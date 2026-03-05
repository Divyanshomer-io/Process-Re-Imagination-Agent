"""Loader and renderer for the Blueprint (strategy report) prompt template.

The canonical prompt lives in ``templates/blueprint.md``.  This module
exposes the raw text plus a renderer that injects the full state context
needed for the LLM to generate the strategy report.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_FILE = _TEMPLATE_DIR / "blueprint.md"

BLUEPRINT_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Executive Summary",
    "Current Reality Synthesis",
    "Strategy: Layered Re-Imagination using Path A/B/C",
    "Architecture of the Future State",
    "Technical Stack",
    "Trust Gap Protocol",
    "Risks, Guardrails, and Open Questions",
)


@lru_cache(maxsize=1)
def get_blueprint_prompt() -> str:
    """Return the raw Blueprint prompt template text."""
    if not _PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Blueprint prompt template not found at {_PROMPT_FILE}. "
            "Ensure prompts/templates/blueprint.md is present in the package."
        )
    return _PROMPT_FILE.read_text(encoding="utf-8")


def validate_prompt_sections(prompt_text: str | None = None) -> list[str]:
    """Verify the prompt mentions every required report section."""
    text = prompt_text or get_blueprint_prompt()
    missing: list[str] = []
    for section in BLUEPRINT_REQUIRED_SECTIONS:
        if not re.search(re.escape(section), text):
            missing.append(section)
    return missing


def _format_friction_table(friction_items: list[dict[str, Any]]) -> str:
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


def _format_path_decisions(path_decisions: list[dict[str, Any]]) -> str:
    if not path_decisions:
        return "- No path decisions available."
    lines: list[str] = []
    for d in path_decisions:
        lines.append(
            f"- **{d.get('path')}** for `{d.get('current_manual_action')}`: "
            f"{d.get('rationale')} (confidence {d.get('confidence', 0):.0%})"
        )
    return "\n".join(lines)


def _format_evidence_register(evidence_references: list[dict[str, str]]) -> str:
    if not evidence_references:
        return "No source evidence references available."
    lines: list[str] = []
    for ref in evidence_references:
        lines.append(
            "- [{id}] {source}: {excerpt}".format(
                id=ref.get("id", "N/A"),
                source=ref.get("source", "N/A"),
                excerpt=str(ref.get("excerpt", ""))[:220],
            )
        )
    return "\n".join(lines)


def render_blueprint_prompt(
    *,
    process_name: str,
    context_region: str,
    trust_gap_phase: str,
    friction_items: list[dict[str, Any]],
    path_decisions: list[dict[str, Any]],
    regional_nuances: dict[str, Any],
    evidence_references: list[dict[str, str]],
    report_mode: str = "FULL",
) -> str:
    """Build the complete blueprint LLM prompt with full state context injected."""
    template = get_blueprint_prompt()
    return template.format(
        process_name=process_name,
        context_region=context_region,
        trust_gap_phase=trust_gap_phase,
        friction_table=_format_friction_table(friction_items),
        path_decisions=_format_path_decisions(path_decisions),
        regional_nuances=json.dumps(regional_nuances, indent=2),
        evidence_register=_format_evidence_register(evidence_references),
        report_mode=report_mode,
    )
