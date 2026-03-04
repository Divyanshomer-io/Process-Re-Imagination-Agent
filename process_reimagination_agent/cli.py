from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer
from langgraph.checkpoint.memory import MemorySaver

from process_reimagination_agent.config import Settings, get_settings
from process_reimagination_agent.graph import build_graph
from process_reimagination_agent.models import InputManifest
from process_reimagination_agent.nodes import _build_path_classification_table, build_friction_points_markdown
from process_reimagination_agent.observability import MetricsCollector, get_logger, render_slo_dashboard
from process_reimagination_agent.reliability import (
    JobEnvelope,
    InMemoryJobQueue,
    execute_with_retry,
    persist_artifact,
    write_dead_letter,
)
from process_reimagination_agent.state import create_initial_state
from process_reimagination_agent.validators import validate_methodology_compliance

app = typer.Typer(help="McCain Agentic Process Re-Imagination Architect (LangGraph)")
LOGGER = get_logger()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _output_dir(settings: Settings, thread_id: str) -> Path:
    path = settings.output_root / thread_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pending_state_path(settings: Settings, thread_id: str) -> Path:
    return _output_dir(settings, thread_id) / "pending_state.json"


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_mermaid_code(blueprint_xml: str) -> str:
    visual_match = re.search(r"<MermaidData><!\[CDATA\[(.*?)\]\]></MermaidData>", blueprint_xml, re.S)
    if visual_match:
        return visual_match.group(1).strip()
    legacy_match = re.search(r"<Diagram[^>]*><!\[CDATA\[(.*?)\]\]></Diagram>", blueprint_xml, re.S)
    if legacy_match:
        return legacy_match.group(1).strip()
    return ""


def _render_mermaid_image(
    settings: Settings,
    *,
    output_dir: Path,
    mermaid_code: str,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "mmd_path": str(output_dir / "process_blueprint.mmd"),
        "svg_path": str(output_dir / "process_blueprint.svg"),
        "renderer": "",
        "status": "skipped",
        "warning": "",
    }
    mmd_path = output_dir / "process_blueprint.mmd"
    svg_path = output_dir / "process_blueprint.svg"
    mmd_path.write_text(mermaid_code, encoding="utf-8")

    if not settings.render_blueprint_image:
        artifact["warning"] = "Image render disabled via RENDER_BLUEPRINT_IMAGE."
        return artifact

    mmdc = shutil.which("mmdc")
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    command: list[str] | None = None

    if mmdc:
        artifact["renderer"] = "mmdc"
        command = [mmdc, "-i", str(mmd_path), "-o", str(svg_path), "-b", "transparent"]
    elif npx:
        artifact["renderer"] = "npx:@mermaid-js/mermaid-cli"
        command = [
            npx,
            "--yes",
            "@mermaid-js/mermaid-cli",
            "-i",
            str(mmd_path),
            "-o",
            str(svg_path),
            "-b",
            "transparent",
        ]
    else:
        artifact["warning"] = "No Mermaid renderer found (mmdc/npx)."
        return artifact

    chrome_candidates = [
        os.getenv("CHROME_PATH", ""),
        os.getenv("GOOGLE_CHROME_BIN", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path(os.getenv("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"),
    ]
    chrome_path = next((path for path in chrome_candidates if path and Path(path).exists()), "")
    command_env = os.environ.copy()
    command_env["PUPPETEER_SKIP_DOWNLOAD"] = "true"
    if chrome_path:
        command_env["PUPPETEER_EXECUTABLE_PATH"] = chrome_path

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=settings.mermaid_render_timeout_sec,
            env=command_env,
        )
    except subprocess.TimeoutExpired:
        artifact["warning"] = (
            f"Render timed out after {settings.mermaid_render_timeout_sec}s "
            f"using renderer {artifact.get('renderer', 'unknown')}."
        )
        return artifact
    except OSError as exc:
        artifact["warning"] = f"Render failed to start: {exc}"
        return artifact
    if svg_path.exists() and svg_path.stat().st_size > 0:
        artifact["status"] = "created"
        if completed.returncode != 0:
            artifact["warning"] = (
                f"Renderer exited {completed.returncode} but SVG was created successfully."
            )
        return artifact

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        artifact["warning"] = f"Render failed (exit {completed.returncode}): {stderr or stdout}"
        return artifact

    artifact["warning"] = "Renderer completed but SVG was not created."
    return artifact


def _write_final_outputs(settings: Settings, thread_id: str, state: dict[str, Any]) -> None:
    output_dir = _output_dir(settings, thread_id)
    report = state.get("strategy_report_markdown") or state.get("refined_blueprint", {}).get("strategy_report_markdown", "")
    xml = state.get("mermaid_xml") or state.get("refined_blueprint", {}).get("mermaid_xml", "")

    (output_dir / "strategy_report.md").write_text(report, encoding="utf-8")
    (output_dir / "process_blueprint.xml").write_text(xml, encoding="utf-8")
    mermaid_code = _extract_mermaid_code(xml)
    render_artifact = _render_mermaid_image(settings, output_dir=output_dir, mermaid_code=mermaid_code) if mermaid_code else {
        "status": "skipped",
        "warning": "Mermaid code not found in blueprint XML.",
    }
    state["render_artifact"] = render_artifact
    if render_artifact.get("warning"):
        state["errors"] = list(state.get("errors", []))
        state["errors"].append(str(render_artifact["warning"]))

    phase_status = dict(state.get("phase_status", {}))
    friction_logs = state.get("cognitive_friction_logs", [])

    friction_md = build_friction_points_markdown(
        process_name=state.get("process_name", "Process"),
        context_region=state.get("context_region", "Global"),
        cognitive_friction_logs=friction_logs,
    )
    (output_dir / "friction_points.md").write_text(friction_md, encoding="utf-8")

    _save_json(
        output_dir / "friction_points.json",
        {
            "process_name": state.get("process_name", ""),
            "context_region": state.get("context_region", ""),
            "cognitive_friction_logs": friction_logs,
            "regional_nuances": state.get("regional_nuances", {}),
            "evidence_references": state.get("evidence_references", []),
            "phase_status": {
                "phase_1_current_reality_synthesis": phase_status.get("phase_1_current_reality_synthesis", "unknown"),
            },
            "errors": state.get("errors", []),
        },
    )
    path_table = _build_path_classification_table(
        state.get("path_decisions", []),
        friction_logs,
    )
    path_classification_md = (
        f"# Path Classification (A/B/C): {state.get('process_name', 'Process')}"
        f" ({state.get('context_region', 'Global')})\n\n"
        f"{path_table}\n"
    )
    (output_dir / "path_classification.md").write_text(path_classification_md, encoding="utf-8")

    _save_json(output_dir / "final_state.json", state)
    persist_artifact(settings, thread_id=thread_id, name="final_state.json", payload=_json_safe(state))


@app.command("run")
def run_workflow(
    process_name: str = typer.Option(..., help="Process name, e.g. Order-to-Cash"),
    context_region: str = typer.Option(..., help="Industry/region context"),
    pain_point: list[str] = typer.Option([], "--pain-point", help="Current pain point (repeatable)"),
    file: list[Path] = typer.Option([], "--file", help="Input artifact path (repeatable)"),
    thread_id: str = typer.Option("", help="Execution thread id; autogenerated if omitted"),
    channel: str = typer.Option("", help="Optional order intake channel hint"),
    order_status: str = typer.Option("open", help="Optional order status hint for regional routing"),
) -> None:
    settings = get_settings()
    settings.validate_llm_available()

    backends: list[str] = []
    if settings.daia_enabled:
        backends.append(f"DAIA ({settings.daia_model})")
    if settings.azure_enabled:
        backends.append(f"Azure OpenAI ({settings.azure_openai_deployment})")
    if settings.openai_enabled:
        backends.append(f"OpenAI ({settings.openai_model})")
    LOGGER.info("LLM backends configured: %s", " > ".join(backends))

    metrics = MetricsCollector()
    start_time = time.perf_counter()
    runtime_thread_id = thread_id or str(uuid4())
    manifest = InputManifest(
        process_name=process_name,
        context_region=context_region,
        pain_points=pain_point,
        files=[str(p) for p in file],
    )
    state = create_initial_state(manifest, trust_gap_phase=settings.trust_gap_default_phase)
    state["raw_inputs"]["channel"] = channel
    state["raw_inputs"]["order_status"] = order_status
    queue = InMemoryJobQueue()
    queue.enqueue(JobEnvelope(job_id=runtime_thread_id, payload={"state": state}))
    metrics.incr("jobs_enqueued")

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer, settings=settings, interrupt_before_blueprint=True)
    config = {"configurable": {"thread_id": runtime_thread_id}}

    envelope = queue.dequeue()
    if not envelope:
        raise typer.BadParameter("No queued job available for processing.")
    metrics.incr("jobs_started")

    def _invoke() -> None:
        graph.invoke(envelope.payload["state"], config=config)

    try:
        execute_with_retry(
            _invoke,
            settings=settings,
            on_retry=lambda attempt, exc: LOGGER.warning(
                "run retry thread_id=%s attempt=%s error=%s", runtime_thread_id, attempt, exc
            ),
        )
    except Exception as exc:
        metrics.incr("jobs_failed")
        dead_path = write_dead_letter(
            settings,
            thread_id=runtime_thread_id,
            reason=f"run_failed: {exc}",
            payload={"state": _json_safe(envelope.payload.get("state", {}))},
        )
        LOGGER.error("run failed thread_id=%s dead_letter=%s error=%s", runtime_thread_id, dead_path, exc)
        raise

    snapshot = graph.get_state(config)
    current_state = dict(snapshot.values or {})
    metrics.incr("jobs_succeeded")

    pending_path = _pending_state_path(settings, runtime_thread_id)
    _save_json(pending_path, current_state)
    persist_artifact(settings, thread_id=runtime_thread_id, name="pending_state.json", payload=_json_safe(current_state))

    next_nodes = tuple(snapshot.next or ())
    if "Blueprint_Node" in next_nodes:
        typer.echo(f"Thread: {runtime_thread_id}")
        typer.echo("Execution paused at Trust Gap checkpoint before Blueprint_Node.")
        typer.echo(f"Pending state: {pending_path}")
        typer.echo("Approve and continue with: cli resume --thread-id <THREAD_ID> --approver <NAME>")
        metrics.timing("run_workflow", time.perf_counter() - start_time)
        if settings.enable_json_metrics:
            metrics_path = _output_dir(settings, runtime_thread_id) / "metrics.json"
            metrics.write_json(metrics_path)
            snapshot = metrics.snapshot()
            (_output_dir(settings, runtime_thread_id) / "slo_dashboard.md").write_text(
                render_slo_dashboard(snapshot), encoding="utf-8"
            )
        return

    if current_state.get("phase_status", {}).get("phase_3_blueprint_generation") == "completed":
        validate_methodology_compliance(current_state, min_report_words=settings.min_report_words)
        _write_final_outputs(settings, runtime_thread_id, current_state)
        typer.echo(f"Thread: {runtime_thread_id}")
        typer.echo("Workflow completed without interruption.")
        metrics.timing("run_workflow", time.perf_counter() - start_time)
        if settings.enable_json_metrics:
            metrics_path = _output_dir(settings, runtime_thread_id) / "metrics.json"
            metrics.write_json(metrics_path)
            snapshot = metrics.snapshot()
            (_output_dir(settings, runtime_thread_id) / "slo_dashboard.md").write_text(
                render_slo_dashboard(snapshot), encoding="utf-8"
            )
        return

    typer.echo(f"Thread: {runtime_thread_id}")
    typer.echo("Workflow ended before blueprint generation. Inspect pending_state.json for escalation details.")
    metrics.timing("run_workflow", time.perf_counter() - start_time)
    if settings.enable_json_metrics:
        metrics_path = _output_dir(settings, runtime_thread_id) / "metrics.json"
        metrics.write_json(metrics_path)
        snapshot = metrics.snapshot()
        (_output_dir(settings, runtime_thread_id) / "slo_dashboard.md").write_text(
            render_slo_dashboard(snapshot), encoding="utf-8"
        )


@app.command("resume")
def resume_workflow(
    thread_id: str = typer.Option(..., help="Execution thread id from run command"),
    approver: str = typer.Option(..., help="Human approver id"),
    notes: str = typer.Option("", help="Approval notes"),
) -> None:
    settings = get_settings()
    settings.validate_llm_available()
    metrics = MetricsCollector()
    start_time = time.perf_counter()
    pending_path = _pending_state_path(settings, thread_id)
    if not pending_path.exists():
        raise typer.BadParameter(f"No pending state found for thread {thread_id} at {pending_path}")

    state = _load_json(pending_path)
    state["manual_approval"] = True
    state["raw_inputs"] = dict(state.get("raw_inputs", {}))
    state["raw_inputs"]["approved_by"] = approver
    state["raw_inputs"]["approval_notes"] = notes

    # Approval received: compile without interrupt to execute Blueprint_Node.
    graph = build_graph(
        checkpointer=MemorySaver(),
        settings=settings,
        interrupt_before_blueprint=False,
    )
    try:
        completed_state = execute_with_retry(
            lambda: graph.invoke(state, config={"configurable": {"thread_id": thread_id}}),
            settings=settings,
            on_retry=lambda attempt, exc: LOGGER.warning(
                "resume retry thread_id=%s attempt=%s error=%s", thread_id, attempt, exc
            ),
        )
    except Exception as exc:
        metrics.incr("resume_failed")
        dead_path = write_dead_letter(
            settings,
            thread_id=thread_id,
            reason=f"resume_failed: {exc}",
            payload={"state": _json_safe(state)},
        )
        LOGGER.error("resume failed thread_id=%s dead_letter=%s error=%s", thread_id, dead_path, exc)
        raise
    final_state = dict(completed_state or {})

    validate_methodology_compliance(final_state, min_report_words=settings.min_report_words)
    _write_final_outputs(settings, thread_id, final_state)
    pending_path.unlink(missing_ok=True)
    persist_artifact(settings, thread_id=thread_id, name="resume_final_state.json", payload=_json_safe(final_state))
    metrics.incr("resume_succeeded")
    metrics.timing("resume_workflow", time.perf_counter() - start_time)
    if settings.enable_json_metrics:
        metrics_path = _output_dir(settings, thread_id) / "metrics_resume.json"
        metrics.write_json(metrics_path)
        snapshot = metrics.snapshot()
        (_output_dir(settings, thread_id) / "slo_dashboard.md").write_text(
            render_slo_dashboard(snapshot), encoding="utf-8"
        )

    typer.echo(f"Thread: {thread_id}")
    typer.echo("Manual approval recorded. Blueprint and strategy report generated.")
    typer.echo(f"Outputs: {_output_dir(settings, thread_id)}")


if __name__ == "__main__":
    app()
    chrome_candidates = [
        os.getenv("CHROME_PATH", ""),
        os.getenv("GOOGLE_CHROME_BIN", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path(os.getenv("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"),
    ]
    chrome_path = next((path for path in chrome_candidates if path and Path(path).exists()), "")
    command_env = os.environ.copy()
    # Prevent puppeteer postinstall from trying to download Chromium in locked enterprise environments.
    command_env["PUPPETEER_SKIP_DOWNLOAD"] = "true"
    if chrome_path:
        command_env["PUPPETEER_EXECUTABLE_PATH"] = chrome_path
