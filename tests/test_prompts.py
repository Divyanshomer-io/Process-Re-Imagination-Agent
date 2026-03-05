from process_reimagination_agent.prompts.friction_points import (
    FRICTION_POINTS_REQUIRED_COLUMNS,
    get_friction_points_prompt,
    validate_prompt_columns,
)


def test_friction_points_prompt_loads_successfully() -> None:
    prompt = get_friction_points_prompt()
    assert len(prompt) > 100
    assert "Pain Points & Opportunities" in prompt


def test_friction_points_prompt_contains_all_required_columns() -> None:
    missing = validate_prompt_columns()
    assert missing == [], f"Prompt template is missing columns: {missing}"


def test_required_columns_tuple_has_ten_entries() -> None:
    assert len(FRICTION_POINTS_REQUIRED_COLUMNS) == 10


def test_friction_points_prompt_is_cached() -> None:
    first = get_friction_points_prompt()
    second = get_friction_points_prompt()
    assert first is second
