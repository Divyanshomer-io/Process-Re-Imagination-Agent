"""Loader for the Pain Points & Opportunities Extractor prompt template.

The canonical prompt lives in ``templates/friction_points.md`` so that business
stakeholders can review and version it independently of Python code.  This
module exposes the prompt text plus the strict column schema extracted from it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PROMPT_FILE = _TEMPLATE_DIR / "friction_points.md"

FRICTION_POINTS_REQUIRED_COLUMNS: tuple[str, ...] = (
    "Item_ID",
    "Issue_or_Opportunity",
    "Current_Observed_Practice",
    "Where_in_Process",
    "Trigger_or_Input_Channel",
    "Region_Impacted",
    "Systems_or_Tools_Mentioned",
    "Why_It_Matters",
    "Evidence",
    "Open_Questions",
)


@lru_cache(maxsize=1)
def get_friction_points_prompt() -> str:
    """Return the full Pain Points & Opportunities Extractor prompt text."""
    if not _PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Friction-points prompt template not found at {_PROMPT_FILE}. "
            "Ensure prompts/templates/friction_points.md is present in the package."
        )
    return _PROMPT_FILE.read_text(encoding="utf-8")


def validate_prompt_columns(prompt_text: str | None = None) -> list[str]:
    """Verify the prompt contains every required column name.

    Returns a list of missing column names (empty when valid).
    """
    text = prompt_text or get_friction_points_prompt()
    missing: list[str] = []
    for col in FRICTION_POINTS_REQUIRED_COLUMNS:
        if not re.search(re.escape(col), text):
            missing.append(col)
    return missing
