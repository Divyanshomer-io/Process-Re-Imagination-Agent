from process_reimagination_agent.models import InputManifest
from process_reimagination_agent.state import create_initial_state


def test_initial_state_contains_required_persistent_fields() -> None:
    manifest = InputManifest(
        process_name="Order Intake",
        context_region="ANZ",
        pain_points=["Manual entry"],
        files=[],
    )
    state = create_initial_state(manifest)
    assert "raw_inputs" in state
    assert "cognitive_friction_logs" in state
    assert "path_decisions" in state
    assert "refined_blueprint" in state

