from __future__ import annotations

import re
from typing import Any


REQUIRED_REPORT_HEADINGS = [
    "## Executive Summary",
    "## Cognitive Friction Analysis",
    "## Architecture of the Future State",
    "## Technical Stack",
    "## The Trust Gap Protocol",
    "## Executive Simplified Summary",
]


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _count_sentences(text: str) -> int:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return 0
    return len(re.findall(r"[^.!?]+[.!?]", normalized))


def validate_phase1_executed(state: dict[str, Any]) -> None:
    phase_status = state.get("phase_status", {})
    if phase_status.get("phase_1_current_reality_synthesis") != "completed":
        raise ValueError("Phase 1 was not completed. PHASE 1 is mandatory and cannot be skipped.")
    if not state.get("cognitive_friction_logs"):
        raise ValueError("Phase 1 produced no cognitive friction logs.")


def validate_path_decisions(path_decisions: list[dict[str, Any]]) -> None:
    if not path_decisions:
        raise ValueError("Path decisions are empty.")
    for decision in path_decisions:
        path = decision.get("path")
        if path not in {"A", "B", "C"}:
            raise ValueError(f"Invalid path decision '{path}'. Expected one of A/B/C.")
        if not decision.get("clean_core_guardrail"):
            raise ValueError("Missing Clean Core guardrail annotation.")
        if not decision.get("side_car_component"):
            raise ValueError("Missing Side-Car component annotation.")


def validate_strategy_report(report: str, min_words: int = 2000) -> None:
    for heading in REQUIRED_REPORT_HEADINGS:
        if heading not in report:
            raise ValueError(f"Missing required report section: {heading}")

    level2_headings = re.findall(r"^##\s+(.+)$", report, re.M)
    appendix_sections = [heading for heading in level2_headings if "appendix" in heading.lower()]
    control_baseline_sections = [
        heading for heading in level2_headings if ("control" in heading.lower() and "baseline" in heading.lower())
    ]
    if len(appendix_sections) != 1:
        raise ValueError("Appendix section must appear exactly once.")
    if len(control_baseline_sections) != 1:
        raise ValueError("Control Baseline section must appear exactly once.")

    summary_heading = "## Executive Simplified Summary"
    if report.count(summary_heading) != 1:
        raise ValueError("Executive Simplified Summary section must appear exactly once.")
    summary_body = report.split(summary_heading, 1)[1].strip()
    if "\n## " in summary_body:
        raise ValueError("Executive Simplified Summary must be the terminal section.")
    if _count_sentences(summary_body) != 3:
        raise ValueError("Executive Simplified Summary must contain exactly 3 sentences.")

    if "Clean Core" not in report:
        raise ValueError("Report must explicitly describe Clean Core strategy.")
    if "Side-Car" not in report and "Side Car" not in report:
        raise ValueError("Report must explicitly describe Side-Car strategy.")
    if "never embedded in the ERP kernel" not in report:
        raise ValueError("Report must explicitly state custom logic is never embedded in ERP kernel.")
    if count_words(report) < min_words:
        raise ValueError(f"Strategy report word count is below threshold {min_words}.")


def validate_mermaid_xml(mermaid_xml: str) -> None:
    try:
        from lxml import etree  # type: ignore[import-not-found]

        root = etree.fromstring(mermaid_xml.encode("utf-8"))
    except Exception as exc:
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(mermaid_xml)
        except Exception as fallback_exc:
            raise ValueError(f"Invalid XML format for blueprint: {fallback_exc}") from fallback_exc

    if root.tag != "VisualArchitecture":
        raise ValueError("Root element must be VisualArchitecture.")
    if root.attrib.get("version") != "2.0":
        raise ValueError("VisualArchitecture version must be 2.0.")

    region_element = root.find("Region")
    if region_element is None or not (region_element.text or "").strip():
        raise ValueError("Region element is required.")
    context_region = (region_element.text or "").strip().lower()

    diagram_type = root.find("DiagramType")
    if diagram_type is None or (diagram_type.text or "").strip() != "Tiered_Agentic_SideCar":
        raise ValueError("DiagramType must be Tiered_Agentic_SideCar.")

    mermaid_data = root.find("MermaidData")
    if mermaid_data is None:
        raise ValueError("MermaidData element missing.")

    content = (mermaid_data.text or "").strip()
    # Structure: required subgraphs and connection types (business-friendly labels).
    required_structure = [
        "graph TD",
        "subgraph External_Intake",
        "subgraph Agentic_SideCar",
        "subgraph Clean_Core_ERP",
        "{{Doc Extractor}}",
        "{{Intent Analyzer}}",
        "{{Dispute Resolver}}",
        "([Order Router])",
        "([Validator])",
        "([Format Engine])",
        "[Create Order]",
        "[Validation]",
        "[Post Order]",
        "[(Master Data)]",
        "[(Policy Rules)]",
    ]
    for token in required_structure:
        if token not in content:
            raise ValueError(f"Mermaid diagram missing required structure: {token}")

    # Connection semantics: solid, dotted, and critical thick path must exist.
    if "-->|" not in content:
        raise ValueError("Mermaid diagram must include solid protocol-labeled flows (-->|...|).")
    if "-.->|" not in content:
        raise ValueError("Mermaid diagram must include dotted protocol-labeled flows (-.->|...|).")
    if "==>|" not in content:
        raise ValueError("Mermaid diagram must include thick protocol-labeled critical flow (==>|...|).")

    # Regional logic enforcement (structure and region-specific nodes).
    if "south africa" in context_region or context_region in {"za", "sa"}:
        if "[(Vector 3PL)]" not in content:
            raise ValueError("South Africa blueprint must include Vector 3PL persistence node.")
        if "Integration Link" not in content:
            raise ValueError("South Africa blueprint must include integration link.")
    if "uruguay" in context_region and "{{Power Street Sync}}" not in content:
        raise ValueError("Uruguay blueprint must include Power Street Sync adaptive intake node.")
    if "china" in context_region:
        if "CN_GATEWAY" not in content:
            raise ValueError("China blueprint must include regional gateway node.")
        if "CH_EMAIL -->|" not in content or "CN_GATEWAY" not in content:
            raise ValueError("China blueprint must route intake through gateway before Side-Car.")


def validate_methodology_compliance(state: dict[str, Any], min_report_words: int = 2000) -> None:
    validate_phase1_executed(state)
    phase_status = state.get("phase_status", {})
    if phase_status.get("phase_2_agentic_reasoning") != "completed":
        raise ValueError("Phase 2 was not completed.")
    validate_path_decisions(state.get("path_decisions", []))
    report = state.get("strategy_report_markdown", "")
    mermaid_xml = state.get("mermaid_xml", "")
    validate_strategy_report(report, min_words=min_report_words)
    validate_mermaid_xml(mermaid_xml)
