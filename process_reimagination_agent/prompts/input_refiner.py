"""Loader and renderer for the Input Refiner prompt template.

The canonical prompt lives in ``templates/input_refiner.md``.  This module
exposes the raw text plus a renderer that injects the current friction table,
quality feedback, and evidence register at call time.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_FILE = _TEMPLATE_DIR / "input_refiner.md"

INPUT_REFINER_REQUIRED_FIELDS: tuple[str, ...] = (
    "friction_id",
    "current_manual_action",
    "where_in_process",
    "source_evidence",
    "proposed_path",
    "rationale",
)


@lru_cache(maxsize=1)
def get_input_refiner_prompt() -> str:
    """Return the raw Input Refiner prompt template text."""
    if not _PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Input-refiner prompt template not found at {_PROMPT_FILE}. "
            "Ensure prompts/templates/input_refiner.md is present in the package."
        )
    return _PROMPT_FILE.read_text(encoding="utf-8")


def validate_prompt_fields(prompt_text: str | None = None) -> list[str]:
    """Verify the prompt contains every required output field name."""
    text = prompt_text or get_input_refiner_prompt()
    missing: list[str] = []
    for field in INPUT_REFINER_REQUIRED_FIELDS:
        if not re.search(re.escape(field), text):
            missing.append(field)
    return missing


def _format_friction_table(friction_items: list[dict[str, Any]]) -> str:
    header = (
        "| Friction_ID | Current_Manual_Action | Where_in_Process "
        "| Trigger_or_Input_Channel | Region_Impacted "
        "| Systems_or_Tools_Mentioned | Why_It's_Friction "
        "| Evidence | Open_Questions |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    rows: list[str] = []
    for item in friction_items:
        rows.append(
            "| {fid} | {action} | {where} | {trigger} | {region} "
            "| {systems} | {why} | {evidence} | {questions} |".format(
                fid=item.get("friction_id", "N/A"),
                action=item.get("current_manual_action", "N/A"),
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


def render_input_refiner_prompt(
    friction_items: list[dict[str, Any]],
    quality_feedback: list[str],
    evidence_references: list[dict[str, str]],
) -> str:
    """Build the complete input-refiner LLM prompt with data injected."""
    template = get_input_refiner_prompt()
    return template.format(
        friction_table=_format_friction_table(friction_items),
        quality_feedback="\n".join(f"- {fb}" for fb in quality_feedback) if quality_feedback else "No feedback.",
        evidence_register=_format_evidence_register(evidence_references),
    )
