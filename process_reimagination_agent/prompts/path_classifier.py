"""Loader and renderer for the Path Classification prompt template.

The canonical prompt lives in ``templates/path_classifier.md`` so that business
stakeholders can review and version it independently of Python code.  This
module exposes the raw prompt text plus a renderer that injects friction data
and evidence references at call time.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_FILE = _TEMPLATE_DIR / "path_classifier.md"

PATH_CLASSIFIER_REQUIRED_COLUMNS: tuple[str, ...] = (
    "friction_id",
    "recommended_path",
    "suitability_justification",
    "core_vs_sidecar_orientation",
    "human_supervision_needed",
    "confidence",
    "evidence",
    "open_questions",
)


@lru_cache(maxsize=1)
def get_path_classifier_prompt() -> str:
    """Return the raw Path Classification prompt template text."""
    if not _PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Path-classifier prompt template not found at {_PROMPT_FILE}. "
            "Ensure prompts/templates/path_classifier.md is present in the package."
        )
    return _PROMPT_FILE.read_text(encoding="utf-8")


def validate_prompt_columns(prompt_text: str | None = None) -> list[str]:
    """Verify the prompt contains every required output column name.

    Returns a list of missing column names (empty when valid).
    """
    text = prompt_text or get_path_classifier_prompt()
    missing: list[str] = []
    for col in PATH_CLASSIFIER_REQUIRED_COLUMNS:
        if not re.search(re.escape(col), text):
            missing.append(col)
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


def render_path_classifier_prompt(
    friction_items: list[dict[str, Any]],
    evidence_references: list[dict[str, str]],
) -> str:
    """Build the complete path-classifier LLM prompt with friction data injected."""
    template = get_path_classifier_prompt()
    return template.format(
        friction_table=_format_friction_table(friction_items),
        evidence_register=_format_evidence_register(evidence_references),
    )
