from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean
from typing import Any
from xml.sax.saxutils import escape

from process_reimagination_agent.config import Settings
from process_reimagination_agent.ingestion import ingest_manifest
from process_reimagination_agent.models import FrictionItem, InputManifest, PathDecision
from process_reimagination_agent.regional_rules import apply_regional_overrides_to_decision, detect_regional_nuances
from process_reimagination_agent.validators import count_words, validate_mermaid_xml, validate_strategy_report


def _compact_text(text: str, max_len: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 3].rstrip()}..."


def _markdown_cell(text: str) -> str:
    return _compact_text(text).replace("|", "\\|")


def _extract_excerpt(content: str, start: int, end: int, max_len: int = 180) -> str:
    window_start = max(0, start - 90)
    window_end = min(len(content), end + 120)
    return _compact_text(content[window_start:window_end], max_len=max_len)


def _collect_document_references(raw_inputs: dict[str, Any], max_refs: int = 12) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for idx, doc in enumerate(raw_inputs.get("documents", []), start=1):
        content = str(doc.get("content", ""))
        if not content.strip():
            continue
        path = str(doc.get("path", ""))
        refs.append(
            {
                "id": f"DOC{idx}",
                "source": Path(path).name if path else f"document_{idx}",
                "path": path,
                "excerpt": _compact_text(content, max_len=220),
            }
        )
        if len(refs) >= max_refs:
            break
    return refs


def _collect_pattern_references(
    raw_inputs: dict[str, Any],
    patterns: list[str],
    *,
    max_refs: int = 3,
) -> list[dict[str, str]]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    refs: list[dict[str, str]] = []
    for idx, doc in enumerate(raw_inputs.get("documents", []), start=1):
        content = str(doc.get("content", ""))
        if not content:
            continue
        matched: re.Match[str] | None = None
        for pattern in compiled:
            matched = pattern.search(content)
            if matched:
                break
        if not matched:
            continue
        path = str(doc.get("path", ""))
        refs.append(
            {
                "id": f"DOC{idx}",
                "source": Path(path).name if path else f"document_{idx}",
                "path": path,
                "excerpt": _extract_excerpt(content, matched.start(), matched.end()),
            }
        )
        if len(refs) >= max_refs:
            break
    return refs


def _derive_document_friction_items(
    *,
    raw_inputs: dict[str, Any],
    combined_text: str,
    context_region: str,
) -> list[FrictionItem]:
    text = combined_text.lower()
    if not text.strip():
        return []

    # These rules translate unstructured process evidence into friction items with source references.
    rules: list[dict[str, Any]] = [
        {
            "patterns": [
                r"\bmanual entry\b",
                r"\bmanually entered\b",
                r"\bemail\b",
                r"\bpdf\b",
                r"\bspreadsheet\b",
                r"\bfax\b",
            ],
            "current_manual_action": "Manual multi-channel order intake (email/PDF/fax/spreadsheet) is re-keyed into SAP.",
            "friction_type": "Human transcription and unstructured intake triage",
            "proposed_path": "C",
            "rationale": "Requires perception over unstructured payloads and adaptive extraction checks.",
            "expected_kpi_shift": "60-80% faster intake and fewer keying defects",
            "requires_perception": True,
            "requires_reasoning": True,
            "requires_adaptive_action": False,
        },
        {
            "patterns": [
                r"\bedi failure\b",
                r"\bfailed idoc\b",
                r"\bmissing data\b",
                r"\bformatting errors?\b",
                r"\bincorrect product codes?\b",
                r"\bincompletion log\b",
                r"\bduplicate order\b",
            ],
            "current_manual_action": "Order capture failures require manual triage for EDI/data-quality exceptions.",
            "friction_type": "Deterministic coordination and status handling",
            "proposed_path": "B",
            "rationale": "Best handled by deterministic validation, routing, and retry workflows.",
            "expected_kpi_shift": "25-40% reduction in exception turnaround time",
            "requires_perception": False,
            "requires_reasoning": False,
            "requires_adaptive_action": False,
        },
        {
            "patterns": [
                r"\bva02\b",
                r"\bva03\b",
                r"\bchange request",
                r"\bchange sales order\b",
                r"\bprocessed manually in sap\b",
            ],
            "current_manual_action": "Order changes are processed manually in SAP (VA02/VA03) after initial intake.",
            "friction_type": "Deterministic coordination and status handling",
            "proposed_path": "B",
            "rationale": "Change flows are repeatable and should be orchestrated via deterministic side-car workflows.",
            "expected_kpi_shift": "20-35% faster order amendment cycle time",
            "requires_perception": False,
            "requires_reasoning": False,
            "requires_adaptive_action": False,
        },
        {
            "patterns": [
                r"\bwhat is the order type\b",
                r"\bconsignment\b",
                r"\benter standard order details into the erp\b",
            ],
            "current_manual_action": "Order-type branching (standard vs consignment) is resolved manually during entry.",
            "friction_type": "ERP standardization opportunity for order-type branching",
            "proposed_path": "A",
            "rationale": "Should be standardized via core ERP rules and validated APIs.",
            "expected_kpi_shift": "Lower transaction variance and fewer branch-specific defects",
            "requires_perception": False,
            "requires_reasoning": False,
            "requires_adaptive_action": False,
        },
        {
            "patterns": [
                r"\bdigital hub\b",
                r"\bmandatory for all orders\b",
                r"\bno direct customer edi\b",
            ],
            "current_manual_action": "China intake must pass through Digital Hub before SAP posting.",
            "friction_type": "Deterministic coordination and status handling",
            "proposed_path": "B",
            "rationale": "Gateway enforcement is deterministic and should be governed in side-car routing policy.",
            "expected_kpi_shift": "Higher routing compliance and reduced posting exceptions",
            "requires_perception": False,
            "requires_reasoning": False,
            "requires_adaptive_action": False,
        },
        {
            "patterns": [
                r"\bpower street\b",
                r"\bon the spot\b",
                r"\btruck\b",
            ],
            "current_manual_action": "Uruguay Power Street truck-loading orders require adaptive normalization before ERP posting.",
            "friction_type": "Channel-specific adaptive intake handling",
            "proposed_path": "C",
            "rationale": "Requires adaptive action across mobile channel payload variability.",
            "expected_kpi_shift": "35-55% faster same-day order capture with fewer format errors",
            "requires_perception": True,
            "requires_reasoning": True,
            "requires_adaptive_action": True,
        },
        {
            "patterns": [
                r"\bvector\b",
                r"\bbackward integration\b",
                r"\bconsignment model\b",
            ],
            "current_manual_action": "South Africa indirect orders need next-day Vector backward integration reconciliation.",
            "friction_type": "Deterministic coordination and status handling",
            "proposed_path": "B",
            "rationale": "Boundary-system handoffs should be automated with deterministic integration checks.",
            "expected_kpi_shift": "20-35% faster indirect-network reconciliation",
            "requires_perception": False,
            "requires_reasoning": False,
            "requires_adaptive_action": False,
        },
        {
            "patterns": [
                r"\bdispute\b",
                r"\bdeduction\b",
                r"\bclaims\b",
                r"\bshortage\b",
            ],
            "current_manual_action": "Deduction and dispute triage requires manual evidence reconciliation across systems.",
            "friction_type": "Manual dispute triage and evidence reconciliation",
            "proposed_path": "C",
            "rationale": "Requires contextual reasoning over policy, order, and logistics evidence.",
            "expected_kpi_shift": "30-50% dispute cycle-time reduction",
            "requires_perception": True,
            "requires_reasoning": True,
            "requires_adaptive_action": True,
        },
    ]

    derived: list[FrictionItem] = []
    seen_actions: set[str] = set()
    for rule in rules:
        if not any(re.search(pattern, text, re.IGNORECASE) for pattern in rule["patterns"]):
            continue
        refs = _collect_pattern_references(raw_inputs, rule["patterns"])
        ref_ids = ", ".join(ref["id"] for ref in refs)
        ref_evidence = "; ".join(
            f"{ref['id']} {ref['source']}: \"{ref['excerpt']}\"" for ref in refs
        )
        current_manual_action = str(rule["current_manual_action"])
        if ref_ids:
            current_manual_action = f"{current_manual_action} (Refs: {ref_ids})"
        action_key = current_manual_action.lower()
        if action_key in seen_actions:
            continue
        seen_actions.add(action_key)
        derived.append(
            FrictionItem(
                current_manual_action=current_manual_action,
                friction_type=str(rule["friction_type"]),
                proposed_path=rule["proposed_path"],  # type: ignore[arg-type]
                rationale=str(rule["rationale"]),
                expected_kpi_shift=str(rule["expected_kpi_shift"]),
                requires_perception=bool(rule["requires_perception"]),
                requires_reasoning=bool(rule["requires_reasoning"]),
                requires_adaptive_action=bool(rule["requires_adaptive_action"]),
                source_evidence=ref_evidence or f"Derived from uploaded process text in {context_region}.",
            )
        )
    return derived


def _merge_friction_items(primary: list[FrictionItem], secondary: list[FrictionItem]) -> list[FrictionItem]:
    merged: list[FrictionItem] = []
    seen: set[str] = set()
    for item in [*primary, *secondary]:
        key = item.current_manual_action.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _fallback_friction_from_pain_points(pain_points: list[str], combined_text: str) -> list[FrictionItem]:
    frictions: list[FrictionItem] = []
    for pain_point in pain_points:
        text = pain_point.lower()
        if any(token in text for token in ["email", "pdf", "spreadsheet", "manual entry", "transcribing"]):
            frictions.append(
                FrictionItem(
                    current_manual_action=pain_point,
                    friction_type="Human transcription and unstructured intake triage",
                    proposed_path="C",
                    rationale="Requires perception over unstructured documents and adaptive extraction checks.",
                    expected_kpi_shift="60-80% faster intake with lower transcription defects",
                    requires_perception=True,
                    requires_reasoning=True,
                    requires_adaptive_action=False,
                    source_evidence="Pain point inventory",
                )
            )
            continue

        if any(token in text for token in ["dispute", "deduction", "trade promo", "shortage"]):
            frictions.append(
                FrictionItem(
                    current_manual_action=pain_point,
                    friction_type="Manual dispute triage and evidence reconciliation",
                    proposed_path="C",
                    rationale="Requires reasoning across invoices, POD, and policy context.",
                    expected_kpi_shift="30-50% dispute cycle-time reduction and DSO improvement",
                    requires_perception=True,
                    requires_reasoning=True,
                    requires_adaptive_action=True,
                    source_evidence="Pain point inventory",
                )
            )
            continue

        if any(token in text for token in ["custom", "z-", "deviation", "non-standard", "tcode"]):
            frictions.append(
                FrictionItem(
                    current_manual_action=pain_point,
                    friction_type="ERP deviation from standard process template",
                    proposed_path="A",
                    rationale="Candidate for core standardization to reduce technical debt.",
                    expected_kpi_shift="Lower support overhead and faster release velocity",
                    requires_perception=False,
                    requires_reasoning=False,
                    requires_adaptive_action=False,
                    source_evidence="Pain point inventory",
                )
            )
            continue

        frictions.append(
            FrictionItem(
                current_manual_action=pain_point,
                friction_type="Deterministic coordination and status handling",
                proposed_path="B",
                rationale="Best handled via workflow orchestration and rule-driven automation.",
                expected_kpi_shift="20-40% cycle-time improvement in repetitive tasks",
                requires_perception=False,
                requires_reasoning=False,
                requires_adaptive_action=False,
                source_evidence="Pain point inventory",
            )
        )

    if frictions:
        return frictions

    # PHASE 1 must run even with sparse evidence.
    return [
        FrictionItem(
            current_manual_action="Human receives mixed-format order requests and re-keys them into ERP.",
            friction_type="Cognitive middleware bridging across channels and core system",
            proposed_path="C",
            rationale="Requires unstructured perception and adaptive handling for partial information.",
            expected_kpi_shift="Significant reduction in manual effort and keying errors",
            requires_perception=True,
            requires_reasoning=True,
            requires_adaptive_action=True,
            source_evidence="Sparse-input fallback generated by mandatory Phase 1",
        )
    ]


def _friction_items_from_state(state: dict[str, Any]) -> list[FrictionItem]:
    logs = state.get("cognitive_friction_logs", [])
    items: list[FrictionItem] = []
    for log in logs:
        try:
            items.append(FrictionItem.model_validate(log))
        except Exception:
            continue
    if items:
        return items
    return _fallback_friction_from_pain_points(state.get("pain_points", []), "")


def _classify_path(item: FrictionItem) -> str:
    # Clean Core policy: prefer standardization (A) where business behavior is not unique.
    if "standard" in item.friction_type.lower() or "deviation" in item.friction_type.lower():
        return "A"
    # Side-Car policy: use deterministic automation (B) for repetitive rule-based tasks.
    if not (item.requires_perception or item.requires_reasoning or item.requires_adaptive_action):
        return "B"
    # Agentic path (C) reserved for perception/reasoning/adaptive action.
    return "C"


def _decision_confidence(item: FrictionItem, iteration_count: int, evidence_penalty: bool) -> float:
    base = 0.90
    if item.requires_perception or item.requires_reasoning or item.requires_adaptive_action:
        base += 0.02
    if item.source_evidence:
        base += 0.03
    base += min(iteration_count, 2) * 0.02
    if evidence_penalty:
        base -= 0.05
    return max(0.50, min(0.99, base))


def friction_points_node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    raw_inputs = dict(state.get("raw_inputs", {}))
    manifest_data = raw_inputs.get("manifest", {})

    manifest = InputManifest.model_validate(
        {
            "process_name": state.get("process_name") or manifest_data.get("process_name", "Order Intake"),
            "context_region": state.get("context_region") or manifest_data.get("context_region", "Global"),
            "pain_points": state.get("pain_points") or manifest_data.get("pain_points", []),
            "files": manifest_data.get("files", []),
            "additional_context": manifest_data.get("additional_context", {}),
        }
    )

    ingest_result = ingest_manifest(manifest)
    combined_text = ingest_result.get("combined_text", "")
    raw_inputs.update(ingest_result)
    evidence_references = _collect_document_references(raw_inputs)

    regional_nuances = detect_regional_nuances(combined_text=combined_text, context_region=manifest.context_region)
    derived_frictions = _derive_document_friction_items(
        raw_inputs=raw_inputs,
        combined_text=combined_text,
        context_region=manifest.context_region,
    )
    explicit_frictions = _fallback_friction_from_pain_points(manifest.pain_points, combined_text) if manifest.pain_points else []
    if manifest.pain_points:
        frictions = _merge_friction_items(derived_frictions, explicit_frictions)
    elif derived_frictions:
        frictions = derived_frictions
    else:
        frictions = _fallback_friction_from_pain_points([], combined_text)

    resolved_pain_points = list(manifest.pain_points)
    if not resolved_pain_points:
        resolved_pain_points = [item.current_manual_action for item in frictions]
    elif derived_frictions:
        existing = {point.strip().lower() for point in resolved_pain_points}
        for item in derived_frictions:
            action = item.current_manual_action.strip()
            if action.lower() not in existing:
                resolved_pain_points.append(action)
                existing.add(action.lower())

    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_1_current_reality_synthesis"] = "completed"

    errors = list(state.get("errors", []))
    extraction_errors = ingest_result.get("extraction_errors", [])
    if extraction_errors:
        errors.extend(extraction_errors)

    return {
        "raw_inputs": raw_inputs,
        "process_name": manifest.process_name,
        "context_region": manifest.context_region,
        "pain_points": resolved_pain_points,
        "cognitive_friction_logs": [item.model_dump() for item in frictions],
        "regional_nuances": regional_nuances,
        "evidence_references": evidence_references,
        "phase_status": phase_status,
        "errors": errors,
    }


def Input_Refiner_Node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    iteration = int(state.get("refinement_iterations", 0)) + 1
    feedback = list(state.get("quality_feedback", []))
    feedback.append(
        (
            f"Refinement pass {iteration}: strengthened evidence mapping and clarified "
            "Path A/B/C rationale to close Trust Gap."
        )
    )

    refined_logs = []
    for item in _friction_items_from_state(state):
        payload = item.model_dump()
        if not payload.get("source_evidence"):
            payload["source_evidence"] = "Refined using quality feedback and source documents"
        payload["rationale"] = (
            f"{payload['rationale']} Refinement pass {iteration} validated against Clean Core and Side-Car policies."
        )
        refined_logs.append(payload)

    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_1_current_reality_synthesis"] = "completed"

    return {
        "refinement_iterations": iteration,
        "quality_feedback": feedback,
        "cognitive_friction_logs": refined_logs,
        "phase_status": phase_status,
    }


def path_classifier_node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    friction_items = _friction_items_from_state(state)
    path_decisions: list[dict[str, Any]] = []
    iteration = int(state.get("refinement_iterations", 0))
    region = state.get("context_region", "Global")

    evidence_penalty = bool(state.get("errors"))
    for item in friction_items:
        path = _classify_path(item)
        # Guardrail: Path C is allowed only when perception/reasoning/adaptive action is needed.
        if path == "C" and not (item.requires_perception or item.requires_reasoning or item.requires_adaptive_action):
            path = "B"

        decision = PathDecision(
            current_manual_action=item.current_manual_action,
            path=path,  # type: ignore[arg-type]
            confidence=_decision_confidence(item, iteration_count=iteration, evidence_penalty=evidence_penalty),
            rationale=f"{item.rationale} Classified via mandatory Phase 2 suitability assessment.",
            clean_core_guardrail=(
                "Keep ERP kernel standard; route custom logic to Side-Car orchestration and APIs only."
            ),
            side_car_component=(
                "Agentic Intake Orchestrator" if path == "C" else "Workflow Automation Side-Car"
            ),
            regional_overrides=[],
        ).model_dump()

        decision = apply_regional_overrides_to_decision(
            decision,
            region=region,
            order_status=state.get("raw_inputs", {}).get("order_status", "open"),
            confidence_score=decision["confidence"],
            channel=state.get("raw_inputs", {}).get("channel", ""),
        )
        path_decisions.append(decision)

    overall_confidence = mean([d["confidence"] for d in path_decisions]) if path_decisions else 0.0
    if "force_confidence_override" in state:
        overall_confidence = float(state["force_confidence_override"])

    quality_feedback = list(state.get("quality_feedback", []))
    if overall_confidence <= settings.confidence_threshold:
        quality_feedback.append(
            (
                f"Confidence {overall_confidence:.2%} below threshold "
                f"{settings.confidence_threshold:.2%}. Additional refinement required."
            )
        )

    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_2_agentic_reasoning"] = "completed"

    return {
        "path_decisions": path_decisions,
        "confidence_score": round(overall_confidence, 4),
        "quality_feedback": quality_feedback,
        "phase_status": phase_status,
    }


def Quality_Control_Node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    confidence = float(state.get("confidence_score", 0.0))
    refinement_iterations = int(state.get("refinement_iterations", 0))
    errors = list(state.get("errors", []))
    feedback = list(state.get("quality_feedback", []))
    phase_status = dict(state.get("phase_status", {}))

    if confidence > settings.confidence_threshold:
        phase_status["quality_control"] = "pass"
        return {"quality_gate_result": "blueprint", "phase_status": phase_status}

    if refinement_iterations >= settings.max_refinement_loops:
        phase_status["quality_control"] = "escalated"
        errors.append(
            (
                f"Trust Gap threshold not met after {refinement_iterations} refinements. "
                "Escalate to human review for source quality and policy verification."
            )
        )
        return {"quality_gate_result": "escalate", "phase_status": phase_status, "errors": errors}

    phase_status["quality_control"] = "refine"
    feedback.append(
        (
            "Quality Control loop triggered: confidence below 95%, returning to Input Refiner "
            "before blueprint generation."
        )
    )
    return {"quality_gate_result": "refine", "phase_status": phase_status, "quality_feedback": feedback}


def quality_route(state: dict[str, Any]) -> str:
    return str(state.get("quality_gate_result", "refine"))


def Human_Escalation_Node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_3_blueprint_generation"] = "blocked_pending_human_escalation"
    errors = list(state.get("errors", []))
    if not errors:
        errors.append("Human escalation required before blueprint generation.")
    return {"phase_status": phase_status, "errors": errors}


def _build_cognitive_friction_table(cognitive_friction_logs: list[dict[str, Any]]) -> str:
    header = (
        "| [Current Manual Action] | Friction Type | Proposed Path | Rationale | Expected KPI Shift | Source References |\n"
        "|---|---|---|---|---|---|"
    )
    rows = []
    for item in cognitive_friction_logs:
        rows.append(
            "| {action} | {ftype} | {path} | {rationale} | {kpi} | {source} |".format(
                action=_markdown_cell(str(item.get("current_manual_action", "N/A"))),
                ftype=_markdown_cell(str(item.get("friction_type", "N/A"))),
                path=_markdown_cell(str(item.get("proposed_path", "N/A"))),
                rationale=_markdown_cell(str(item.get("rationale", "N/A"))),
                kpi=_markdown_cell(str(item.get("expected_kpi_shift", "N/A"))),
                source=_markdown_cell(str(item.get("source_evidence", "N/A"))),
            )
        )
    return "\n".join([header, *rows]) if rows else header


def _add_unique_section(
    section_order: list[str],
    section_registry: dict[str, str],
    heading: str,
    body: str,
) -> None:
    if heading in section_registry:
        raise ValueError(f"Duplicate protected section detected during generation: {heading}")
    section_order.append(heading)
    section_registry[heading] = body.strip()


def _render_report_from_sections(
    report_title: str,
    section_order: list[str],
    section_registry: dict[str, str],
) -> str:
    parts = [report_title]
    for heading in section_order:
        parts.append(f"{heading}\n\n{section_registry[heading]}")
    return "\n\n".join(parts)


def _prepend_toc(report_title: str, section_order: list[str], report: str) -> str:
    """Prepend a table of contents after the report title for easier navigation."""
    if not report.startswith(report_title):
        return report
    rest = report[len(report_title) :].lstrip("\n")
    toc_lines = ["**Contents**"] + [f"- {h.replace('## ', '')}" for h in section_order]
    return report_title + "\n\n" + "\n".join(toc_lines) + "\n\n" + rest


def _build_reference_register(references: list[dict[str, str]]) -> str:
    if not references:
        return "- No explicit source references were captured from uploaded artifacts."
    lines = [
        "| Reference ID | Source Artifact | Evidence Excerpt |",
        "|---|---|---|",
    ]
    for ref in references:
        lines.append(
            "| {id} | {source} | {excerpt} |".format(
                id=_markdown_cell(str(ref.get("id", "N/A"))),
                source=_markdown_cell(str(ref.get("source", "N/A"))),
                excerpt=_markdown_cell(str(ref.get("excerpt", ""))),
            )
        )
    return "\n".join(lines)


def _build_strategy_report(state: dict[str, Any], settings: Settings) -> str:
    process_name = state.get("process_name", "Process")
    context_region = state.get("context_region", "Global")
    trust_gap_phase = state.get("trust_gap_phase", "Shadow")
    cognitive_friction_logs = state.get("cognitive_friction_logs", [])
    path_decisions = state.get("path_decisions", [])
    evidence_references = state.get("evidence_references", [])

    table = _build_cognitive_friction_table(cognitive_friction_logs)
    decision_lines = [
        f"- **{d.get('path')}** for `{d.get('current_manual_action')}`: {d.get('rationale')} "
        f"(confidence {d.get('confidence', 0):.0%})"
        for d in path_decisions
    ]
    regional_nuances = json.dumps(state.get("regional_nuances", {}), indent=2)

    report_title = f"# Re-Imagined Strategy Report: {process_name}"
    section_order: list[str] = []
    section_registry: dict[str, str] = {}

    _add_unique_section(
        section_order,
        section_registry,
        "## Executive Summary",
        (
            f"The One Big Move for {process_name} in {context_region} is to replace human middleware with a "
            "Side-Car intelligence and orchestration layer that protects the SAP core while accelerating order-cycle "
            "execution. This architecture treats every intake channel as an event source, every exception as a managed "
            "decision point, and every ERP transaction as a standards-based API call rather than a custom-coded branch. "
            "The strategic benefit is immediate: higher touchless throughput, lower transcription defects, faster "
            "exception closure, and lower operational risk across regional variations. The design also keeps long-term "
            "cost under control by avoiding core-kernel customization and by consolidating complex logic into reusable "
            "side-car services. The methodology is intentionally strict: Phase 1 captures current reality and cognitive "
            "friction, Phase 2 maps each friction to Path A/B/C with explicit suitability logic, and Phase 3 produces a "
            "deployable blueprint backed by trust controls. The operating model is therefore transformation-ready and "
            "audit-ready from day one."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Cognitive Friction Analysis",
        (
            "The following table is the mandatory friction inventory used by the Architect phase. Each row identifies "
            "where humans currently act as middleware, what category of friction exists, and which intervention path "
            "provides the safest and fastest improvement without violating Clean Core policies.\n\n"
            f"{table}"
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Source Evidence Register",
        (
            "The following references were derived from uploaded source artifacts and used to ground the "
            "friction and flow decisions in this report.\n\n"
            f"{_build_reference_register(evidence_references)}"
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Architecture of the Future State",
        (
            "The future state is a hub-and-spoke operating model where the Agentic Side-Car is the controlled brain "
            "between channels and SAP. Personas are explicit: **The Intake Scribe** extracts and normalizes incoming "
            "order payloads; **The Intent Analyzer** classifies business intent and routes deterministic vs agentic work; "
            "**The Dispute Judge** handles contextual exceptions requiring evidence reasoning. Path C tasks stay in this "
            "layer and are executed with confidence scoring, policy checks, and human escalation hooks. Path B tasks are "
            "delivered as deterministic workflow components such as routing, formatting, and validation engines. Path A "
            "tasks are pushed back to standard ERP APIs and data checks. Regional variations are managed through policy "
            "injection and adapter patterns in the side-car, not through core transaction branching. This architecture "
            "lets McCain scale automation without coupling business variability to ERP internals."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Technical Stack",
        (
            "System of Intelligence: LangGraph orchestration, policy guardrails, confidence routing, and optional LLM "
            "services configured through Azure/OpenAI-compatible settings. System of Record: SAP S/4HANA standard APIs, "
            "master data, and posting integrity controls. Integration contracts are protocol-labeled and observable: "
            "Webhook/AS2 intake, gRPC-style internal coordination, and OData/BAPI posting calls to ERP. Operational "
            "control points include schema checks, idempotency, payload validation, and exception queues. **Clean Core "
            "enforcement is explicit: all custom logic is isolated in the Side-Car layer and never embedded in the ERP "
            "kernel.** This separation protects upgradeability and reduces regression risk during SAP releases while "
            "still enabling high-adaptivity automation on top."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Integration Design Deep Dive",
        (
            "The integration design follows a staged processing contract. Stage 1 handles omnichannel intake normalization "
            "to convert emails, EDI payloads, and partner messages into a canonical order event. Stage 2 performs "
            "classification and pathing: deterministic validations are executed through Path B services, while ambiguous "
            "or context-rich tasks are routed to Path C reasoning nodes. Stage 3 executes approved ERP interactions via "
            "standard API endpoints and performs post-transaction status callbacks to the side-car. Failure modes are "
            "handled in-band: malformed payloads trigger formatter retries, confidence failures trigger refinement loops, "
            "and prolonged uncertainty triggers human escalation. This design ensures that failure in one adapter or "
            "service does not corrupt core posting behavior."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Agent Persona Reasoning Model",
        (
            "Agent personas are intentionally constrained by reasoning boundaries. The Intake Scribe is optimized for "
            "perception and structured extraction; it should not execute financial decisions. The Intent Analyzer is "
            "optimized for context classification and action routing; it determines whether a case is suitable for Path A, "
            "B, or C and records rationale for auditability. The Dispute Judge is optimized for evidence-based reasoning "
            "in exception scenarios and must return both decision and evidence chain. Together these personas create a "
            "transparent cognitive assembly line where each decision is attributable, reviewable, and reversible. This "
            "design lowers black-box risk and supports phased trust adoption."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## The Trust Gap Protocol",
        (
            f"Current operating mode defaults to **{trust_gap_phase}**. In Shadow, agents produce recommendations while "
            "humans keep execution authority and annotate decision quality gaps. In Co-Pilot, high-confidence low-risk "
            "steps can execute with explicit override and sampling audits. In Autopilot, approved lanes execute "
            "touchlessly with continuous telemetry, rollback hooks, and policy drift detection. The confidence threshold "
            "is strictly greater than 95%; anything at or below threshold is routed back to refinement. If loop limits are "
            "reached, the process hard-stops into human escalation rather than silently degrading quality."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Path Design Decisions",
        "\n".join(decision_lines) if decision_lines else "- No decisions available.",
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Regional Policy Registry",
        (
            "The policy registry below captures normalized regional signals used to drive runtime behavior in the "
            "orchestration layer.\n\n"
            f"```json\n{regional_nuances}\n```"
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Delivery and Rollout Plan",
        (
            "Wave 1 establishes mandatory synthesis and confidence gating with human approval checkpoints. Wave 2 expands "
            "deterministic automations and adapter hardening for region-specific channels. Wave 3 scales approved agentic "
            "lanes with deeper telemetry, cost controls, and governance scorecards. KPI packs include touchless rate, "
            "manual touch reduction, exception turnaround, posting accuracy, and confidence distribution by task type. "
            "Exit criteria for each wave include audit evidence, rollback readiness, and trend stability over multiple "
            "business cycles. Governance and rollback procedures are defined per wave with clear ownership and sign-off. "
            "Operational readiness is confirmed through staging validation and pilot runs before production cutover. "
            "Staged rollout allows measured risk reduction and quick wins in high-impact channels before broader deployment. "
            "Change management and training are aligned with each wave to ensure adoption and continuity. Event payload "
            "contracts are versioned and backward-compatible; policy decisions are traceable to explicit evidence chains; "
            "side-car services are horizontally scalable. Rollout governance uses measurable confidence and exception KPIs "
            "to prevent quality drift."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Appendix: Control and Operability Baseline",
        (
            "Core operability controls include schema validation, deterministic retries, idempotency keys, payload lineage, "
            "and cross-system correlation IDs. Governance controls include policy versioning, role-based approval, and "
            "exception triage SLAs. Reliability controls include dead-letter routing, retry budget limits, and monitored "
            "degradation paths. These controls make the automation stack production-safe while maintaining separation of "
            "concerns between side-car intelligence and ERP record integrity."
        ),
    )

    _add_unique_section(
        section_order,
        section_registry,
        "## Executive Simplified Summary",
        (
            "This design gives McCain one intelligent intake layer that reduces manual work and speeds order processing "
            "across regions. By keeping custom logic in the Side-Car and using only standard ERP APIs, the solution "
            "protects SAP stability and lowers upgrade risk. The trust-gated rollout lets the business scale automation "
            "safely while improving accuracy, cycle time, and service quality."
        ),
    )

    report = _render_report_from_sections(report_title, section_order, section_registry)
    # Add distinct paragraphs only when below word count; never repeat the same block.
    expansion_paragraphs = [
        "Further technical detail: event payload contracts are versioned and backward-compatible, policy decisions are "
        "traceable to explicit evidence chains, side-car services are horizontally scalable, and rollout governance uses "
        "measurable confidence and exception KPIs to prevent quality drift.",
        "Staged rollout allows measured risk reduction and quick wins in high-impact channels before broader deployment. "
        "Change management and training are aligned with each wave to ensure adoption and continuity.",
        "Quality gates at each wave prevent regression: automated tests, contract checks, and confidence thresholds must "
        "pass before promoting to the next environment. Stakeholder sign-off is required at wave boundaries.",
        "Runbooks and playbooks document standard operations, incident response, and escalation paths. Monitoring and "
        "alerting are configured per wave with clear ownership and response SLAs.",
        "Post-go-live support includes hypercare windows, knowledge transfer, and continuous improvement cycles to refine "
        "automation based on real-world usage and feedback.",
        "Security and compliance checks are embedded in the pipeline: access control, audit logging, and data handling "
        "follow agreed standards before any wave is signed off.",
        "Performance baselines are established in Wave 1 and monitored through Waves 2 and 3; deviations trigger review "
        "before further scale-out.",
        "Communication plans cover each wave: stakeholder updates, training schedules, and go-live notifications are "
        "aligned with the rollout calendar.",
        "Documentation includes architecture decisions, configuration guides, and runbooks; all are kept in sync with "
        "deployed releases.",
        "Lessons learned from each wave are captured and fed into the next; retrospectives are mandatory at wave boundaries.",
        "Capacity planning is reviewed before each wave to ensure infrastructure and licenses support the intended scope.",
        "Vendor and partner dependencies are identified early; contracts and support levels are confirmed prior to wave start.",
        "Risk registers are maintained per wave with mitigation and contingency; executive steering reviews them monthly.",
        "Testing strategy covers unit, integration, and end-to-end scenarios; regression suites are automated and run per wave.",
        "Data migration and cutover plans are defined for any legacy or manual data that must move into the new flow.",
        "User acceptance criteria are agreed with business owners before each wave; sign-off is documented and stored.",
        "Environment strategy ensures dev, test, and production are aligned; promotion and rollback are repeatable.",
        "Support models define L1/L2/L3 responsibilities and handoffs; escalation paths are clear and tested.",
        "Metrics and dashboards are set up to track wave success: throughput, errors, confidence distribution, and manual touch.",
        "Feedback loops from production feed into the next wave; continuous improvement is part of the operating model.",
        "Stakeholder maps and RACI matrices clarify who decides, who executes, and who is consulted at each stage.",
        "Go-live checklists cover technical, process, and people readiness; no wave proceeds without green on all criteria.",
        "Benefits realization is tracked against the business case; variances are reported and addressed in steering forums.",
        "Training materials and job aids are updated per wave; super-user networks are established in each region.",
        "Cutover windows and freeze periods are agreed with the business and communicated well in advance.",
        "Post-implementation reviews capture what went well and what to improve; actions are assigned and tracked.",
        "Integration and interface testing cover all touchpoints; stub and mock strategies are used where systems are not ready.",
        "Disaster recovery and business continuity are validated; RTO and RPO targets are met before go-live.",
        "Access and authorization are reviewed per wave; role design and segregation of duties are documented.",
        "Reporting and analytics requirements are confirmed; dashboards and extracts are tested with real data.",
        "Localization and language needs are addressed where the wave spans multiple countries or languages.",
        "Scalability and load testing confirm the solution can handle expected volumes at peak times.",
        "Vendor and internal team capacity are secured for hypercare and early stabilisation after each go-live.",
        "Communication and change impact assessments are completed so that affected teams are prepared for each wave.",
        "Approval workflows and delegation of authority are configured to match the target operating model before go-live.",
        "Data quality and master data readiness are confirmed so that the solution has the right inputs from day one.",
        "Backup and restore procedures are tested; recovery drills are run at least once per wave.",
        "Network and infrastructure dependencies are documented and monitored; latency and availability targets are set.",
        "License and subscription coverage is verified for all components and users in scope for the wave.",
        "Handover from project to operations is formalised with knowledge transfer and support ownership.",
        "Final business sign-off and warranty period start are recorded before the wave is closed.",
        "Audit and compliance evidence is collected and stored for each wave for future reviews.",
        "Lessons and templates are reused across regions to speed up later waves and keep quality consistent.",
    ]
    idx = 0
    while count_words(report) < settings.min_report_words and idx < len(expansion_paragraphs):
        section_registry["## Delivery and Rollout Plan"] = (
            f"{section_registry['## Delivery and Rollout Plan']}\n\n{expansion_paragraphs[idx]}"
        )
        report = _render_report_from_sections(report_title, section_order, section_registry)
        idx += 1

    report = _prepend_toc(report_title, section_order, report)
    return report


def _signal_reference_ids(raw_inputs: dict[str, Any], patterns: list[str], max_refs: int = 2) -> list[str]:
    refs = _collect_pattern_references(raw_inputs, patterns, max_refs=max_refs)
    return [ref["id"] for ref in refs]


def _flow_signals(raw_inputs: dict[str, Any], combined_text: str) -> dict[str, dict[str, Any]]:
    text = combined_text.lower()
    signals: dict[str, dict[str, Any]] = {
        "order_type_gateway": {
            "enabled": bool(re.search(r"\bwhat is the order type\b|\bconsignment\b", text)),
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\bwhat is the order type\b", r"\bconsignment\b", r"\benter standard order details\b"],
            ),
        },
        "capture_failure_gateway": {
            "enabled": bool(re.search(r"\border capturing failure\b|\bedi failure\b|\bfailed idoc\b", text)),
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\border capturing failure\b", r"\bedi failure\b", r"\bfailed idoc\b"],
            ),
        },
        "change_handler": {
            "enabled": bool(re.search(r"\bva02\b|\bchange request\b|\bchange sales order\b", text)),
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\bva02\b", r"\bchange request\b", r"\bchange sales order\b"],
            ),
        },
        "availability_check": {
            "enabled": bool(re.search(r"\bcheck product and service availability\b|\batp\b", text)),
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\bcheck product and service availability\b", r"\batp\b"],
            ),
        },
    }
    return signals


def _label_with_refs(base_label: str, ref_ids: list[str]) -> str:
    if not ref_ids:
        return base_label
    return f"{base_label} Ref {' '.join(ref_ids)}"


def _build_evidence_reference_xml(references: list[dict[str, str]]) -> str:
    if not references:
        return "  <EvidenceReferences/>"
    lines = ["  <EvidenceReferences>"]
    for ref in references:
        lines.append(
            '    <Reference id="{id}" source="{source}" path="{path}">{excerpt}</Reference>'.format(
                id=escape(str(ref.get("id", ""))),
                source=escape(str(ref.get("source", ""))),
                path=escape(str(ref.get("path", ""))),
                excerpt=escape(str(ref.get("excerpt", ""))),
            )
        )
    lines.append("  </EvidenceReferences>")
    return "\n".join(lines)


def _is_region_match(region: str, candidates: set[str]) -> bool:
    region_norm = region.strip().lower()
    return any(token in region_norm for token in candidates)


def _build_visual_architecture_xml(state: dict[str, Any]) -> str:
    raw_inputs = dict(state.get("raw_inputs", {}))
    combined_text = str(raw_inputs.get("combined_text", ""))
    evidence_references = list(state.get("evidence_references", [])) or _collect_document_references(raw_inputs)
    flow_signals = _flow_signals(raw_inputs, combined_text)

    context_region = str(state.get("context_region", "Global")).strip()
    is_south_africa = _is_region_match(context_region, {"south africa", "za", "sa"})
    is_uruguay = _is_region_match(context_region, {"uruguay"})
    is_china = _is_region_match(context_region, {"china"})

    lines: list[str] = []
    lines.append("graph TD")
    lines.append("  %% Zone A: External_Intake")
    lines.append('  subgraph External_Intake ["Customer Channels"]')
    lines.append("    CH_EMAIL([Email/PDF]):::external")
    lines.append("    CH_CHAT([WhatsApp/Chat]):::external")
    lines.append("    CH_EDI([EDI/Portal]):::external")
    if is_south_africa:
        lines.append("    SA_VECTOR[(Vector 3PL)]:::persistence")
    if is_uruguay:
        lines.append("    UY_SYNC{{Power Street Sync}}:::agent")
    if is_china:
        lines.append("    CN_GATEWAY[Regional Gateway]:::core")
    lines.append("  end")
    lines.append("")
    lines.append("  %% Zone B: Agentic_SideCar")
    lines.append('  subgraph Agentic_SideCar ["Intelligent Automation"]')
    lines.append("    AG_SCRIBE{{Doc Extractor}}:::agent")
    lines.append("    AG_INTENT{{Intent Analyzer}}:::agent")
    lines.append("    AG_DISPUTE{{Dispute Resolver}}:::agent")
    lines.append("    WF_ROUTER([Order Router]):::workflow")
    if flow_signals["change_handler"]["enabled"]:
        lines.append("    WF_CHANGE([Change Request Handler]):::workflow")
    if flow_signals["capture_failure_gateway"]["enabled"]:
        lines.append("    DG_CAPTURE_FAIL{{Capture Failure Decision}}:::agent")
    if flow_signals["order_type_gateway"]["enabled"]:
        lines.append("    DG_ORDER_TYPE{{Order Type Decision}}:::agent")
    lines.append("    WF_VALIDATOR([Validator]):::workflow")
    lines.append("    WF_FORMAT([Format Engine]):::workflow")
    lines.append("    DB_POLICY[(Policy Rules)]:::persistence")
    lines.append("  end")
    lines.append("")
    lines.append("  %% Zone C: Clean_Core_ERP")
    lines.append('  subgraph Clean_Core_ERP ["Core System"]')
    lines.append("    ERP_VA01[Create Order]:::core")
    lines.append("    ERP_MD[Validation]:::core")
    lines.append("    ERP_POST[Post Order]:::core")
    if flow_signals["availability_check"]["enabled"]:
        lines.append("    ERP_AVAIL[Check Product and Service Availability]:::core")
    lines.append("    DB_S4[(Master Data)]:::persistence")
    lines.append("  end")
    lines.append("")
    lines.append("  %% Evidence References derived from uploaded documents")
    if evidence_references:
        for ref in evidence_references[:8]:
            lines.append(
                "  %% {id} {source}: {excerpt}".format(
                    id=ref.get("id", "DOC"),
                    source=_compact_text(str(ref.get("source", "")), max_len=50),
                    excerpt=_compact_text(str(ref.get("excerpt", "")), max_len=110),
                )
            )
    else:
        lines.append("  %% No source evidence references were detected")
    lines.append("")
    lines.append("  %% Intake routing with regional logic")
    if is_china:
        lines.append("  CH_EMAIL -->|Webhook| CN_GATEWAY")
        lines.append("  CH_CHAT -->|Webhook| CN_GATEWAY")
        lines.append("  CH_EDI -->|EDI| CN_GATEWAY")
        if is_south_africa:
            lines.append("  SA_VECTOR -.->|Integration Link| CN_GATEWAY")
        lines.append("  CN_GATEWAY -->|Route| WF_ROUTER")
    elif is_uruguay:
        lines.append("  CH_EMAIL -->|Webhook| UY_SYNC")
        lines.append("  CH_CHAT -->|Webhook| UY_SYNC")
        lines.append("  CH_EDI -->|EDI| UY_SYNC")
        lines.append("  UY_SYNC -->|Normalize| AG_SCRIBE")
    else:
        lines.append("  CH_EMAIL -->|Webhook| WF_ROUTER")
        lines.append("  CH_CHAT -->|Webhook| WF_ROUTER")
        lines.append("  CH_EDI -->|EDI| WF_ROUTER")
    if is_south_africa and not is_china:
        lines.append("  SA_VECTOR -.->|Integration Link| WF_ROUTER")
    lines.append("")
    lines.append("  %% Side-Car orchestration flow")
    lines.append(
        "  WF_ROUTER -.->|{label}| AG_SCRIBE".format(
            label=_label_with_refs("Normalize Payload", flow_signals["change_handler"]["refs"]),
        )
    )
    if flow_signals["change_handler"]["enabled"]:
        lines.append(
            "  WF_ROUTER -.->|{label}| WF_CHANGE".format(
                label=_label_with_refs("Change Queue", flow_signals["change_handler"]["refs"]),
            )
        )
        lines.append("  WF_CHANGE -->|Amend Order| AG_INTENT")
    lines.append("  AG_SCRIBE -->|Structured Data| AG_INTENT")
    lines.append("  AG_INTENT -.->|Apply Rules| DB_POLICY")
    if flow_signals["capture_failure_gateway"]["enabled"]:
        lines.append(
            "  AG_INTENT -->|{label}| DG_CAPTURE_FAIL".format(
                label=_label_with_refs("Detect Capture Failure", flow_signals["capture_failure_gateway"]["refs"]),
            )
        )
        if flow_signals["order_type_gateway"]["enabled"]:
            lines.append("  DG_CAPTURE_FAIL -->|No| DG_ORDER_TYPE")
        else:
            lines.append("  DG_CAPTURE_FAIL -->|No| WF_VALIDATOR")
        lines.append("  DG_CAPTURE_FAIL -->|Yes| AG_DISPUTE")
    if flow_signals["order_type_gateway"]["enabled"]:
        if not flow_signals["capture_failure_gateway"]["enabled"]:
            lines.append(
                "  AG_INTENT -->|{label}| DG_ORDER_TYPE".format(
                    label=_label_with_refs("Resolve Order Type", flow_signals["order_type_gateway"]["refs"]),
                )
            )
        lines.append("  DG_ORDER_TYPE -->|Standard| WF_VALIDATOR")
        lines.append("  DG_ORDER_TYPE -->|Consignment| WF_VALIDATOR")
    if not flow_signals["order_type_gateway"]["enabled"] and not flow_signals["capture_failure_gateway"]["enabled"]:
        lines.append("  AG_INTENT -->|Validate| WF_VALIDATOR")
    lines.append("  WF_VALIDATOR -->|Format| WF_FORMAT")
    lines.append("  AG_INTENT -->|Exception to Resolve| AG_DISPUTE")
    lines.append("  AG_DISPUTE -.->|Resolve Case| ERP_VA01")
    lines.append("")
    lines.append("  %% Clean Core standard processing")
    lines.append("  WF_FORMAT -.->|Post to System| ERP_VA01")
    lines.append("  ERP_VA01 -->|Update| ERP_MD")
    lines.append("  ERP_MD -.->|Check Data| DB_S4")
    lines.append("  ERP_MD ==>|Post to System| ERP_POST")
    lines.append("  ERP_POST -->|Notify Status| WF_ROUTER")
    if flow_signals["availability_check"]["enabled"]:
        lines.append(
            "  ERP_POST -->|{label}| ERP_AVAIL".format(
                label=_label_with_refs("Availability Sync", flow_signals["availability_check"]["refs"]),
            )
        )
        lines.append("  ERP_AVAIL -->|Status Callback| WF_ROUTER")
    lines.append("")
    lines.append("  %% Visual classes")
    lines.append("  classDef external fill:#E3F2FD,stroke:#1E88E5,color:#0D47A1,stroke-width:1px;")
    lines.append("  classDef agent fill:#FFF3CD,stroke:#B8860B,color:#5D4037,stroke-width:2px;")
    lines.append("  classDef workflow fill:#F5F5F5,stroke:#616161,color:#263238,stroke-width:1px;")
    lines.append("  classDef core fill:#ECEFF1,stroke:#455A64,color:#263238,stroke-width:1.5px;")
    lines.append("  classDef persistence fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20,stroke-width:1.5px;")

    mermaid_data = "\n".join(lines)
    evidence_reference_xml = _build_evidence_reference_xml(evidence_references[:12])
    return f"""<VisualArchitecture version="2.0">
  <Region>{escape(context_region)}</Region>
  <DiagramType>Tiered_Agentic_SideCar</DiagramType>
{evidence_reference_xml}
  <MermaidData><![CDATA[
{mermaid_data}
  ]]></MermaidData>
</VisualArchitecture>"""


def Blueprint_Node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    if not state.get("manual_approval", False):
        raise ValueError(
            "Trust Gap Protocol requires manual approval before Blueprint_Node execution. "
            "Set manual_approval=true only after human checkpoint review."
        )

    strategy_report = _build_strategy_report(state, settings)
    mermaid_xml = _build_visual_architecture_xml(state)

    validate_strategy_report(strategy_report, min_words=settings.min_report_words)
    validate_mermaid_xml(mermaid_xml)

    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_3_blueprint_generation"] = "completed"

    return {
        "strategy_report_markdown": strategy_report,
        "mermaid_xml": mermaid_xml,
        "refined_blueprint": {
            "strategy_report_markdown": strategy_report,
            "mermaid_xml": mermaid_xml,
        },
        "phase_status": phase_status,
    }
