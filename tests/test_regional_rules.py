from process_reimagination_agent.regional_rules import (
    apply_regional_overrides_to_decision,
    should_apply_uruguay_power_street_adapter,
    should_use_anz_va01_fallback,
)


def test_anz_va01_fallback_only_on_exception_conditions() -> None:
    assert should_use_anz_va01_fallback(order_status="shipped", confidence_score=0.99, is_anz_context=True)
    assert should_use_anz_va01_fallback(order_status="open", confidence_score=0.90, is_anz_context=True)
    assert not should_use_anz_va01_fallback(order_status="open", confidence_score=0.99, is_anz_context=True)
    assert not should_use_anz_va01_fallback(order_status="shipped", confidence_score=0.99, is_anz_context=False)


def test_uruguay_power_street_adapter_rule() -> None:
    assert should_apply_uruguay_power_street_adapter(channel="Power Street", country="Uruguay")
    assert should_apply_uruguay_power_street_adapter(channel="powerstreet", country="Uruguay")
    assert not should_apply_uruguay_power_street_adapter(channel="email", country="Uruguay")
    assert not should_apply_uruguay_power_street_adapter(channel="Power Street", country="ANZ")


def test_regional_override_applied_to_decision_payload() -> None:
    decision = {
        "path": "B",
        "confidence": 0.91,
        "side_car_component": "Workflow Automation Side-Car",
        "regional_overrides": [],
    }
    updated = apply_regional_overrides_to_decision(
        decision,
        region="ANZ",
        order_status="blocked",
        confidence_score=0.91,
        channel="email",
    )
    assert "ANZ_VA01_FALLBACK" in updated["regional_overrides"]

