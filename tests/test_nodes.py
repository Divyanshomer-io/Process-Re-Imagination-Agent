from process_reimagination_agent.config import Settings
from process_reimagination_agent.models import InputManifest
from process_reimagination_agent.nodes import Architect_Node, Synthesizer_Node
from process_reimagination_agent.state import create_initial_state


def test_synthesizer_always_runs_with_sparse_inputs() -> None:
    manifest = InputManifest(
        process_name="Order Intake",
        context_region="Global",
        pain_points=[],
        files=[],
    )
    state = create_initial_state(manifest)
    updated = Synthesizer_Node(state, Settings())
    assert updated["phase_status"]["phase_1_current_reality_synthesis"] == "completed"
    assert updated["cognitive_friction_logs"]


def test_architect_path_c_guardrail_enforced() -> None:
    manifest = InputManifest(
        process_name="Order Intake",
        context_region="Global",
        pain_points=[],
        files=[],
    )
    state = create_initial_state(manifest)
    state["cognitive_friction_logs"] = [
        {
            "current_manual_action": "Send status update email",
            "friction_type": "Deterministic coordination and status handling",
            "proposed_path": "C",
            "rationale": "Original suggestion",
            "expected_kpi_shift": "10%",
            "requires_perception": False,
            "requires_reasoning": False,
            "requires_adaptive_action": False,
            "source_evidence": "test",
        }
    ]
    updated = Architect_Node(state, Settings())
    assert updated["path_decisions"][0]["path"] == "B"

