from __future__ import annotations

from typing import Any, Literal, Required, TypedDict

from process_reimagination_agent.models import InputManifest

TrustGapPhase = Literal["Shadow", "Co-Pilot", "Autopilot"]
PathType = Literal["A", "B", "C"]


class AgentState(TypedDict, total=False):
    """LangGraph state for the 3-phase transformation workflow."""

    # Required persistent fields from the specification.
    raw_inputs: Required[dict[str, Any]]
    cognitive_friction_logs: Required[list[dict[str, Any]]]
    path_decisions: Required[list[dict[str, Any]]]
    refined_blueprint: Required[dict[str, Any]]

    # Decision-complete orchestration fields.
    process_name: str
    context_region: str
    pain_points: list[str]
    regional_nuances: dict[str, Any]
    evidence_references: list[dict[str, str]]
    canonical_documents: list[dict[str, Any]]
    process_graphs: list[dict[str, Any]]
    phase_status: dict[str, str]
    confidence_score: float
    trust_gap_phase: TrustGapPhase
    quality_feedback: list[str]
    refinement_iterations: int
    manual_approval: bool
    strategy_report_markdown: str
    mermaid_xml: str
    use_case_cards_json: str
    errors: list[str]
    quality_gate_result: Literal["refine", "blueprint", "escalate"]
    force_confidence_override: float
    path_classifier_prompt: str


def create_initial_state(manifest: InputManifest, trust_gap_phase: TrustGapPhase = "Shadow") -> AgentState:
    """Create a fully initialized agent state with mandatory phase placeholders."""
    return AgentState(
        raw_inputs={"manifest": manifest.model_dump()},
        cognitive_friction_logs=[],
        path_decisions=[],
        refined_blueprint={},
        process_name=manifest.process_name,
        context_region=manifest.context_region,
        pain_points=manifest.pain_points,
        regional_nuances={},
        evidence_references=[],
        canonical_documents=[],
        process_graphs=[],
        phase_status={
            "phase_1_current_reality_synthesis": "pending",
            "phase_2_agentic_reasoning": "pending",
            "phase_3_blueprint_generation": "pending",
        },
        confidence_score=0.0,
        trust_gap_phase=trust_gap_phase,
        quality_feedback=[],
        refinement_iterations=0,
        manual_approval=False,
        strategy_report_markdown="",
        mermaid_xml="",
        use_case_cards_json="",
        errors=[],
        quality_gate_result="refine",
    )
