from process_reimagination_agent.prompts.input_refiner import (
    INPUT_REFINER_REQUIRED_FIELDS,
    get_input_refiner_prompt,
    render_input_refiner_prompt,
    validate_prompt_fields,
)


def test_input_refiner_prompt_loads_successfully() -> None:
    prompt = get_input_refiner_prompt()
    assert len(prompt) > 100
    assert "Cognitive Friction Refinement" in prompt


def test_input_refiner_prompt_contains_all_required_fields() -> None:
    missing = validate_prompt_fields()
    assert missing == [], f"Prompt template is missing fields: {missing}"


def test_input_refiner_prompt_is_cached() -> None:
    first = get_input_refiner_prompt()
    second = get_input_refiner_prompt()
    assert first is second


def test_render_input_refiner_prompt_injects_data() -> None:
    friction_items = [
        {
            "friction_id": "F-001",
            "current_manual_action": "Test action",
            "where_in_process": "Test step",
            "trigger_or_input_channel": "Email",
            "region_impacted": "Global",
            "systems_or_tools_mentioned": "SAP",
            "why_its_friction": "Delay",
            "source_evidence": "DOC1",
            "open_questions": "",
        }
    ]
    rendered = render_input_refiner_prompt(
        friction_items,
        quality_feedback=["Low confidence"],
        evidence_references=[{"id": "DOC1", "source": "test.txt", "excerpt": "sample"}],
    )
    assert "F-001" in rendered
    assert "Low confidence" in rendered
    assert "DOC1" in rendered


def test_required_fields_tuple_count() -> None:
    assert len(INPUT_REFINER_REQUIRED_FIELDS) >= 5
