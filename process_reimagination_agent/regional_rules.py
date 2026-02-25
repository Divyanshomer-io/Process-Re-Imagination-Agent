from __future__ import annotations

from typing import Any


def detect_regional_nuances(combined_text: str, context_region: str) -> dict[str, Any]:
    """
    Normalize region signals used by orchestration.

    These rules intentionally keep business variation in the Side-Car orchestration layer
    and out of the Core ERP kernel to preserve Clean Core.
    """
    text = f"{context_region}\n{combined_text}".lower()
    return {
        "india_dc_based_entry": ("india" in text) and ("dc" in text or "distribution center" in text),
        "china_digital_hub": ("china" in text) and ("digital hub" in text),
        "anz_va01_exception_enabled": ("anz" in text) or ("va01" in text),
        "uruguay_power_street_enabled": ("uruguay" in text) or ("power street" in text),
    }


def should_use_anz_va01_fallback(order_status: str, confidence_score: float, is_anz_context: bool) -> bool:
    """
    ANZ VA01 rule:
    - Enabled only for ANZ context.
    - Triggered as fallback for exceptions (not for clean open/high-confidence flow).
    """
    if not is_anz_context:
        return False
    status = order_status.strip().lower()
    is_exception_state = status in {"shipped", "blocked", "rejected", "partially delivered"}
    return is_exception_state or confidence_score <= 0.95


def should_apply_uruguay_power_street_adapter(channel: str, country: str) -> bool:
    """
    Uruguay Power Street rule:
    - Applies as channel adapter before posting to ERP.
    - Keeps mapping/validation in Side-Car layer, not in Core ERP custom logic.
    """
    country_match = country.strip().lower() == "uruguay"
    channel_match = channel.strip().lower() in {"power street", "powerstreet"}
    return country_match and channel_match


def apply_regional_overrides_to_decision(
    decision: dict[str, Any],
    *,
    region: str,
    order_status: str = "open",
    confidence_score: float = 1.0,
    channel: str = "",
) -> dict[str, Any]:
    """Attach regional override metadata to a path decision."""
    updated = dict(decision)
    overrides = list(updated.get("regional_overrides", []))
    region_lower = region.lower()

    if should_use_anz_va01_fallback(
        order_status=order_status,
        confidence_score=confidence_score,
        is_anz_context="anz" in region_lower,
    ):
        overrides.append("ANZ_VA01_FALLBACK")
        updated["side_car_component"] = "ANZ Change Manager + VA01 Fallback Gate"

    if should_apply_uruguay_power_street_adapter(channel=channel, country=region):
        overrides.append("URUGUAY_POWER_STREET_ADAPTER")
        updated["side_car_component"] = "Uruguay Power Street Adapter"

    updated["regional_overrides"] = sorted(set(overrides))
    return updated

