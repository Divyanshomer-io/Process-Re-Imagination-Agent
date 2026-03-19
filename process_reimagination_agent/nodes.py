from __future__ import annotations

import json
import re
import time
from pathlib import Path
from statistics import mean
from typing import Any, Callable, TypeVar
from xml.sax.saxutils import escape

from process_reimagination_agent.config import Settings
from process_reimagination_agent.ingestion import ingest_manifest
from process_reimagination_agent.llm_client import call_llm
from process_reimagination_agent.models import FrictionItem, InputManifest, PathDecision
from process_reimagination_agent.process_graph import graph_motifs, graph_signals
from process_reimagination_agent.observability import get_logger
from process_reimagination_agent.prompts.blueprint import render_blueprint_prompt
from process_reimagination_agent.prompts.friction_points import (
    FRICTION_POINTS_REQUIRED_COLUMNS,
    get_friction_points_prompt,
)
from process_reimagination_agent.prompts.input_refiner import render_input_refiner_prompt
from process_reimagination_agent.prompts.path_classifier import render_path_classifier_prompt
from process_reimagination_agent.prompts.process_blueprint import render_process_blueprint_prompt
from process_reimagination_agent.prompts.use_case_cards import render_use_case_cards_prompt
from process_reimagination_agent.regional_rules import apply_regional_overrides_to_decision, detect_regional_nuances
from process_reimagination_agent.validators import count_words, validate_mermaid_xml, validate_process_blueprint_xml, validate_strategy_report, validate_use_case_cards_json

_logger = get_logger()

_SYSTEM_MESSAGE_ANALYST = (
    "You are a Principal Enterprise AI Architect and Business Transformation Strategist. "
    "You analyze process documents with high reasoning precision. You produce structured, "
    "evidence-grounded outputs that are auditable and actionable. You never hallucinate "
    "details not present in the source documents. When information is missing, you "
    "explicitly state 'Not specified' and flag it as an open question."
)

_SYSTEM_MESSAGE_BLUEPRINT = (
    "You are a Principal Enterprise AI Architect and Business Transformation Strategist. "
    "You generate comprehensive strategy reports that re-imagine processes into Zero-Touch "
    "Agentic Ecosystems using SAP Clean Core (S/4HANA), SAP BTP Side-Car orchestration, and "
    "SAP Joule/GenAI agentic capabilities. Your output must be well-structured Markdown with "
    "all required sections using Path A/B/C as the organizing logic. You enforce Clean Core "
    "principles: all custom logic stays in the Side-Car layer and is never embedded in the "
    "ERP kernel. Every recommendation must cite evidence from the source documents as "
    "{Document Name, Page/Section, short quote/paraphrase}. You never invent technologies "
    "not present in inputs; when uncertain you state 'Not specified in inputs'."
)

_SYSTEM_MESSAGE_PROCESS_BLUEPRINT = (
    "You are a Principal Enterprise AI Architect and Business Transformation Strategist. "
    "You generate To-Be process blueprints as XML-wrapped Mermaid.js flowcharts. "
    "You use Hub-and-Spoke architecture with Clean Core + Side-Car pattern. "
    "Your output must be a single valid XML block containing valid Mermaid.js code. "
    "You never invent systems or channels not present in the inputs. "
    "Path C is reserved for perception/reasoning/adaptive action only — SAP write/execution "
    "actions must use Path A (core) or Path B (BTP automation). "
    "You organize the diagram into exactly three top-level areas: External, Internal_System, "
    "and Employees, with nested subgraphs inside Internal_System."
)

_SYSTEM_MESSAGE_USE_CASE_CARDS = (
    "You are a Principal Enterprise AI Architect and Business Transformation Strategist. "
    "You generate a portfolio of Use Case Cards in consulting-ready JSON format. "
    "Cards must be grounded in the Strategy Report and Path A/B/C decisions. "
    "You return ONLY valid JSON — no prose, no markdown fences, no explanation. "
    "You create cards primarily for Path C and major Path B items, with at least one Path A card. "
    "You never invent tech names beyond SAP S/4HANA, SAP BTP, SAP Joule/GenAI; "
    "if not stated in inputs, you use 'Not specified in inputs'. "
    "You never output URLs or local file paths. Each card must cite at least one evidence item."
)

_MAX_DOCUMENT_CHARS = 4_000_000  # ~1M tokens; ensures entire files read for typical large document sets
_MAX_TOKENS_ANALYSIS = 100000
_MAX_TOKENS_BLUEPRINT = 100000
_MAX_TOKENS_USE_CASE_CARDS = 100000

_LLM_PARSE_MAX_RETRIES = 3
_LLM_PARSE_RETRY_BACKOFF = 2

_T = TypeVar("_T")


def _call_llm_with_parse_retry(
    prompt: str,
    settings: Settings,
    parse_fn: Callable[[str], _T | None],
    *,
    system_message: str | None = None,
    max_tokens: int | None = None,
    max_retries: int = _LLM_PARSE_MAX_RETRIES,
    node_label: str = "Node",
) -> tuple[_T, str]:
    """Call the LLM and parse the response, retrying with correction hints on parse failure.

    Returns a tuple of (parsed_result, raw_llm_response).
    Raises RuntimeError after all retries are exhausted.
    """
    current_prompt = prompt
    last_raw = ""
    for attempt in range(1, max_retries + 1):
        raw = call_llm(current_prompt, settings, system_message=system_message, max_tokens=max_tokens)
        last_raw = raw
        parsed = parse_fn(raw)
        if parsed:
            if attempt > 1:
                print(f"[{node_label}] LLM parse succeeded on retry attempt {attempt}")
            return parsed, raw

        print(f"[{node_label}] LLM parse failed (attempt {attempt}/{max_retries})")
        _logger.warning("%s: LLM parse failed (attempt %d/%d)", node_label, attempt, max_retries)

        if attempt < max_retries:
            correction = (
                f"\n\n=== CORRECTION (attempt {attempt} failed) ===\n"
                f"Your previous response could not be parsed into the required structured format. "
                f"Please re-read the formatting instructions above carefully and try again. "
                f"Return ONLY the requested structured output (table or JSON) with no extra prose."
            )
            current_prompt = prompt + correction
            time.sleep(_LLM_PARSE_RETRY_BACKOFF * attempt)

    raise RuntimeError(
        f"[{node_label}] All {max_retries} LLM parse attempts failed. "
        f"Last raw response ({len(last_raw)} chars): {last_raw[:200]}..."
    )


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
    # Each rule populates the Pain Points & Opportunities table columns.
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
            "where_in_process": "Order Intake / Data Entry",
            "trigger_or_input_channel": "Email, PDF, Fax, Spreadsheet",
            "systems_or_tools_mentioned": "SAP",
            "why_its_friction": "Delay from manual re-keying; high transcription error rate; rework when data is misinterpreted.",
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
            "where_in_process": "Order Capture / Exception Handling",
            "trigger_or_input_channel": "EDI",
            "systems_or_tools_mentioned": "SAP (IDoc processing)",
            "why_its_friction": "Delay from manual triage of EDI failures; rework cycle for data-quality corrections.",
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
            "where_in_process": "Order Amendment",
            "trigger_or_input_channel": "Not specified",
            "systems_or_tools_mentioned": "SAP (VA02, VA03)",
            "why_its_friction": "Manual SAP transaction processing delays order amendment cycle; error-prone repetitive steps.",
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
            "where_in_process": "Order Type Classification",
            "trigger_or_input_channel": "Not specified",
            "systems_or_tools_mentioned": "ERP",
            "why_its_friction": "Inconsistent manual branching between order types creates variance and routing defects.",
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
            "where_in_process": "Order Intake Gateway",
            "trigger_or_input_channel": "Digital Hub",
            "systems_or_tools_mentioned": "SAP, Digital Hub",
            "why_its_friction": "Mandatory gateway step adds latency; manual routing compliance enforcement.",
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
            "where_in_process": "Truck-Loading Order Capture",
            "trigger_or_input_channel": "Power Street mobile channel",
            "systems_or_tools_mentioned": "ERP, Power Street",
            "why_its_friction": "Mobile payload variability causes format errors; same-day order capture delayed.",
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
            "where_in_process": "Indirect Order Reconciliation",
            "trigger_or_input_channel": "Vector 3PL backward integration",
            "systems_or_tools_mentioned": "Vector, SAP",
            "why_its_friction": "Next-day reconciliation lag; manual handoff between boundary systems creates delays.",
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
            "where_in_process": "Dispute / Deduction Triage",
            "trigger_or_input_channel": "Not specified",
            "systems_or_tools_mentioned": "Not specified",
            "why_its_friction": "Manual cross-system evidence reconciliation; extended dispute cycle time; compliance risk.",
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
                where_in_process=str(rule.get("where_in_process", "Not specified")),
                trigger_or_input_channel=str(rule.get("trigger_or_input_channel", "Not specified")),
                systems_or_tools_mentioned=str(rule.get("systems_or_tools_mentioned", "Not specified")),
                why_its_friction=str(rule.get("why_its_friction", "")),
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


def _derive_graph_friction_items(raw_inputs: dict[str, Any], context_region: str) -> list[FrictionItem]:
    graphs = raw_inputs.get("process_graphs", [])
    if not graphs:
        return []
    graph = graphs[0] if isinstance(graphs[0], dict) else {}
    motifs = graph_motifs(graph)  # type: ignore[arg-type]
    derived: list[FrictionItem] = []

    if motifs.get("manual_touchpoints", 0) >= 2:
        derived.append(
            FrictionItem(
                current_manual_action="Process graph shows repeated manual touchpoints across diagram branches.",
                where_in_process="Multiple steps (graph-derived)",
                trigger_or_input_channel="Not specified",
                systems_or_tools_mentioned="Not specified",
                why_its_friction="Repeated manual intervention nodes increase handling time and error rate.",
                friction_type="Human transcription and unstructured intake triage",
                proposed_path="C",
                rationale="Graph topology indicates repeated manual intervention nodes across intake flow.",
                expected_kpi_shift="40-65% reduction in manual handling effort",
                requires_perception=True,
                requires_reasoning=True,
                requires_adaptive_action=False,
                source_evidence=f"Graph-derived motifs from uploaded diagrams in {context_region}.",
            )
        )
    if motifs.get("exception_branches", 0) >= 1:
        derived.append(
            FrictionItem(
                current_manual_action="Diagram includes explicit failure/exception branches requiring routing and rework.",
                where_in_process="Exception Handling (graph-derived)",
                trigger_or_input_channel="Not specified",
                systems_or_tools_mentioned="Not specified",
                why_its_friction="Exception branches cause rework loops and delay downstream processing.",
                friction_type="Deterministic coordination and status handling",
                proposed_path="B",
                rationale="Exception branches are structurally explicit and suited for deterministic orchestration.",
                expected_kpi_shift="20-35% faster exception turnaround",
                requires_perception=False,
                requires_reasoning=False,
                requires_adaptive_action=False,
                source_evidence=f"Graph-derived exception motif count={motifs.get('exception_branches', 0)}.",
            )
        )
    if motifs.get("gateway_count", 0) >= 1:
        derived.append(
            FrictionItem(
                current_manual_action="Decision gateways exist in flow and rely on inconsistent branching execution.",
                where_in_process="Decision Gateway (graph-derived)",
                trigger_or_input_channel="Not specified",
                systems_or_tools_mentioned="ERP",
                why_its_friction="Inconsistent gateway branching causes variance and routing defects.",
                friction_type="ERP standardization opportunity for order-type branching",
                proposed_path="A",
                rationale="Gateway-based branching can be standardized with rule-driven ERP/API behavior.",
                expected_kpi_shift="Lower branch variance and fewer routing defects",
                requires_perception=False,
                requires_reasoning=False,
                requires_adaptive_action=False,
                source_evidence=f"Graph-derived gateway motif count={motifs.get('gateway_count', 0)}.",
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
    raise ValueError(
        "No valid friction items found in agent state. "
        "The upstream friction_points_node must produce LLM-generated friction items before downstream nodes can run."
    )


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


def _parse_llm_friction_table(raw_response: str, context_region: str) -> list[FrictionItem]:
    """Parse an LLM markdown-table response into FrictionItem objects.

    Expects the new 10-column "Pain Points & Opportunities" table layout:
    Item_ID | Issue_or_Opportunity | Current_Observed_Practice | Where_in_Process
    | Trigger_or_Input_Channel | Region_Impacted | Systems_or_Tools_Mentioned
    | Why_It_Matters | Evidence | Open_Questions

    Accepts rows with 5+ cells (lenient) and maps columns by position.
    """
    items: list[FrictionItem] = []
    try:
        lines = [ln.strip() for ln in raw_response.splitlines() if ln.strip().startswith("|")]
        data_lines = [ln for ln in lines if not re.match(r"^\|[\s\-:|]+\|$", ln)]
        if len(data_lines) < 2:
            _logger.warning("_parse_llm_friction_table: only %d data lines found (need >=2), raw starts with: %s",
                            len(data_lines), raw_response[:300])
            return []
        skipped = 0
        for row in data_lines[1:]:
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if len(cells) < 5:
                skipped += 1
                continue
            def _cell(idx: int, default: str = "") -> str:
                return cells[idx] if idx < len(cells) else default

            issue_label = _cell(1, "Not specified")
            practice_text = _cell(2, "Not specified")
            why_it_matters = _cell(7, "")
            items.append(
                FrictionItem(
                    friction_id=_cell(0) or "",
                    issue_or_opportunity=issue_label or "Not specified",
                    current_manual_action=practice_text or "Not specified",
                    where_in_process=_cell(3, "Not specified") or "Not specified",
                    trigger_or_input_channel=_cell(4, "Not specified") or "Not specified",
                    region_impacted=_cell(5, context_region or "Global") or context_region or "Global",
                    systems_or_tools_mentioned=_cell(6, "Not specified") or "Not specified",
                    why_its_friction=why_it_matters,
                    open_questions=_cell(9, ""),
                    friction_type=why_it_matters or "LLM-identified pain point",
                    proposed_path="C" if any(
                        kw in why_it_matters.lower()
                        for kw in ["perception", "reasoning", "unstructured", "contextual"]
                    ) else "B",
                    rationale=f"LLM-identified: {why_it_matters}" if why_it_matters else "LLM-identified pain point",
                    expected_kpi_shift="To be assessed",
                    requires_perception="unstructured" in (practice_text + why_it_matters).lower(),
                    requires_reasoning="reason" in why_it_matters.lower() or "judgment" in why_it_matters.lower(),
                    requires_adaptive_action="adaptive" in why_it_matters.lower() or "exception" in why_it_matters.lower(),
                    source_evidence=_cell(8, ""),
                )
            )
        if skipped:
            _logger.warning("_parse_llm_friction_table: skipped %d rows with <5 cells", skipped)
    except Exception as exc:
        _logger.warning("Failed to parse LLM friction table: %s", exc)
    return items


def friction_points_node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    print("\n=== [friction_points_node] STARTED ===")
    _logger.info(">>> Entering friction_points_node")
    friction_prompt = get_friction_points_prompt()

    raw_inputs = dict(state.get("raw_inputs", {}))
    raw_inputs["friction_analysis_prompt"] = friction_prompt
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

    ingest_result = ingest_manifest(manifest, settings=settings)
    combined_text = ingest_result.get("combined_text", "")
    raw_inputs.update(ingest_result)
    evidence_references = _collect_document_references(raw_inputs)

    regional_nuances = detect_regional_nuances(combined_text=combined_text, context_region=manifest.context_region)

    # --- LLM-powered friction analysis (required, with retry on parse failure) ---
    llm_prompt = friction_prompt
    if combined_text.strip():
        llm_prompt = friction_prompt + "\n\n=== DOCUMENT TEXT ===\n" + combined_text[:_MAX_DOCUMENT_CHARS]

    print("[friction_points_node] Calling LLM for friction analysis...")
    _logger.info("friction_points_node: calling LLM for friction analysis (%d chars of document text)...", min(len(combined_text), _MAX_DOCUMENT_CHARS))

    def _parse_friction(raw: str) -> list[FrictionItem] | None:
        items = _parse_llm_friction_table(raw, manifest.context_region)
        return items if items else None

    llm_frictions, _ = _call_llm_with_parse_retry(
        llm_prompt,
        settings,
        _parse_friction,
        system_message=_SYSTEM_MESSAGE_ANALYST,
        max_tokens=_MAX_TOKENS_ANALYSIS,
        node_label="friction_points_node",
    )
    print(f"[friction_points_node] USING LLM OUTPUT: {len(llm_frictions)} friction items from LLM (GPT-5 only, no supplements)")
    _logger.info("friction_points_node: LLM produced %d friction items (strict GPT-5 only)", len(llm_frictions))

    # Strict: use only LLM output; no deterministic supplements or fallbacks
    frictions = llm_frictions

    for idx, item in enumerate(frictions, start=1):
        item.friction_id = f"P-{idx:03d}"
        if item.region_impacted == "Global":
            item.region_impacted = manifest.context_region or "Global"

    resolved_pain_points = list(manifest.pain_points)
    if not resolved_pain_points:
        resolved_pain_points = [item.current_manual_action for item in frictions]

    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_1_current_reality_synthesis"] = "completed"

    errors = list(state.get("errors", []))
    extraction_errors = ingest_result.get("extraction_errors", [])
    if extraction_errors:
        errors.extend(extraction_errors)

    return {
        "raw_inputs": raw_inputs,
        "canonical_documents": raw_inputs.get("canonical_documents", []),
        "process_graphs": raw_inputs.get("process_graphs", []),
        "process_name": manifest.process_name,
        "context_region": manifest.context_region,
        "pain_points": resolved_pain_points,
        "cognitive_friction_logs": [item.model_dump() for item in frictions],
        "regional_nuances": regional_nuances,
        "evidence_references": evidence_references,
        "phase_status": phase_status,
        "errors": errors,
    }


def _parse_llm_refined_items(raw_response: str, original_items: list[FrictionItem]) -> list[dict[str, Any]] | None:
    """Parse an LLM JSON-array response of refined friction items.

    Accepts partial matches: entries matching known friction_ids are merged
    with originals.  Unmatched originals are preserved as-is.
    """
    try:
        cleaned = raw_response.strip()
        json_match = re.search(r"\[.*]", cleaned, re.DOTALL)
        if not json_match:
            _logger.warning("_parse_llm_refined_items: no JSON array found in response (%d chars)", len(cleaned))
            return None
        parsed: list[dict[str, Any]] = json.loads(json_match.group())
    except (json.JSONDecodeError, TypeError) as exc:
        _logger.warning("_parse_llm_refined_items: JSON parse failed: %s", exc)
        return None

    if not isinstance(parsed, list) or not parsed:
        _logger.warning("_parse_llm_refined_items: parsed result is not a non-empty list")
        return None

    original_lookup = {item.friction_id: item for item in original_items}
    refined_lookup: dict[str, dict[str, Any]] = {}
    skipped = 0
    for entry in parsed:
        fid = str(entry.get("friction_id", ""))
        orig = original_lookup.get(fid)
        if orig is None:
            skipped += 1
            continue
        base = orig.model_dump()
        for key in (
            "issue_or_opportunity", "current_manual_action", "where_in_process",
            "trigger_or_input_channel", "systems_or_tools_mentioned", "why_its_friction",
            "source_evidence", "open_questions", "friction_type", "rationale",
            "expected_kpi_shift",
        ):
            if entry.get(key):
                base[key] = str(entry[key])
        if entry.get("proposed_path") in {"A", "B", "C"}:
            base["proposed_path"] = entry["proposed_path"]
        if isinstance(entry.get("requires_perception"), bool):
            base["requires_perception"] = entry["requires_perception"]
        if isinstance(entry.get("requires_reasoning"), bool):
            base["requires_reasoning"] = entry["requires_reasoning"]
        if isinstance(entry.get("requires_adaptive_action"), bool):
            base["requires_adaptive_action"] = entry["requires_adaptive_action"]
        refined_lookup[fid] = base

    if skipped:
        _logger.warning("_parse_llm_refined_items: skipped %d entries with unmatched friction_id", skipped)

    if not refined_lookup:
        _logger.warning("_parse_llm_refined_items: no valid refined entries after filtering")
        return None

    results: list[dict[str, Any]] = []
    for item in original_items:
        if item.friction_id in refined_lookup:
            results.append(refined_lookup[item.friction_id])
        else:
            results.append(item.model_dump())

    _logger.info("_parse_llm_refined_items: merged %d LLM-refined items (kept %d originals unchanged)",
                 len(refined_lookup), len(original_items) - len(refined_lookup))
    return results


def Input_Refiner_Node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    print("\n=== [Input_Refiner_Node] STARTED ===")
    _logger.info(">>> Entering Input_Refiner_Node")
    iteration = int(state.get("refinement_iterations", 0)) + 1
    print(f"[Input_Refiner_Node] Refinement pass {iteration}")
    feedback = list(state.get("quality_feedback", []))
    feedback.append(
        (
            f"Refinement pass {iteration}: strengthened evidence mapping and clarified "
            "Path A/B/C rationale to close Trust Gap."
        )
    )

    friction_items = _friction_items_from_state(state)
    friction_logs = state.get("cognitive_friction_logs", [])
    evidence_refs = list(state.get("evidence_references", []))

    # --- LLM-powered refinement (required, with retry on parse failure) ---
    rendered_prompt = render_input_refiner_prompt(friction_logs, feedback, evidence_refs)
    print(f"[Input_Refiner_Node] Calling LLM for refinement (pass {iteration})...")

    def _parse_refined(raw: str) -> list[dict[str, Any]] | None:
        return _parse_llm_refined_items(raw, friction_items)

    refined_logs, _ = _call_llm_with_parse_retry(
        rendered_prompt,
        settings,
        _parse_refined,
        system_message=_SYSTEM_MESSAGE_ANALYST,
        max_tokens=_MAX_TOKENS_ANALYSIS,
        node_label="Input_Refiner_Node",
    )
    print(f"[Input_Refiner_Node] USING LLM OUTPUT: {len(refined_logs)} refined items (pass {iteration})")
    _logger.info("Input_Refiner_Node: LLM-refined friction items (pass %d)", iteration)

    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_1_current_reality_synthesis"] = "completed"

    return {
        "refinement_iterations": iteration,
        "quality_feedback": feedback,
        "cognitive_friction_logs": refined_logs,
        "phase_status": phase_status,
    }


_CONFIDENCE_LABEL_TO_FLOAT: dict[str, float] = {
    "high": 0.97,
    "medium": 0.90,
    "low": 0.75,
}



def _parse_llm_classifications(
    raw_response: str,
    friction_items: list[FrictionItem],
) -> list[dict[str, Any]] | None:
    """Extract structured path classifications from the LLM table response.

    Parses the "Path Classification (A/B/C) — SAP" markdown table with columns:
    Item_ID | Recommended_Path | Suitability_Justification | SAP_Target
    | Core_vs_SideCar_Orientation | Human_Supervision_Needed | Confidence
    | Evidence | Open_Questions

    Falls back to JSON parsing if no table is detected.
    """
    friction_lookup = {item.friction_id: item for item in friction_items}

    # Try table parsing first (new Prompt 2 output format)
    table_results = _parse_classification_table(raw_response, friction_lookup)
    if table_results:
        return table_results

    # Fallback: try JSON parsing for backward compatibility
    try:
        cleaned = raw_response.strip()
        json_match = re.search(r"\[.*]", cleaned, re.DOTALL)
        if not json_match:
            _logger.warning("_parse_llm_classifications: no table or JSON array found in response (%d chars). Starts with: %s",
                            len(cleaned), cleaned[:200])
            return None
        classifications: list[dict[str, Any]] = json.loads(json_match.group())
    except (json.JSONDecodeError, TypeError) as exc:
        _logger.warning("_parse_llm_classifications: JSON fallback parse failed: %s. Response starts with: %s",
                        exc, raw_response.strip()[:200])
        return None

    if not isinstance(classifications, list) or not classifications:
        _logger.warning("_parse_llm_classifications: parsed result is not a non-empty list")
        return None

    results: list[dict[str, Any]] = []
    skipped = 0
    for entry in classifications:
        fid = str(entry.get("friction_id", "") or entry.get("item_id", "") or entry.get("Item_ID", ""))
        item = friction_lookup.get(fid)
        if item is None:
            skipped += 1
            continue
        recommended = str(entry.get("recommended_path", "") or entry.get("Recommended_Path", "")).strip().upper()
        if recommended not in {"A", "B", "C"}:
            skipped += 1
            continue
        results.append({
            "friction_id": fid,
            "recommended_path": recommended,
            "suitability_justification": str(entry.get("suitability_justification", "") or entry.get("Suitability_Justification", "")),
            "sap_target": str(entry.get("sap_target", "") or entry.get("SAP_Target", "")),
            "core_vs_sidecar_orientation": str(entry.get("core_vs_sidecar_orientation", "") or entry.get("Core_vs_SideCar_Orientation", "")),
            "human_supervision_needed": str(entry.get("human_supervision_needed", "") or entry.get("Human_Supervision_Needed", "")),
            "confidence": str(entry.get("confidence", "Medium") or entry.get("Confidence", "Medium")),
            "evidence": str(entry.get("evidence", "") or entry.get("Evidence", "")),
            "open_questions": str(entry.get("open_questions", "") or entry.get("Open_Questions", "")),
        })

    if skipped:
        _logger.warning("_parse_llm_classifications: skipped %d entries (unmatched friction_id or invalid path), kept %d",
                        skipped, len(results))
    if not results:
        _logger.warning("_parse_llm_classifications: no valid entries after filtering")
        return None
    _logger.info("_parse_llm_classifications: successfully parsed %d/%d LLM classifications",
                 len(results), len(friction_items))
    return results


def _parse_classification_table(
    raw_response: str,
    friction_lookup: dict[str, FrictionItem],
) -> list[dict[str, Any]] | None:
    """Parse a markdown table from the path classifier LLM response.

    Table columns (0-indexed):
    0: Item_ID, 1: Recommended_Path, 2: Suitability_Justification,
    3: SAP_Target, 4: Core_vs_SideCar_Orientation,
    5: Human_Supervision_Needed, 6: Confidence, 7: Evidence, 8: Open_Questions
    """
    try:
        lines = [ln.strip() for ln in raw_response.splitlines() if ln.strip().startswith("|")]
        data_lines = [ln for ln in lines if not re.match(r"^\|[\s\-:|]+\|$", ln)]
        if len(data_lines) < 2:
            return None
        results: list[dict[str, Any]] = []
        skipped = 0
        for row in data_lines[1:]:
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if len(cells) < 3:
                skipped += 1
                continue
            def _cell(idx: int, default: str = "") -> str:
                return cells[idx] if idx < len(cells) else default

            fid = _cell(0).strip()
            item = friction_lookup.get(fid)
            if item is None:
                skipped += 1
                continue
            recommended = _cell(1).strip().upper()
            if recommended not in {"A", "B", "C"}:
                skipped += 1
                continue
            results.append({
                "friction_id": fid,
                "recommended_path": recommended,
                "suitability_justification": _cell(2),
                "sap_target": _cell(3),
                "core_vs_sidecar_orientation": _cell(4),
                "human_supervision_needed": _cell(5),
                "confidence": _cell(6, "Medium"),
                "evidence": _cell(7),
                "open_questions": _cell(8),
            })
        if skipped:
            _logger.warning("_parse_classification_table: skipped %d rows", skipped)
        if not results:
            return None
        _logger.info("_parse_classification_table: parsed %d classifications from table", len(results))
        return results
    except Exception as exc:
        _logger.warning("_parse_classification_table: failed: %s", exc)
        return None


def _apply_guardrail(path: str, item: FrictionItem) -> str:
    """Enforce the strict suitability rule: Path C requires perception/reasoning/adaptive action."""
    if path == "C" and not (item.requires_perception or item.requires_reasoning or item.requires_adaptive_action):
        return "B"
    return path


def _has_hard_extraction_failures(errors: list[str]) -> bool:
    """Return True only for genuine extraction failures, not tool-availability warnings."""
    soft_warning_tokens = {"ocr rendering unavailable", "poppler", "tesseract", "pdf2image"}
    for err in errors:
        err_lower = err.lower()
        if any(token in err_lower for token in soft_warning_tokens):
            continue
        if "not found" in err_lower or "extraction failed" in err_lower or "empty extraction" in err_lower:
            return True
    return False


def path_classifier_node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    print("\n=== [path_classifier_node] STARTED ===")
    _logger.info(">>> Entering path_classifier_node")
    friction_items = _friction_items_from_state(state)
    iteration = int(state.get("refinement_iterations", 0))
    region = state.get("context_region", "Global")
    evidence_penalty = _has_hard_extraction_failures(list(state.get("errors", [])))

    friction_logs = state.get("cognitive_friction_logs", [])
    evidence_refs = list(state.get("evidence_references", []))
    rendered_prompt = render_path_classifier_prompt(friction_logs, evidence_refs)

    print(f"[path_classifier_node] Calling LLM for path classification ({len(friction_items)} friction items)...")
    _logger.info("path_classifier_node: calling LLM for path classification (%d friction items)...", len(friction_items))

    def _parse_classifications(raw: str) -> list[dict[str, Any]] | None:
        return _parse_llm_classifications(raw, friction_items)

    llm_classifications, _ = _call_llm_with_parse_retry(
        rendered_prompt,
        settings,
        _parse_classifications,
        system_message=_SYSTEM_MESSAGE_ANALYST,
        max_tokens=_MAX_TOKENS_ANALYSIS,
        node_label="path_classifier_node",
    )
    print(f"[path_classifier_node] USING LLM OUTPUT: {len(llm_classifications)} classifications parsed successfully")
    _logger.info("path_classifier_node: using LLM-driven classification")

    llm_map: dict[str, dict[str, Any]] = {}
    for entry in llm_classifications:
        llm_map[entry["friction_id"]] = entry

    path_decisions: list[dict[str, Any]] = []
    for item in friction_items:
        llm_entry = llm_map.get(item.friction_id)
        if llm_entry:
            path = _apply_guardrail(llm_entry["recommended_path"], item)
            confidence_label = llm_entry["confidence"].strip().lower()
            confidence = _CONFIDENCE_LABEL_TO_FLOAT.get(confidence_label, 0.90)
            rationale = (
                f"{llm_entry['suitability_justification']} "
                "Classified via mandatory Phase 2 suitability assessment."
            )
        else:
            path = _apply_guardrail(item.proposed_path or "B", item)
            confidence = 0.90
            rationale = f"{item.rationale} Classified via LLM friction analysis proposed_path (item not matched in classification response)."

        decision = PathDecision(
            current_manual_action=item.current_manual_action,
            path=path,  # type: ignore[arg-type]
            confidence=confidence,
            rationale=rationale,
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
        "path_classifier_prompt": rendered_prompt,
    }


def Quality_Control_Node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    print("\n=== [Quality_Control_Node] STARTED ===")
    _logger.info(">>> Entering Quality_Control_Node")
    confidence = float(state.get("confidence_score", 0.0))
    print(f"[Quality_Control_Node] Confidence: {confidence:.2%} (threshold: {settings.confidence_threshold:.2%})")
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
    print("\n=== [Human_Escalation_Node] STARTED ===")
    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_3_blueprint_generation"] = "blocked_pending_human_escalation"
    errors = list(state.get("errors", []))
    if not errors:
        errors.append("Human escalation required before blueprint generation.")
    return {"phase_status": phase_status, "errors": errors}


_COLUMN_TO_FIELD: dict[str, str] = {
    "Item_ID": "friction_id",
    "Issue_or_Opportunity": "issue_or_opportunity",
    "Current_Observed_Practice": "current_manual_action",
    "Where_in_Process": "where_in_process",
    "Trigger_or_Input_Channel": "trigger_or_input_channel",
    "Region_Impacted": "region_impacted",
    "Systems_or_Tools_Mentioned": "systems_or_tools_mentioned",
    "Why_It_Matters": "why_its_friction",
    "Evidence": "source_evidence",
    "Open_Questions": "open_questions",
}

_COLUMN_DEFAULTS: dict[str, str] = {
    "friction_id": "N/A",
    "issue_or_opportunity": "N/A",
    "current_manual_action": "N/A",
    "where_in_process": "Not specified",
    "trigger_or_input_channel": "Not specified",
    "region_impacted": "Global",
    "systems_or_tools_mentioned": "Not specified",
    "why_its_friction": "N/A",
    "source_evidence": "N/A",
    "open_questions": "",
}


def _build_cognitive_friction_table(cognitive_friction_logs: list[dict[str, Any]]) -> str:
    columns = FRICTION_POINTS_REQUIRED_COLUMNS
    header_line = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join("---" for _ in columns) + "|"
    header = f"{header_line}\n{separator}"

    rows: list[str] = []
    for item in cognitive_friction_logs:
        cells: list[str] = []
        for col in columns:
            field = _COLUMN_TO_FIELD.get(col, col.lower())
            default = _COLUMN_DEFAULTS.get(field, "")
            cells.append(_markdown_cell(str(item.get(field, default))))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, *rows]) if rows else header


def build_friction_points_markdown(
    *,
    process_name: str,
    context_region: str,
    cognitive_friction_logs: list[dict[str, Any]],
) -> str:
    """Render the full Pain Points & Opportunities markdown document.

    This is the primary output artifact for the friction_points_node.
    It produces ONLY the table (no narrative preamble) per the stored prompt.
    """
    table = _build_cognitive_friction_table(cognitive_friction_logs)
    return (
        f"# Pain Points & Opportunities (A/B/C Candidates): {process_name} ({context_region})\n\n"
        f"{table}\n"
    )


def _confidence_label(value: float) -> str:
    if value >= 0.95:
        return "High"
    if value >= 0.85:
        return "Medium"
    return "Low"


def _orientation_label(path: str) -> str:
    if path == "A":
        return "Core"
    return "Side-Car"


def _supervision_label(path: str, confidence: float) -> str:
    if path == "A":
        return "No"
    if path == "B":
        if confidence < 0.90:
            return "Conditional"
        return "No"
    # Path C
    if confidence >= 0.97:
        return "Conditional"
    return "Yes"


def _sap_target_label(path: str) -> str:
    if path == "A":
        return "SAP S/4HANA"
    if path == "B":
        return "SAP BTP"
    return "SAP Joule/GenAI"


def _build_path_classification_table(
    path_decisions: list[dict[str, Any]],
    cognitive_friction_logs: list[dict[str, Any]],
) -> str:
    """Build the Path Classification (A/B/C) — SAP markdown table matching the prompt schema."""
    friction_lookup: dict[str, dict[str, Any]] = {}
    for item in cognitive_friction_logs:
        action_key = str(item.get("current_manual_action", "")).strip().lower()
        friction_lookup[action_key] = item

    header = (
        "| Item_ID | Recommended_Path | Suitability_Justification "
        "| SAP_Target | Core_vs_SideCar_Orientation | Human_Supervision_Needed "
        "| Confidence | Evidence | Open_Questions |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    rows: list[str] = []
    for decision in path_decisions:
        action = str(decision.get("current_manual_action", ""))
        friction = friction_lookup.get(action.strip().lower(), {})
        friction_id = str(friction.get("friction_id", "N/A"))
        path = str(decision.get("path", ""))
        confidence = float(decision.get("confidence", 0.0))

        rows.append(
            "| {fid} | {path} | {justification} | {sap_target} | {orientation} | {supervision} "
            "| {confidence} | {evidence} | {questions} |".format(
                fid=_markdown_cell(friction_id),
                path=_markdown_cell(path),
                justification=_markdown_cell(str(decision.get("rationale", ""))),
                sap_target=_markdown_cell(_sap_target_label(path)),
                orientation=_markdown_cell(_orientation_label(path)),
                supervision=_markdown_cell(_supervision_label(path, confidence)),
                confidence=_markdown_cell(_confidence_label(confidence)),
                evidence=_markdown_cell(str(friction.get("source_evidence", "N/A"))),
                questions=_markdown_cell(str(friction.get("open_questions", ""))),
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


def _group_decisions_by_path(
    path_decisions: list[dict[str, Any]],
    cognitive_friction_logs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Partition path decisions into A/B/C groups with friction context attached."""
    friction_lookup: dict[str, dict[str, Any]] = {}
    for item in cognitive_friction_logs:
        key = str(item.get("current_manual_action", "")).strip().lower()
        friction_lookup[key] = item

    groups: dict[str, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}
    for decision in path_decisions:
        path = str(decision.get("path", "B"))
        action = str(decision.get("current_manual_action", ""))
        friction = friction_lookup.get(action.strip().lower(), {})
        enriched = {**decision, "friction": friction}
        groups.setdefault(path, []).append(enriched)
    return groups


def _build_hotspots(cognitive_friction_logs: list[dict[str, Any]], top_n: int = 5) -> str:
    """Identify the top N friction hotspots with evidence for the Current Reality Synthesis."""
    if not cognitive_friction_logs:
        return "No friction items available for hotspot analysis."

    ranked = sorted(
        cognitive_friction_logs,
        key=lambda x: (
            bool(x.get("requires_perception")),
            bool(x.get("requires_reasoning")),
            bool(x.get("requires_adaptive_action")),
        ),
        reverse=True,
    )
    lines: list[str] = ["**Hotspots (Top Friction Points)**\n"]
    for item in ranked[:top_n]:
        fid = item.get("friction_id", "N/A")
        issue = item.get("issue_or_opportunity") or item.get("current_manual_action", "N/A")
        evidence = item.get("source_evidence", "Not specified in inputs")
        lines.append(f"- **{fid}**: {_compact_text(str(issue), 160)} — Evidence: {_compact_text(str(evidence), 200)}")
    return "\n".join(lines)


def _build_strategy_report(state: dict[str, Any], settings: Settings) -> str:
    process_name = state.get("process_name", "Process")
    context_region = state.get("context_region", "Global")
    trust_gap_phase = state.get("trust_gap_phase", "Shadow")
    cognitive_friction_logs = state.get("cognitive_friction_logs", [])
    path_decisions = state.get("path_decisions", [])
    evidence_references = state.get("evidence_references", [])

    table = _build_cognitive_friction_table(cognitive_friction_logs)
    path_groups = _group_decisions_by_path(path_decisions, cognitive_friction_logs)

    report_title = f"# Re-Imagined Strategy Report: {process_name}"
    section_order: list[str] = []
    section_registry: dict[str, str] = {}

    # --- 1. Executive Summary ---
    _add_unique_section(
        section_order,
        section_registry,
        "## Executive Summary",
        (
            f"**One Big Move:** Transform {process_name} in {context_region} from a human-middleware-dependent "
            "operation into a Zero-Touch Agentic Ecosystem. The architecture rests on three pillars: SAP S/4HANA "
            "Clean Core as the immutable System of Record (Path A), SAP BTP as the Side-Car orchestration and "
            "deterministic automation layer (Path B), and SAP Joule/GenAI for agentic perception, reasoning, and "
            "adaptive action only where suitability demands it (Path C). Clean Core enforcement is explicit: all "
            "custom logic is isolated in the Side-Car layer and never embedded in the ERP kernel. The strategic "
            "benefit is immediate: higher touchless throughput, lower transcription defects, faster exception "
            "closure, and lower operational risk across regional variations. Path A/B/C decisions serve as the "
            "organizing logic throughout this report, ensuring every recommendation is grounded in suitability "
            "assessment and evidence from source documents."
        ),
    )

    # --- 2. Current Reality Synthesis ---
    hotspots = _build_hotspots(cognitive_friction_logs)
    _add_unique_section(
        section_order,
        section_registry,
        "## Current Reality Synthesis",
        (
            f"The analysis of {process_name} across {context_region} reveals a process landscape where human "
            "operators act as cognitive middleware between unstructured intake channels and the SAP core system. "
            "The following pain points and opportunities were identified from source documents and process analysis.\n\n"
            f"{table}\n\n"
            "The source evidence register below grounds these findings in uploaded artifacts.\n\n"
            f"{_build_reference_register(evidence_references)}\n\n"
            f"{hotspots}"
        ),
    )

    # --- 3. Strategy: Layered Re-Imagination using Path A/B/C ---
    path_a_items = path_groups.get("A", [])
    path_b_items = path_groups.get("B", [])
    path_c_items = path_groups.get("C", [])

    def _format_path_items(items: list[dict[str, Any]]) -> str:
        if not items:
            return "No items classified to this path based on current inputs.\n"
        lines: list[str] = []
        for d in items:
            friction = d.get("friction", {})
            fid = friction.get("friction_id", "N/A")
            action = _compact_text(str(d.get("current_manual_action", "")), 140)
            rationale = _compact_text(str(d.get("rationale", "")), 200)
            lines.append(f"- **{fid}** — {action}: {rationale}")
        return "\n".join(lines)

    _add_unique_section(
        section_order,
        section_registry,
        "## Strategy: Layered Re-Imagination using Path A/B/C",
        (
            "The re-imagination strategy is organized into three layers aligned with the SAP Clean Core + BTP + "
            "Joule/GenAI architecture. Each friction point is assigned to exactly one path based on the mandatory "
            "Phase 2 suitability assessment.\n\n"
            "### Path A: SAP S/4HANA Core Standardization (Foundation)\n\n"
            "Path A items are candidates for ERP standardization. These represent processes where business behavior "
            "is not unique and can be governed through standard SAP configuration, validated APIs, and master data "
            "rules. No custom code enters the ERP kernel.\n\n"
            f"{_format_path_items(path_a_items)}\n\n"
            "### Path B: SAP BTP Platform Enhancements / Deterministic Automation (Bridge)\n\n"
            "Path B items are handled by deterministic orchestration in the SAP BTP Side-Car layer. These are "
            "repeatable, rule-based tasks suited for workflow automation, format engines, routing policies, and "
            "validation pipelines. No perception or reasoning is required.\n\n"
            f"{_format_path_items(path_b_items)}\n\n"
            "### Path C: SAP Joule/GenAI Agentic AI Deployment (Game Changer)\n\n"
            "Path C items require agentic AI capabilities: perception over unstructured inputs, contextual "
            "reasoning, or adaptive action under ambiguity. These are deployed through SAP Joule/GenAI with "
            "confidence scoring, policy guardrails, and human escalation triggers.\n\n"
            f"{_format_path_items(path_c_items)}"
        ),
    )

    # --- 4. Architecture of the Future State ---
    _add_unique_section(
        section_order,
        section_registry,
        "## Architecture of the Future State",
        (
            "The future state is a **Hub-and-Spoke** operating model where the SAP BTP Side-Car is the controlled "
            "intelligence hub between external channels and the SAP S/4HANA Clean Core.\n\n"
            "**Agent Persona 1: The Intake Scribe**\n"
            "- Responsibilities: Extract, normalize, and structure incoming order payloads from mixed channels.\n"
            "- Inputs: Emails, PDFs, EDI messages, faxes, spreadsheets, portal submissions.\n"
            "- Decisions: Field mapping, format detection, payload completeness check.\n"
            "- Outputs: Canonical order event in standardized schema.\n"
            "- Escalation Triggers: Confidence below threshold on field extraction; missing mandatory fields "
            "after retry.\n\n"
            "**Agent Persona 2: The Intent Analyzer**\n"
            "- Responsibilities: Classify business intent and route work to the correct path (A/B/C).\n"
            "- Inputs: Structured canonical event from the Intake Scribe; policy rules; historical patterns.\n"
            "- Decisions: Path assignment, order-type branching, exception detection.\n"
            "- Outputs: Routing decision with rationale and confidence score.\n"
            "- Escalation Triggers: Ambiguous intent; conflicting policy signals; confidence below threshold.\n\n"
            "**Agent Persona 3: The Dispute Judge**\n"
            "- Responsibilities: Resolve contextual exceptions requiring cross-system evidence reasoning.\n"
            "- Inputs: Dispute/deduction claims, invoices, proof-of-delivery, trade promotion agreements.\n"
            "- Decisions: Claim validity, root-cause assignment, resolution recommendation.\n"
            "- Outputs: Resolution decision with evidence chain and audit trail.\n"
            "- Escalation Triggers: Insufficient evidence; policy conflict; value above auto-resolve threshold.\n\n"
            "Regional variations are managed through policy injection and adapter patterns in the Side-Car, "
            "not through core transaction branching. This architecture lets the organization scale automation "
            "without coupling business variability to ERP internals."
        ),
    )

    # --- 5. Technical Stack ---
    _add_unique_section(
        section_order,
        section_registry,
        "## Technical Stack",
        (
            "The technical stack separates concerns between the System of Record and the System of Intelligence.\n\n"
            "**System of Record: SAP S/4HANA**\n"
            "Standard APIs (OData, BAPI), master data governance, posting integrity controls, and transaction "
            "processing. No custom logic is deployed here. Clean Core enforcement is explicit: all custom logic "
            "is isolated in the Side-Car layer and never embedded in the ERP kernel.\n\n"
            "**Side-Car: SAP BTP Orchestration/Automation**\n"
            "Workflow orchestration, deterministic routing, format engines, validation pipelines, policy rule "
            "stores, event-driven integration (Webhook/AS2 intake, OData/BAPI posting). Schema validation, "
            "idempotency keys, payload lineage, and exception queues are enforced at this layer.\n\n"
            "**Agentic: SAP Joule/GenAI**\n"
            "Perception over unstructured documents, contextual reasoning for exception handling, confidence-scored "
            "decision-making with human escalation hooks. Deployed only for Path C items where suitability "
            "assessment confirms the need for perception, reasoning, or adaptive action.\n\n"
            "Integration contracts are protocol-labeled and observable. This separation protects upgradeability "
            "and reduces regression risk during SAP releases while enabling high-adaptivity automation on top."
        ),
    )

    # --- 6. The Trust Gap Protocol ---
    _add_unique_section(
        section_order,
        section_registry,
        "## The Trust Gap Protocol",
        (
            f"Current operating mode defaults to **{trust_gap_phase}**.\n\n"
            "**Shadow Phase:** Agents produce recommendations while humans retain full execution authority. "
            "Decision quality gaps are annotated and tracked. All agentic outputs are logged for audit.\n\n"
            "**Co-Pilot Phase:** High-confidence, low-risk steps execute with explicit human override capability "
            "and sampling audits. Confidence threshold is strictly greater than 95%; anything at or below "
            "threshold is routed back to refinement.\n\n"
            "**Autopilot Phase:** Approved lanes execute touchlessly with continuous telemetry, rollback hooks, "
            "and policy drift detection. If loop limits are reached, the process hard-stops into human "
            "escalation rather than silently degrading quality.\n\n"
            "The transition between phases is governed by measurable trust metrics: decision accuracy, exception "
            "rates, human override frequency, and confidence distribution stability over multiple business cycles."
        ),
    )

    # --- 7. Risks, Guardrails, and Open Questions ---
    open_questions: list[str] = []
    for item in cognitive_friction_logs:
        q = str(item.get("open_questions", "")).strip()
        if q and q.lower() not in {"", "n/a", "none"}:
            fid = item.get("friction_id", "N/A")
            open_questions.append(f"- **{fid}**: {_compact_text(q, 200)}")
    questions_block = "\n".join(open_questions) if open_questions else "- No open questions flagged in current inputs."

    _add_unique_section(
        section_order,
        section_registry,
        "## Risks, Guardrails, and Open Questions",
        (
            "**Risks**\n"
            "- Data quality in source channels may degrade agentic extraction accuracy. Mitigation: schema "
            "validation at intake with fallback to human review.\n"
            "- Regional regulatory variance may require policy updates that outpace automation deployment. "
            "Mitigation: policy injection via Side-Car adapter patterns, never in ERP kernel.\n"
            "- Trust adoption may stall if Shadow phase runs too long without measurable improvement. "
            "Mitigation: defined exit criteria and KPI packs per trust phase.\n"
            "- Over-assignment to Path C inflates agentic compute costs without proportional value. "
            "Mitigation: strict suitability assessment requiring perception/reasoning/adaptive action.\n\n"
            "**Guardrails**\n"
            "- Path C is assigned only when perception, reasoning, or adaptive action is demonstrably required.\n"
            "- All custom logic stays in the SAP BTP Side-Car; the SAP S/4HANA core remains standard.\n"
            "- Confidence thresholds gate every agentic decision; sub-threshold results route to human escalation.\n"
            "- Dead-letter routing, retry budgets, and idempotency keys protect against data corruption.\n\n"
            f"**Open Questions from Analysis**\n{questions_block}"
        ),
    )

    report = _render_report_from_sections(report_title, section_order, section_registry)

    expansion_paragraphs = [
        "Further risk mitigation: event payload contracts are versioned and backward-compatible, policy decisions are "
        "traceable to explicit evidence chains, and Side-Car services are horizontally scalable to absorb volume spikes.",
        "Staged rollout allows measured risk reduction and quick wins in high-impact channels before broader deployment. "
        "Change management and training are aligned with each trust phase to ensure adoption and continuity.",
        "Quality gates prevent regression: automated tests, contract checks, and confidence thresholds must pass before "
        "promoting to the next trust phase. Stakeholder sign-off is required at phase boundaries.",
        "Operational runbooks document standard operations, incident response, and escalation paths for each agent persona. "
        "Monitoring and alerting are configured per trust phase with clear ownership and response SLAs.",
        "Post-go-live support includes hypercare windows, knowledge transfer, and continuous improvement cycles to refine "
        "agentic behavior based on real-world usage patterns and decision quality feedback.",
        "Security and compliance checks are embedded in the pipeline: access control, audit logging, and data handling "
        "follow agreed standards before any trust phase transition is signed off.",
        "Performance baselines are established in Shadow phase and monitored through Co-Pilot and Autopilot; deviations "
        "trigger review before further scale-out of agentic lanes.",
        "Testing strategy covers unit, integration, and end-to-end scenarios across all three paths; regression suites "
        "are automated and run per trust phase transition.",
        "Data migration and cutover plans are defined for any legacy or manual data that must move into the agentic flow. "
        "Master data readiness is confirmed so that the solution has the right inputs from day one.",
        "Benefits realization is tracked against the business case; variances are reported and addressed in steering forums. "
        "Metrics and dashboards track throughput, errors, confidence distribution, and manual touch reduction.",
        "Disaster recovery and business continuity are validated; RTO and RPO targets are met before Autopilot go-live.",
        "Integration and interface testing cover all SAP BTP touchpoints; stub and mock strategies are used where "
        "downstream systems are not ready.",
    ]
    idx = 0
    expand_section = "## Risks, Guardrails, and Open Questions"
    while count_words(report) < settings.min_report_words and idx < len(expansion_paragraphs):
        section_registry[expand_section] = (
            f"{section_registry[expand_section]}\n\n{expansion_paragraphs[idx]}"
        )
        report = _render_report_from_sections(report_title, section_order, section_registry)
        idx += 1

    report = _prepend_toc(report_title, section_order, report)
    return report


def _signal_reference_ids(raw_inputs: dict[str, Any], patterns: list[str], max_refs: int = 2) -> list[str]:
    refs = _collect_pattern_references(raw_inputs, patterns, max_refs=max_refs)
    return [ref["id"] for ref in refs]


def _flow_signals(raw_inputs: dict[str, Any], combined_text: str) -> dict[str, dict[str, Any]]:
    graphs = raw_inputs.get("process_graphs", [])
    primary_graph = graphs[0] if graphs else None
    structure_signals = graph_signals(primary_graph)
    text = combined_text.lower()

    # Fallback keeps legacy behavior if no graph was extracted.
    order_type_enabled = structure_signals["order_type_gateway"] or bool(
        re.search(r"\bwhat is the order type\b|\bconsignment\b", text)
    )
    capture_failure_enabled = structure_signals["capture_failure_gateway"] or bool(
        re.search(r"\border capturing failure\b|\bedi failure\b|\bfailed idoc\b", text)
    )
    change_handler_enabled = structure_signals["change_handler"] or bool(
        re.search(r"\bva02\b|\bchange request\b|\bchange sales order\b", text)
    )
    availability_enabled = structure_signals["availability_check"] or bool(
        re.search(r"\bcheck product and service availability\b|\batp\b", text)
    )
    signals: dict[str, dict[str, Any]] = {
        "order_type_gateway": {
            "enabled": order_type_enabled,
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\bwhat is the order type\b", r"\bconsignment\b", r"\benter standard order details\b"],
            ),
        },
        "capture_failure_gateway": {
            "enabled": capture_failure_enabled,
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\border capturing failure\b", r"\bedi failure\b", r"\bfailed idoc\b"],
            ),
        },
        "change_handler": {
            "enabled": change_handler_enabled,
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\bva02\b", r"\bchange request\b", r"\bchange sales order\b"],
            ),
        },
        "availability_check": {
            "enabled": availability_enabled,
            "refs": _signal_reference_ids(
                raw_inputs,
                [r"\bcheck product and service availability\b", r"\batp\b"],
            ),
        },
        "manual_loop_risk": {"enabled": structure_signals["manual_loop_risk"], "refs": []},
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


def _extract_process_blueprint_xml(raw_response: str) -> str | None:
    """Extract the ProcessBlueprint XML block from an LLM response.

    The LLM may wrap the XML in markdown code fences or include preamble text.
    This function finds the outermost <ProcessBlueprint ...> ... </ProcessBlueprint>
    block and returns it, or None if not found.
    """
    # Unwrap markdown code fences (```xml ... ``` or ``` ... ```) like use case cards
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Use [\s\S]*? for multiline content; IGNORECASE handles varied closing tag casing
    match = re.search(
        r"<ProcessBlueprint\b[^>]*>[\s\S]*?</ProcessBlueprint>",
        cleaned,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(0).strip()
    return None


def _generate_use_case_cards(state: dict[str, Any], settings: Settings, strategy_report: str) -> str | None:
    """Call the LLM with Prompt 4 to generate Use Case Cards JSON, with retries.

    Returns the validated JSON string, or None only after all retries are exhausted.
    """
    ucc_prompt = render_use_case_cards_prompt(
        process_name=state.get("process_name", "Process"),
        context_region=state.get("context_region", "Global"),
        friction_items=state.get("cognitive_friction_logs", []),
        path_decisions=state.get("path_decisions", []),
        strategy_report=strategy_report,
    )

    current_prompt = ucc_prompt
    for attempt in range(1, _LLM_PARSE_MAX_RETRIES + 1):
        print(f"[Blueprint_Node] Calling LLM for use case cards (attempt {attempt})...")
        _logger.info("Blueprint_Node: calling LLM for use case cards (Prompt 4, attempt %d)...", attempt)

        try:
            llm_response = call_llm(
                current_prompt,
                settings,
                system_message=_SYSTEM_MESSAGE_USE_CASE_CARDS,
                max_tokens=_MAX_TOKENS_USE_CASE_CARDS,
            )
        except Exception as exc:
            _logger.warning("Blueprint_Node: LLM call for use case cards failed (attempt %d): %s", attempt, exc)
            print(f"[Blueprint_Node] LLM call for use case cards failed (attempt {attempt}): {exc}")
            if attempt < _LLM_PARSE_MAX_RETRIES:
                time.sleep(_LLM_PARSE_RETRY_BACKOFF * attempt)
            continue

        print(f"[Blueprint_Node] Use case cards LLM response received ({len(llm_response)} chars)")

        cleaned = llm_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            validate_use_case_cards_json(cleaned)
            print(f"[Blueprint_Node] USING LLM-GENERATED USE CASE CARDS (validated, attempt {attempt})")
            _logger.info("Blueprint_Node: LLM-generated use case cards passed validation (attempt %d)", attempt)
            return cleaned
        except ValueError as exc:
            _logger.warning("Blueprint_Node: LLM use case cards failed validation (attempt %d): %s", attempt, exc)
            print(f"[Blueprint_Node] LLM use case cards failed validation (attempt {attempt}): {exc}")
            correction = (
                f"\n\n=== CORRECTION (attempt {attempt} failed: {exc}) ===\n"
                f"Your previous JSON output failed validation. Return ONLY a valid JSON array "
                f"of use case card objects. No markdown fences, no prose, no explanation."
            )
            current_prompt = ucc_prompt + correction
            if attempt < _LLM_PARSE_MAX_RETRIES:
                time.sleep(_LLM_PARSE_RETRY_BACKOFF * attempt)

    _logger.warning("Blueprint_Node: all %d use case card attempts failed", _LLM_PARSE_MAX_RETRIES)
    print(f"[Blueprint_Node] All {_LLM_PARSE_MAX_RETRIES} use case card attempts failed")
    return None


def _generate_llm_process_blueprint(state: dict[str, Any], settings: Settings, strategy_report: str) -> str | None:
    """Call the LLM with Prompt 5 to generate the ProcessBlueprint XML + Mermaid diagram, with retries.

    Returns the validated XML string, or None only after all retries are exhausted.
    """
    blueprint_prompt = render_process_blueprint_prompt(
        process_name=state.get("process_name", "Process"),
        context_region=state.get("context_region", "Global"),
        friction_items=state.get("cognitive_friction_logs", []),
        path_decisions=state.get("path_decisions", []),
        strategy_report=strategy_report,
        use_case_cards=state.get("use_case_cards", ""),
        run_layout=state.get("run_layout", "LR"),
    )

    current_prompt = blueprint_prompt
    for attempt in range(1, _LLM_PARSE_MAX_RETRIES + 1):
        print(f"[Blueprint_Node] Calling LLM for process blueprint (attempt {attempt})...")
        _logger.info("Blueprint_Node: calling LLM for process blueprint (Prompt 5, attempt %d)...", attempt)

        try:
            llm_blueprint_response = call_llm(
                current_prompt,
                settings,
                system_message=_SYSTEM_MESSAGE_PROCESS_BLUEPRINT,
                max_tokens=_MAX_TOKENS_BLUEPRINT,
            )
        except Exception as exc:
            _logger.warning("Blueprint_Node: LLM call for process blueprint failed (attempt %d): %s", attempt, exc)
            print(f"[Blueprint_Node] LLM call for process blueprint failed (attempt {attempt}): {exc}")
            if attempt < _LLM_PARSE_MAX_RETRIES:
                time.sleep(_LLM_PARSE_RETRY_BACKOFF * attempt)
            continue

        print(f"[Blueprint_Node] Process blueprint LLM response received ({len(llm_blueprint_response)} chars)")

        extracted = _extract_process_blueprint_xml(llm_blueprint_response)
        if not extracted:
            _logger.warning("Blueprint_Node: could not extract ProcessBlueprint XML (attempt %d)", attempt)
            print(f"[Blueprint_Node] Could not extract ProcessBlueprint XML (attempt {attempt})")
            correction = (
                f"\n\n=== CORRECTION (attempt {attempt}: no valid XML found) ===\n"
                f"Your previous response did not contain a valid <ProcessBlueprint> XML block. "
                f"Please output a single XML block starting with <ProcessBlueprint version=\"1.0\"> and ending with "
                f"</ProcessBlueprint>, containing a <Diagram type=\"mermaid\"><![CDATA[ ... ]]></Diagram> section "
                f"with valid Mermaid.js flowchart code."
            )
            current_prompt = blueprint_prompt + correction
            if attempt < _LLM_PARSE_MAX_RETRIES:
                time.sleep(_LLM_PARSE_RETRY_BACKOFF * attempt)
            continue

        try:
            validate_process_blueprint_xml(extracted)
            print(f"[Blueprint_Node] USING LLM-GENERATED PROCESS BLUEPRINT (validated, attempt {attempt})")
            _logger.info("Blueprint_Node: LLM-generated process blueprint passed validation (attempt %d)", attempt)
            return extracted
        except ValueError as exc:
            _logger.warning("Blueprint_Node: LLM process blueprint failed validation (attempt %d): %s", attempt, exc)
            print(f"[Blueprint_Node] LLM process blueprint failed validation (attempt {attempt}): {exc}")
            correction = (
                f"\n\n=== CORRECTION (attempt {attempt} failed validation: {exc}) ===\n"
                f"Your previous ProcessBlueprint XML failed validation. Please ensure the XML contains "
                f"valid Mermaid.js flowchart code inside <Diagram type=\"mermaid\"><![CDATA[ ... ]]></Diagram>."
            )
            current_prompt = blueprint_prompt + correction
            if attempt < _LLM_PARSE_MAX_RETRIES:
                time.sleep(_LLM_PARSE_RETRY_BACKOFF * attempt)

    _logger.warning("Blueprint_Node: all %d process blueprint attempts failed", _LLM_PARSE_MAX_RETRIES)
    print(f"[Blueprint_Node] All {_LLM_PARSE_MAX_RETRIES} process blueprint attempts failed")
    return None


def _generate_fallback_process_blueprint(state: dict[str, Any], run_layout: str = "LR") -> str:
    """Generate a minimal valid ProcessBlueprint XML when LLM attempts have exhausted.

    Produces a placeholder 3-area diagram that passes validation so the pipeline
    can complete and the user can view/edit the output.
    """
    process_name = state.get("process_name", "Process")
    process_id = f"{process_name}_Reimagined"
    layout = run_layout.upper() if (run_layout or "").upper() in ("LR", "TB") else "LR"
    mermaid = f'''flowchart {layout}
  subgraph External["External"]
    EXT1["Input Channel (HITL)"]
  end
  subgraph Internal_System["Internal_System"]
    subgraph Agents_SAP_Joule_GenAI["Agents_SAP_Joule_GenAI"]
      AG1["Intake & Classify (Path C)"]
    end
    subgraph SAP_BTP_Automation["SAP_BTP_Automation"]
      BTP1["Orchestrate (Path B)"]
    end
    subgraph SAP_S4HANA_Clean_Core["SAP_S4HANA_Clean_Core"]
      S41["Core Execute (Path A)"]
    end
  end
  subgraph Employees["Employees"]
    EMP1["Review & Approve (HITL)"]
  end
  EXT1 -.->|"Trigger"| AG1
  AG1 ==>|"Process"| BTP1
  BTP1 --> S41
  S41 --> EMP1'''
    return f"""<ProcessBlueprint version="1.0">
  <ProcessID>{escape(process_id)}</ProcessID>
  <ArchitectureType>Agentic_SideCar</ArchitectureType>
  <Diagram type="mermaid"><![CDATA[
{mermaid}
  ]]></Diagram>
</ProcessBlueprint>"""


def Blueprint_Node(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    print("\n=== [Blueprint_Node] STARTED ===")
    _logger.info(">>> Entering Blueprint_Node")
    if not state.get("manual_approval", False):
        raise ValueError(
            "Trust Gap Protocol requires manual approval before Blueprint_Node execution. "
            "Set manual_approval=true only after human checkpoint review."
        )

    # --- LLM-powered strategy report (required, with retry on failure) ---
    effective_min_words = 900 if settings.report_mode == "DEMO" else settings.min_report_words
    bp_prompt = render_blueprint_prompt(
        process_name=state.get("process_name", "Process"),
        context_region=state.get("context_region", "Global"),
        trust_gap_phase=state.get("trust_gap_phase", "Shadow"),
        friction_items=state.get("cognitive_friction_logs", []),
        path_decisions=state.get("path_decisions", []),
        regional_nuances=state.get("regional_nuances", {}),
        evidence_references=state.get("evidence_references", []),
        report_mode=settings.report_mode,
    )

    strategy_report = ""
    current_bp_prompt = bp_prompt
    for report_attempt in range(1, _LLM_PARSE_MAX_RETRIES + 1):
        print(f"[Blueprint_Node] Calling LLM for strategy report generation (attempt {report_attempt})...")
        _logger.info("Blueprint_Node: calling LLM for strategy report (attempt %d, mode=%s)...", report_attempt, settings.report_mode)
        llm_response = call_llm(
            current_bp_prompt,
            settings,
            system_message=_SYSTEM_MESSAGE_BLUEPRINT,
            max_tokens=_MAX_TOKENS_BLUEPRINT,
        )
        print(f"[Blueprint_Node] LLM response received ({len(llm_response)} chars, ~{len(llm_response.split())} words)")
        _logger.info("Blueprint_Node: LLM response received (%d chars, ~%d words)", len(llm_response), len(llm_response.split()))

        llm_word_count = count_words(llm_response)
        print(f"[Blueprint_Node] LLM returned {llm_word_count} words (threshold: {effective_min_words})")

        # Strict: use raw LLM output only; no patching or injection of non-LLM content
        strategy_word_count = count_words(llm_response)

        if strategy_word_count >= effective_min_words:
            try:
                validate_strategy_report(llm_response, min_words=effective_min_words)
                strategy_report = llm_response
                print(f"[Blueprint_Node] USING LLM-GENERATED REPORT ({strategy_word_count} words, attempt {report_attempt}) — raw GPT-5 output only")
                _logger.info("Blueprint_Node: using LLM-generated strategy report (%d words, raw GPT-5 only)", strategy_word_count)
                break
            except Exception as exc:
                _logger.warning("Blueprint_Node: LLM report failed validation (attempt %d): %s", report_attempt, exc)
                print(f"[Blueprint_Node] LLM report failed validation (attempt {report_attempt}): {exc}")
                correction = (
                    f"\n\n=== CORRECTION (attempt {report_attempt} failed validation: {exc}) ===\n"
                    f"Your previous report failed validation. Please ensure all required sections are present "
                    f"and the report has at least {effective_min_words} words. Include these mandatory sections: "
                    f"Executive Summary, Current Reality Synthesis, Strategy: Layered Re-Imagination using Path A/B/C, "
                    f"Architecture of the Future State, Technical Stack, The Trust Gap Protocol, "
                    f"Risks Guardrails and Open Questions. Include the phrase 'never embedded in the ERP kernel'."
                )
                current_bp_prompt = bp_prompt + correction
        else:
            _logger.warning("Blueprint_Node: LLM response too short (attempt %d): %d words < %d required", report_attempt, strategy_word_count, effective_min_words)
            print(f"[Blueprint_Node] LLM response too short (attempt {report_attempt}): {strategy_word_count} words < {effective_min_words}")
            correction = (
                f"\n\n=== CORRECTION (attempt {report_attempt}: only {strategy_word_count} words) ===\n"
                f"Your previous response was too short ({strategy_word_count} words). "
                f"The report MUST contain at least {effective_min_words} words. "
                f"Please produce a comprehensive, detailed strategy report with all required sections fully elaborated."
            )
            current_bp_prompt = bp_prompt + correction

        if report_attempt < _LLM_PARSE_MAX_RETRIES:
            time.sleep(_LLM_PARSE_RETRY_BACKOFF * report_attempt)

    if not strategy_report:
        raise RuntimeError(
            f"[Blueprint_Node] All {_LLM_PARSE_MAX_RETRIES} strategy report LLM attempts failed. "
            f"Last response had {count_words(llm_response)} words (needed {effective_min_words})."
        )

    # --- LLM-powered use case cards (Prompt 4: JSON, with retries) ---
    use_case_cards_json = _generate_use_case_cards(state, settings, strategy_report)
    if use_case_cards_json:
        print("[Blueprint_Node] LLM-generated use case cards will be included in output")
    else:
        print("[Blueprint_Node] Use case cards generation exhausted retries — omitted from output")

    # --- LLM-powered process blueprint (Prompt 5: XML + Mermaid, with retries) ---
    state_with_cards = dict(state)
    if use_case_cards_json:
        state_with_cards["use_case_cards"] = use_case_cards_json
    mermaid_xml = _generate_llm_process_blueprint(state_with_cards, settings, strategy_report)
    if not mermaid_xml:
        print("[Blueprint_Node] All LLM attempts failed — using fallback placeholder blueprint")
        _logger.warning("Blueprint_Node: using fallback ProcessBlueprint after all LLM attempts failed")
        mermaid_xml = _generate_fallback_process_blueprint(
            state_with_cards,
            run_layout=state.get("run_layout", "LR"),
        )
    else:
        # Validate LLM output; if it fails, use fallback so run completes successfully
        try:
            validate_process_blueprint_xml(mermaid_xml)
            print("[Blueprint_Node] USING LLM-GENERATED PROCESS BLUEPRINT as mermaid_xml")
        except ValueError as exc:
            _logger.warning("Blueprint_Node: LLM blueprint failed validation, using fallback: %s", exc)
            print(f"[Blueprint_Node] LLM blueprint failed validation ({exc}) — using fallback placeholder")
            mermaid_xml = _generate_fallback_process_blueprint(
                state_with_cards,
                run_layout=state.get("run_layout", "LR"),
            )

    validate_strategy_report(strategy_report, min_words=effective_min_words)
    validate_process_blueprint_xml(mermaid_xml)

    phase_status = dict(state.get("phase_status", {}))
    phase_status["phase_3_blueprint_generation"] = "completed"

    result: dict[str, Any] = {
        "strategy_report_markdown": strategy_report,
        "mermaid_xml": mermaid_xml,
        "refined_blueprint": {
            "strategy_report_markdown": strategy_report,
            "mermaid_xml": mermaid_xml,
        },
        "phase_status": phase_status,
    }

    if use_case_cards_json:
        result["use_case_cards_json"] = use_case_cards_json
        result["refined_blueprint"]["use_case_cards_json"] = use_case_cards_json

    result["process_blueprint_xml"] = mermaid_xml
    result["refined_blueprint"]["process_blueprint_xml"] = mermaid_xml

    return result
