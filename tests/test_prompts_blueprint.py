from process_reimagination_agent.prompts.blueprint import (
    BLUEPRINT_REQUIRED_SECTIONS,
    get_blueprint_prompt,
    render_blueprint_prompt,
    validate_prompt_sections,
)


def test_blueprint_prompt_loads_successfully() -> None:
    prompt = get_blueprint_prompt()
    assert len(prompt) > 100
    assert "Re-Imagined Strategy Report" in prompt


def test_blueprint_prompt_contains_all_required_sections() -> None:
    missing = validate_prompt_sections()
    assert missing == [], f"Prompt template is missing sections: {missing}"


def test_blueprint_prompt_is_cached() -> None:
    first = get_blueprint_prompt()
    second = get_blueprint_prompt()
    assert first is second


def test_render_blueprint_prompt_injects_data() -> None:
    rendered = render_blueprint_prompt(
        process_name="Order Intake",
        context_region="ANZ",
        trust_gap_phase="Shadow",
        friction_items=[
            {
                "friction_id": "F-001",
                "current_manual_action": "Manual order entry",
                "where_in_process": "Order Intake",
                "trigger_or_input_channel": "Email",
                "region_impacted": "ANZ",
                "systems_or_tools_mentioned": "SAP",
                "why_its_friction": "Delay",
                "source_evidence": "DOC1",
                "open_questions": "",
            }
        ],
        path_decisions=[
            {
                "path": "C",
                "current_manual_action": "Manual order entry",
                "rationale": "Requires perception",
                "confidence": 0.97,
            }
        ],
        regional_nuances={"anz": {"va01_fallback": True}},
        evidence_references=[{"id": "DOC1", "source": "test.txt", "excerpt": "sample"}],
    )
    assert "Order Intake" in rendered
    assert "ANZ" in rendered
    assert "F-001" in rendered
    assert "Shadow" in rendered


def test_required_sections_tuple_has_thirteen_entries() -> None:
    assert len(BLUEPRINT_REQUIRED_SECTIONS) == 13
