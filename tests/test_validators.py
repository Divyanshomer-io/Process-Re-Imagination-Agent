import pytest

from process_reimagination_agent.validators import validate_mermaid_xml, validate_strategy_report


def _valid_report(min_words: int = 2000) -> str:
    base = """
## Executive Summary
Clean Core and Side-Car operating model for agentic orchestration with custom logic never embedded in the ERP kernel.

## Pain Points & Opportunities (A/B/C Candidates)
| [Current Manual Action] | Friction Type | Proposed Path | Rationale | Expected KPI Shift |
|---|---|---|---|---|
| Manual order entry | Human middleware | C | Requires perception and reasoning | 50% faster |

## Architecture of the Future State
Agent personas drive intake, adjudication, and orchestration.

## Technical Stack
System of Intelligence in Side-Car, System of Record in Core ERP, with custom logic never embedded in the ERP kernel.

## The Trust Gap Protocol
Shadow to Co-Pilot to Autopilot with strict confidence controls.

## Appendix: Control and Operability Baseline
Single instance section only.

## Executive Simplified Summary
This design reduces manual work and speeds order processing. It protects ERP stability by keeping custom logic in the Side-Car layer. It scales automation safely with strong trust controls.
"""
    report = base
    padding = (
        "Additional implementation detail expands integration governance, persona reasoning, control design, and rollout "
        "execution while maintaining non-repetitive section headings and preserving Clean Core boundaries. "
    )
    while len(report.split()) < min_words:
        report = report.replace(
            "## Appendix: Control and Operability Baseline",
            f"{padding}\n\n## Appendix: Control and Operability Baseline",
            1,
        )
    return report


def test_validate_strategy_report_accepts_compliant_content() -> None:
    report = _valid_report()
    validate_strategy_report(report, min_words=2000)


def test_validate_mermaid_xml_accepts_compliant_xml() -> None:
    xml = """<VisualArchitecture version="2.0">
  <Region>Uruguay</Region>
  <DiagramType>Tiered_Agentic_SideCar</DiagramType>
  <MermaidData><![CDATA[
graph TD
  subgraph External_Intake [Customer Channels]
    CH_EMAIL([Email/PDF]):::external
    CH_CHAT([WhatsApp/Chat]):::external
    CH_EDI([EDI/Portal]):::external
    UY_SYNC{{Power Street Sync}}:::agent
  end

  subgraph Agentic_SideCar [Intelligent Automation]
    AG_SCRIBE{{Doc Extractor}}:::agent
    AG_INTENT{{Intent Analyzer}}:::agent
    AG_DISPUTE{{Dispute Resolver}}:::agent
    WF_ROUTER([Order Router]):::workflow
    WF_VALIDATOR([Validator]):::workflow
    WF_FORMAT([Format Engine]):::workflow
    DB_POLICY[(Policy Rules)]:::persistence
  end

  subgraph Clean_Core_ERP [Core System]
    ERP_VA01[Create Order]:::core
    ERP_MD[Validation]:::core
    ERP_POST[Post Order]:::core
    DB_S4[(Master Data)]:::persistence
  end

  CH_EMAIL -->|Send| UY_SYNC
  CH_CHAT -->|Send| UY_SYNC
  CH_EDI -->|Submit| UY_SYNC
  UY_SYNC -->|Process| AG_SCRIBE
  WF_ROUTER -.->|Process| AG_SCRIBE
  AG_SCRIBE -->|Structured Data| AG_INTENT
  AG_INTENT -.->|Apply Rules| DB_POLICY
  AG_INTENT -->|Validate| WF_VALIDATOR
  WF_VALIDATOR -->|Format| WF_FORMAT
  AG_INTENT -->|Exception to Resolve| AG_DISPUTE
  AG_DISPUTE -.->|Resolve Case| ERP_VA01
  WF_FORMAT -.->|Post to System| ERP_VA01
  ERP_VA01 -->|Update| ERP_MD
  ERP_MD -.->|Check Data| DB_S4
  ERP_MD ==>|Post to System| ERP_POST
  ERP_POST -->|Notify Status| WF_ROUTER
  ]]></MermaidData>
</VisualArchitecture>"""
    validate_mermaid_xml(xml)


def test_validate_mermaid_xml_rejects_missing_china_gateway() -> None:
    # China region requires CN_GATEWAY and routing through it; this diagram routes directly to WF_ROUTER.
    xml = """<VisualArchitecture version="2.0">
  <Region>China</Region>
  <DiagramType>Tiered_Agentic_SideCar</DiagramType>
  <MermaidData><![CDATA[
graph TD
  subgraph External_Intake [Customer Channels]
    CH_EMAIL([Email/PDF]):::external
    CH_CHAT([WhatsApp/Chat]):::external
    CH_EDI([EDI/Portal]):::external
  end
  subgraph Agentic_SideCar [Intelligent Automation]
    AG_SCRIBE{{Doc Extractor}}:::agent
    AG_INTENT{{Intent Analyzer}}:::agent
    AG_DISPUTE{{Dispute Resolver}}:::agent
    WF_ROUTER([Order Router]):::workflow
    WF_VALIDATOR([Validator]):::workflow
    WF_FORMAT([Format Engine]):::workflow
    DB_POLICY[(Policy Rules)]:::persistence
  end
  subgraph Clean_Core_ERP [Core System]
    ERP_VA01[Create Order]:::core
    ERP_MD[Validation]:::core
    ERP_POST[Post Order]:::core
    DB_S4[(Master Data)]:::persistence
  end
  CH_EMAIL -->|Send| WF_ROUTER
  CH_CHAT -->|Send| WF_ROUTER
  CH_EDI -->|Submit| WF_ROUTER
  WF_ROUTER -.->|Process| AG_SCRIBE
  AG_SCRIBE -->|Structured Data| AG_INTENT
  AG_INTENT -.->|Apply Rules| DB_POLICY
  AG_INTENT -->|Validate| WF_VALIDATOR
  WF_VALIDATOR -->|Format| WF_FORMAT
  AG_INTENT -->|Exception to Resolve| AG_DISPUTE
  AG_DISPUTE -.->|Resolve Case| ERP_VA01
  WF_FORMAT -.->|Post to System| ERP_VA01
  ERP_VA01 -->|Update| ERP_MD
  ERP_MD -.->|Check Data| DB_S4
  ERP_MD ==>|Post to System| ERP_POST
  ERP_POST -->|Notify Status| WF_ROUTER
  ]]></MermaidData>
</VisualArchitecture>"""
    with pytest.raises(ValueError):
        validate_mermaid_xml(xml)


def test_validate_strategy_report_rejects_short_report() -> None:
    with pytest.raises(ValueError):
        validate_strategy_report("## Executive Summary short", min_words=2000)


def test_validate_strategy_report_rejects_duplicate_appendix() -> None:
    report = _valid_report()
    report = report.replace(
        "## Appendix: Control and Operability Baseline",
        "## Appendix: Control and Operability Baseline\none\n\n## Appendix: Control and Operability Baseline",
        1,
    )
    with pytest.raises(ValueError):
        validate_strategy_report(report, min_words=2000)


def test_validate_strategy_report_rejects_invalid_summary_sentence_count() -> None:
    report = _valid_report()
    report = report.replace(
        "This design reduces manual work and speeds order processing. It protects ERP stability by keeping custom logic in the Side-Car layer. It scales automation safely with strong trust controls.",
        "This design reduces manual work and speeds order processing. It protects ERP stability by keeping custom logic in the Side-Car layer.",
        1,
    )
    with pytest.raises(ValueError):
        validate_strategy_report(report, min_words=2000)
