from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateEngagementRequest(BaseModel):
    process_name: str = Field(min_length=3)
    context_region: str = Field(min_length=2)


class KpiItem(BaseModel):
    name: str = ""
    baseline: str = ""
    target: str = ""
    notes: str = ""
    id: str = ""


class UpdateEngagementRequest(BaseModel):
    process_name: str | None = None
    context_region: str | None = None
    pain_points: str | None = None
    pain_points_list: list[str] | None = None
    regional_variations: bool | None = None
    regional_nuances: str | None = None
    strategic_guardrails: str | None = None
    kpis: list[KpiItem] | None = None
    channel: str | None = None
    order_status: str | None = None


class ApproveRequest(BaseModel):
    approver: str = Field(min_length=1)
    notes: str = ""


# ---------------------------------------------------------------------------
# Response schemas — mirror the exact shapes the UI consumes
# ---------------------------------------------------------------------------

class EngagementMeta(BaseModel):
    id: str
    thread_id: str
    process_name: str
    region: str
    status: Literal["draft", "running", "ready", "error", "pending_approval"]
    created_at: datetime


class FileInfo(BaseModel):
    id: str
    name: str
    date: datetime
    category: Literal["as_is", "pain_point", "benchmark"]
    tag: str = ""


class UploadedFileResponse(BaseModel):
    id: str
    name: str
    date: datetime


class RunStatusResponse(BaseModel):
    status: Literal["draft", "running", "ready", "error", "pending_approval"]
    progress: float = 0.0
    current_phase: int = 0
    phase1_steps: list[StepStatus] = []
    phase2_steps: list[StepStatus] = []
    phase3_steps: list[StepStatus] = []
    error: str | None = None
    confidence_score: float | None = None
    quality_gate_result: str | None = None


class StepStatus(BaseModel):
    label: str
    status: Literal["pending", "running", "complete"] = "pending"


RunStatusResponse.model_rebuild()


# --- Results tab shapes (match mockResults.ts exactly) ---

class FrictionItemResponse(BaseModel):
    """Matches the UI's FrictionItem element shape."""
    id: str
    manualAction: str
    whereInProcess: str
    region: str
    whyItMatters: str
    evidenceText: str
    openQuestions: str
    evidenceCount: int
    relatedPainPoints: list[str]
    evidence: list[str]
    pathClassification: Literal["A", "B", "C"]


class PathItemResponse(BaseModel):
    """Matches the UI's mockPathData element shape."""
    item: str
    path: Literal["A", "B", "C"]
    suitabilityReason: str
    notes: str


class UseCaseResponse(BaseModel):
    """Matches the UI's mockUseCases element shape."""
    id: str
    title: str
    path: Literal["A", "B", "C"] | str
    sapTarget: str
    context: str
    agentRole: str
    mechanism: str
    tech: str
    value: str


class StrategyReportResponse(BaseModel):
    markdown: str


class BlueprintResponse(BaseModel):
    xml: str
    mermaid: str
    svg: str


class ApproveResponse(BaseModel):
    status: str
    message: str
