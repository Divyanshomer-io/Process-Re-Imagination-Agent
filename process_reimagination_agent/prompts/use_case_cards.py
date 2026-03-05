"""Loader and renderer for the Use Case Cards (Prompt 4) prompt template.

The canonical prompt lives in ``templates/use_case_cards.md``.  This module
exposes the raw text plus a renderer that injects the full state context
needed for the LLM to generate the JSON use case card portfolio.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_FILE = _TEMPLATE_DIR / "use_case_cards.md"

USE_CASE_CARDS_REQUIRED_FIELDS: tuple[str, ...] = (
    "process_name",
    "run_scope",
    "use_case_cards",
)

USE_CASE_CARD_REQUIRED_FIELDS: tuple[str, ...] = (
    "use_case_id",
    "title",
    "path",
    "sap_target",
    "context",
    "agent_role_or_owner",
    "mechanism",
    "tech_mapping",
    "value",
    "human_in_the_loop",
    "dependencies_and_risks",
    "evidence",
)


@lru_cache(maxsize=1)
def get_use_case_cards_prompt() -> str:
    """Return the raw Use Case Cards prompt template text."""
    if not _PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Use Case Cards prompt template not found at {_PROMPT_FILE}. "
            "Ensure prompts/templates/use_case_cards.md is present in the package."
        )
    return _PROMPT_FILE.read_text(encoding="utf-8")


def _format_friction_table(friction_items: list[dict[str, Any]]) -> str:
    """Format cognitive friction logs into the Pain Points & Opportunities table."""
    header = (
        "| Item_ID | Issue_or_Opportunity | Current_Observed_Practice | Where_in_Process "
        "| Trigger_or_Input_Channel | Region_Impacted "
        "| Systems_or_Tools_Mentioned | Why_It_Matters "
        "| Evidence | Open_Questions |\n"
        "|---|---|---|---|---|---|---|---|---|---|"
    )
    rows: list[str] = []
    for item in friction_items:
        rows.append(
            "| {fid} | {issue} | {practice} | {where} | {trigger} | {region} "
            "| {systems} | {why} | {evidence} | {questions} |".format(
                fid=item.get("friction_id", "N/A"),
                issue=item.get("issue_or_opportunity", "N/A"),
                practice=item.get("current_manual_action", "N/A"),
                where=item.get("where_in_process", "Not specified"),
                trigger=item.get("trigger_or_input_channel", "Not specified"),
                region=item.get("region_impacted", "Global"),
                systems=item.get("systems_or_tools_mentioned", "Not specified"),
                why=item.get("why_its_friction", "N/A"),
                evidence=item.get("source_evidence", "N/A"),
                questions=item.get("open_questions", ""),
            )
        )
    return "\n".join([header, *rows]) if rows else header


def _format_path_classification_table(path_decisions: list[dict[str, Any]]) -> str:
    """Format path decisions into the Path Classification (A/B/C) — SAP table."""
    if not path_decisions:
        return "No path classification decisions available."
    header = (
        "| Item_ID | Recommended_Path | Rationale | SAP_Target "
        "| Clean_Core_Guardrail | Side_Car_Component | Confidence |\n"
        "|---|---|---|---|---|---|---|"
    )
    rows: list[str] = []
    for d in path_decisions:
        path = str(d.get("path", ""))
        sap_target = {"A": "SAP S/4HANA", "B": "SAP BTP", "C": "SAP Joule/GenAI"}.get(path, "N/A")
        rows.append(
            "| {action} | {path} | {rationale} | {sap} | {guardrail} | {sidecar} | {conf} |".format(
                action=str(d.get("current_manual_action", "N/A"))[:80],
                path=path,
                rationale=str(d.get("rationale", ""))[:120],
                sap=sap_target,
                guardrail=str(d.get("clean_core_guardrail", ""))[:80],
                sidecar=str(d.get("side_car_component", ""))[:60],
                conf=f"{d.get('confidence', 0):.0%}" if isinstance(d.get("confidence"), (int, float)) else str(d.get("confidence", "")),
            )
        )
    return "\n".join([header, *rows])


def _format_strategy_report(strategy_report: str, max_chars: int = 6000) -> str:
    """Include the strategy report (truncated if very long) for context."""
    if not strategy_report or not strategy_report.strip():
        return "Strategy report not yet available."
    if len(strategy_report) <= max_chars:
        return strategy_report
    return strategy_report[:max_chars].rstrip() + "\n\n[... truncated for prompt context ...]"


def render_use_case_cards_prompt(
    *,
    process_name: str,
    context_region: str,
    friction_items: list[dict[str, Any]],
    path_decisions: list[dict[str, Any]],
    strategy_report: str = "",
) -> str:
    """Build the complete use case cards LLM prompt with full state context."""
    template = get_use_case_cards_prompt()
    return template.format(
        process_name=process_name,
        context_region=context_region,
        friction_table=_format_friction_table(friction_items),
        path_classification_table=_format_path_classification_table(path_decisions),
        strategy_report=_format_strategy_report(strategy_report),
    )
