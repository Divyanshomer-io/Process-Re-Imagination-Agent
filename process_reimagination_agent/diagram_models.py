from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


NodeType = Literal["start_event", "task", "gateway", "end_event", "subprocess", "annotation", "unknown"]
EdgeType = Literal["sequence", "message", "association", "unknown"]
GatewayType = Literal["xor", "and", "or", "event", "none"]


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x0: float = Field(ge=0.0)
    y0: float = Field(ge=0.0)
    x1: float = Field(ge=0.0)
    y1: float = Field(ge=0.0)


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    text: str = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    bbox: BoundingBox | None = None


class DiagramNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    node_type: NodeType = "unknown"
    gateway_type: GatewayType = "none"
    lane: str | None = None
    page_number: int = Field(ge=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class DiagramEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    edge_type: EdgeType = "sequence"
    condition_label: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class DiagramLane(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lane_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class DiagramPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    page_type: Literal["text", "diagram", "mixed"] = "text"
    text_content: str = ""
    extraction_method: str = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    lanes: list[DiagramLane] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProcessGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str = Field(min_length=1)
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    lanes: list[DiagramLane] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    unresolved_edges: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class CanonicalDocumentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    pages: list[DiagramPage] = Field(default_factory=list)
    graph: ProcessGraph | None = None
    extraction_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
