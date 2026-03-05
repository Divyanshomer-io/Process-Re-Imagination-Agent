from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InputManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_name: str = Field(min_length=3)
    context_region: str = Field(min_length=2)
    pain_points: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    additional_context: dict[str, str] = Field(default_factory=dict)


class FrictionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Pain Points & Opportunities table columns (strict output schema).
    friction_id: str = ""
    issue_or_opportunity: str = ""
    current_manual_action: str = Field(min_length=3)
    where_in_process: str = "Not specified"
    trigger_or_input_channel: str = "Not specified"
    region_impacted: str = "Global"
    systems_or_tools_mentioned: str = "Not specified"
    why_its_friction: str = ""
    open_questions: str = ""

    # Internal classification fields used by downstream path-classifier and refiner.
    friction_type: str = Field(min_length=3)
    proposed_path: Literal["A", "B", "C"]
    rationale: str = Field(min_length=5)
    expected_kpi_shift: str = Field(min_length=3)
    requires_perception: bool = False
    requires_reasoning: bool = False
    requires_adaptive_action: bool = False
    source_evidence: str = ""


class PathDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_manual_action: str
    path: Literal["A", "B", "C"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    clean_core_guardrail: str
    side_car_component: str
    regional_overrides: list[str] = Field(default_factory=list)


class ArchitectAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[PathDecision]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    trust_gap_ready: bool
    quality_feedback: list[str] = Field(default_factory=list)


class BlueprintArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_report_markdown: str
    mermaid_xml: str


class TrustGapStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: Literal["Shadow", "Co-Pilot", "Autopilot"] = "Shadow"
    approved: bool = False
    approver: str | None = None
    notes: str | None = None

