"""Bridge between FastAPI async world and the synchronous LangGraph agent."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from process_reimagination_agent.config import Settings, get_settings
from process_reimagination_agent.graph import build_graph
from process_reimagination_agent.models import InputManifest
from process_reimagination_agent.nodes import Blueprint_Node
from process_reimagination_agent.state import create_initial_state
from process_reimagination_agent.validators import validate_methodology_compliance

from core.session_manager import EngagementSession

logger = logging.getLogger("cpre.bridge")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _update_step(steps: list[dict[str, str]], index: int, status: str) -> None:
    if 0 <= index < len(steps):
        steps[index]["status"] = status


def _complete_all(steps: list[dict[str, str]]) -> None:
    for s in steps:
        s["status"] = "complete"


def _calculate_progress(session: EngagementSession) -> float:
    total = len(session.phase1_steps) + len(session.phase2_steps) + len(session.phase3_steps)
    if total == 0:
        return 0.0
    completed = sum(
        1 for s in (session.phase1_steps + session.phase2_steps + session.phase3_steps)
        if s["status"] == "complete"
    )
    return (completed / total) * 100.0


def _run_agent_sync(session: EngagementSession, settings: Settings) -> dict[str, Any]:
    """Synchronous function that runs phases 1+2 of the agent pipeline.

    Called from asyncio.to_thread to avoid blocking the event loop.
    """
    from core.file_manager import get_file_paths

    file_paths = get_file_paths(session.files)

    pain_points = list(session.pain_points_list)
    if session.pain_points and not pain_points:
        pain_points = [p.strip() for p in session.pain_points.split("\n") if p.strip()]

    manifest = InputManifest(
        process_name=session.process_name,
        context_region=session.region,
        pain_points=pain_points,
        files=file_paths,
    )

    # Phase 1 step 1-4: reading inputs
    for i in range(min(4, len(session.phase1_steps))):
        _update_step(session.phase1_steps, i, "running")
        session.progress = _calculate_progress(session)
        _update_step(session.phase1_steps, i, "complete")

    state = create_initial_state(manifest, trust_gap_phase=settings.trust_gap_default_phase)
    state["raw_inputs"]["channel"] = session.channel
    state["raw_inputs"]["order_status"] = session.order_status

    checkpointer = MemorySaver()
    graph = build_graph(
        checkpointer=checkpointer,
        settings=settings,
        interrupt_before_blueprint=True,
    )
    config = {"configurable": {"thread_id": session.thread_id}}

    # Phase 1 step 5: identify cognitive friction
    _update_step(session.phase1_steps, 4, "running")
    session.current_phase = 1
    session.progress = _calculate_progress(session)

    graph.invoke(state, config=config)

    _complete_all(session.phase1_steps)
    session.current_phase = 2
    session.progress = _calculate_progress(session)

    snapshot = graph.get_state(config)
    current_state = dict(snapshot.values or {})

    # Mark phase 2 steps
    _complete_all(session.phase2_steps)
    session.progress = _calculate_progress(session)

    # Save pending state
    output_dir = settings.output_root / session.thread_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pending_path = output_dir / "pending_state.json"
    pending_path.write_text(
        json.dumps(_json_safe(current_state), indent=2),
        encoding="utf-8",
    )

    return current_state


def _run_blueprint_sync(
    session: EngagementSession,
    approver: str,
    notes: str,
    settings: Settings,
) -> dict[str, Any]:
    """Synchronous function that runs phase 3 (Blueprint_Node) after approval."""
    pending_path = settings.output_root / session.thread_id / "pending_state.json"
    if not pending_path.exists() and session.agent_state:
        state = dict(session.agent_state)
    else:
        state = json.loads(pending_path.read_text(encoding="utf-8"))

    state["manual_approval"] = True
    state["raw_inputs"] = dict(state.get("raw_inputs", {}))
    state["raw_inputs"]["approved_by"] = approver
    state["raw_inputs"]["approval_notes"] = notes

    _update_step(session.phase3_steps, 0, "running")
    session.current_phase = 3
    session.progress = _calculate_progress(session)

    blueprint_output = Blueprint_Node(state, settings)
    final_state = {**state, **blueprint_output}

    _complete_all(session.phase3_steps)
    session.progress = 100.0

    try:
        validate_methodology_compliance(final_state, min_report_words=settings.min_report_words)
    except Exception as exc:
        logger.warning("Methodology compliance warning: %s", exc)

    _write_final_outputs(settings, session.thread_id, final_state)

    pending_path.unlink(missing_ok=True)
    return final_state


def _write_final_outputs(settings: Settings, thread_id: str, state: dict[str, Any]) -> None:
    """Replicates the CLI's _write_final_outputs logic."""
    import re
    from process_reimagination_agent.nodes import (
        _build_path_classification_table,
        build_friction_points_markdown,
    )

    output_dir = settings.output_root / thread_id
    output_dir.mkdir(parents=True, exist_ok=True)

    report = state.get("strategy_report_markdown") or state.get("refined_blueprint", {}).get("strategy_report_markdown", "")
    xml = state.get("mermaid_xml") or state.get("refined_blueprint", {}).get("mermaid_xml", "")

    (output_dir / "strategy_report.md").write_text(report, encoding="utf-8")
    (output_dir / "process_blueprint.xml").write_text(xml, encoding="utf-8")

    mermaid_code = ""
    mermaid_match = re.search(r"<MermaidData><!\[CDATA\[(.*?)\]\]></MermaidData>", xml, re.S)
    if mermaid_match:
        mermaid_code = mermaid_match.group(1).strip()
        (output_dir / "process_blueprint.mmd").write_text(mermaid_code, encoding="utf-8")

    from process_reimagination_agent.mermaid_render import render_mermaid_to_svg

    render_artifact = (
        render_mermaid_to_svg(settings, output_dir=output_dir, mermaid_code=mermaid_code)
        if mermaid_code
        else {"status": "skipped", "warning": "Mermaid code not found in blueprint XML."}
    )
    state["render_artifact"] = render_artifact
    if render_artifact.get("warning"):
        state.setdefault("errors", [])
        state["errors"].append(str(render_artifact["warning"]))

    friction_logs = state.get("cognitive_friction_logs", [])
    friction_md = build_friction_points_markdown(
        process_name=state.get("process_name", "Process"),
        context_region=state.get("context_region", "Global"),
        cognitive_friction_logs=friction_logs,
    )
    (output_dir / "friction_points.md").write_text(friction_md, encoding="utf-8")
    (output_dir / "friction_points.json").write_text(
        json.dumps(_json_safe({
            "process_name": state.get("process_name", ""),
            "context_region": state.get("context_region", ""),
            "cognitive_friction_logs": friction_logs,
            "evidence_references": state.get("evidence_references", []),
        }), indent=2),
        encoding="utf-8",
    )

    path_table = _build_path_classification_table(
        state.get("path_decisions", []),
        friction_logs,
    )
    (output_dir / "path_classification.md").write_text(
        f"# Path Classification: {state.get('process_name', '')}\n\n{path_table}\n",
        encoding="utf-8",
    )

    use_case_cards = state.get("use_case_cards_json") or state.get("refined_blueprint", {}).get("use_case_cards_json", "")
    if use_case_cards:
        (output_dir / "use_case_cards.json").write_text(use_case_cards, encoding="utf-8")

    (output_dir / "final_state.json").write_text(
        json.dumps(_json_safe(state), indent=2), encoding="utf-8"
    )


async def execute_agent_run(session: EngagementSession) -> None:
    """Run the full agent pipeline (phases 1+2+3) in a background thread.

    After phases 1+2 complete, automatically proceeds to phase 3 (blueprint
    generation) without requiring manual approval.
    """
    settings = get_settings()
    settings.validate_llm_available()

    session.status = "running"
    session.init_progress()

    try:
        state = await asyncio.to_thread(_run_agent_sync, session, settings)
        session.agent_state = state
        session.confidence_score = state.get("confidence_score")
        session.quality_gate_result = state.get("quality_gate_result")

        if state.get("quality_gate_result") == "escalate":
            session.status = "error"
            session.run_error = "Quality gate escalated to human review. Confidence too low after max refinement loops."
            return

        _complete_all(session.phase1_steps)
        _complete_all(session.phase2_steps)
        session.progress = _calculate_progress(session)

        # Auto-approve and run Phase 3 (Blueprint generation)
        logger.info("Auto-approving and starting Phase 3 for session %s", session.id)
        final_state = await asyncio.to_thread(
            _run_blueprint_sync, session, "auto-approved", "Automatic approval", settings
        )
        session.agent_state = final_state
        session.status = "ready"
        session.progress = 100.0

    except Exception as exc:
        logger.exception("Agent run failed for session %s", session.id)
        session.status = "error"
        session.run_error = str(exc)


async def execute_agent_resume(
    session: EngagementSession,
    approver: str,
    notes: str,
) -> None:
    """Resume the agent (phase 3) after human approval, in a background thread."""
    settings = get_settings()

    session.status = "running"
    try:
        final_state = await asyncio.to_thread(
            _run_blueprint_sync, session, approver, notes, settings
        )
        session.agent_state = final_state
        session.status = "ready"
        session.progress = 100.0
    except Exception as exc:
        logger.exception("Agent resume failed for session %s", session.id)
        session.status = "error"
        session.run_error = str(exc)
