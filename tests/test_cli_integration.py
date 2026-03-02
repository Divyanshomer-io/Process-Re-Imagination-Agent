from pathlib import Path

import pytest
import json

pytest.importorskip("langgraph")
pytest.importorskip("typer")
from typer.testing import CliRunner

from process_reimagination_agent.cli import app


def test_cli_run_then_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    thread_id = "cli-test-thread"
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("RENDER_BLUEPRINT_IMAGE", "false")

    run_result = runner.invoke(
        app,
        [
            "run",
            "--process-name",
            "Order Intake",
            "--context-region",
            "ANZ",
            "--pain-point",
            "Manual email/PDF order entry",
            "--pain-point",
            "Frequent order modifications",
            "--file",
            str(Path("sample_inputs/order_intake_notes.txt").resolve()),
            "--thread-id",
            thread_id,
        ],
    )
    assert run_result.exit_code == 0
    pending = tmp_path / thread_id / "pending_state.json"
    assert pending.exists()

    resume_result = runner.invoke(
        app,
        [
            "resume",
            "--thread-id",
            thread_id,
            "--approver",
            "qa.user",
        ],
    )
    assert resume_result.exit_code == 0
    assert (tmp_path / thread_id / "strategy_report.md").exists()
    assert (tmp_path / thread_id / "process_blueprint.xml").exists()
    assert (tmp_path / thread_id / "process_blueprint.mmd").exists()
    friction_path = tmp_path / thread_id / "friction_points.json"
    assert friction_path.exists()
    assert (tmp_path / thread_id / "path_classification.json").exists()
    friction_payload = json.loads(friction_path.read_text(encoding="utf-8"))
    assert "evidence_references" in friction_payload
