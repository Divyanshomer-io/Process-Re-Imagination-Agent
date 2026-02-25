import pytest

from process_reimagination_agent.validators import validate_mermaid_xml, validate_strategy_report


def _valid_report(min_words: int = 2000) -> str:
    base = """
## Executive Summary
Clean Core and Side-Car operating model for agentic orchestration.

## Cognitive Friction Analysis
| [Current Manual Action] | Friction Type | Proposed Path | Rationale | Expected KPI Shift |
|---|---|---|---|---|
| Manual order entry | Human middleware | C | Requires perception and reasoning | 50% faster |

## Architecture of the Future State
Agent personas drive intake, adjudication, and orchestration.

## Technical Stack
System of Intelligence in Side-Car, System of Record in Core ERP.

## The Trust Gap Protocol
Shadow to Co-Pilot to Autopilot with strict confidence controls.
"""
    words = base.split()
    while len(words) < min_words:
        words.extend("control policy validation clean core side-car".split())
    return " ".join(words)


def test_validate_strategy_report_accepts_compliant_content() -> None:
    report = _valid_report()
    validate_strategy_report(report, min_words=2000)


def test_validate_mermaid_xml_accepts_compliant_xml() -> None:
    xml = """<VisualArchitecture version="2.0">
  <Region>Uruguay</Region>
  <DiagramType>Tiered_Agentic_SideCar</DiagramType>
  <MermaidData><![CDATA[
graph TD
  subgraph Zone_A [Omni-Channel Intake Tier]
    CH_EMAIL([Email/PDF Intake]):::external
    CH_CHAT([WhatsApp/Chat Intake]):::external
    CH_EDI([EDI Intake]):::external
    UY_SYNC{{Power Street Sync}}:::agent
  end

  subgraph Zone_B [Agentic Side-Car Orchestrator]
    AG_SCRIBE{{The Scribe}}:::agent
    AG_INTENT{{Intent Analyzer}}:::agent
    AG_DISPUTE{{Dispute Judge}}:::agent
    WF_ROUTER([Email Router]):::workflow
    WF_VALIDATOR([Data Validator]):::workflow
    WF_FORMAT([Formatting Engine]):::workflow
    DB_POLICY[(Regional Policy DB)]:::persistence
  end

  subgraph Zone_C [The Clean Core (SAP ERP)]
    ERP_VA01[VA01 API]:::core
    ERP_MD[Master Data Check]:::core
    ERP_POST[Final Order Posting]:::core
    DB_S4[(S/4HANA Master Data)]:::persistence
  end

  CH_EMAIL -->|Webhook| UY_SYNC
  CH_CHAT -->|Webhook| UY_SYNC
  CH_EDI -->|AS2| UY_SYNC
  UY_SYNC -->|gRPC| AG_SCRIBE
  WF_ROUTER -.->|Event Bus| AG_SCRIBE
  AG_SCRIBE -->|JSON Payload| AG_INTENT
  AG_INTENT -.->|Policy Query API| DB_POLICY
  AG_INTENT -->|Validation RPC| WF_VALIDATOR
  WF_VALIDATOR -->|Schema Rules| WF_FORMAT
  AG_INTENT -->|Exception Context| AG_DISPUTE
  AG_DISPUTE -.->|Case Resolution API| ERP_VA01
  WF_FORMAT -.->|OData API| ERP_VA01
  ERP_VA01 -->|BAPI/OData| ERP_MD
  ERP_MD -.->|Master Data Read| DB_S4
  ERP_MD ==>|OData API| ERP_POST
  ERP_POST -->|Status Webhook| WF_ROUTER
  ]]></MermaidData>
</VisualArchitecture>"""
    validate_mermaid_xml(xml)


def test_validate_mermaid_xml_rejects_missing_china_gateway() -> None:
    xml = """<VisualArchitecture version="2.0">
  <Region>China</Region>
  <DiagramType>Tiered_Agentic_SideCar</DiagramType>
  <MermaidData><![CDATA[
graph TD
  subgraph Zone_A [Omni-Channel Intake Tier]
    CH_EMAIL([Email/PDF Intake]):::external
    CH_CHAT([WhatsApp/Chat Intake]):::external
    CH_EDI([EDI Intake]):::external
  end
  subgraph Zone_B [Agentic Side-Car Orchestrator]
    AG_SCRIBE{{The Scribe}}:::agent
    AG_INTENT{{Intent Analyzer}}:::agent
    AG_DISPUTE{{Dispute Judge}}:::agent
    WF_ROUTER([Email Router]):::workflow
    WF_VALIDATOR([Data Validator]):::workflow
    WF_FORMAT([Formatting Engine]):::workflow
    DB_POLICY[(Regional Policy DB)]:::persistence
  end
  subgraph Zone_C [The Clean Core (SAP ERP)]
    ERP_VA01[VA01 API]:::core
    ERP_MD[Master Data Check]:::core
    ERP_POST[Final Order Posting]:::core
    DB_S4[(S/4HANA Master Data)]:::persistence
  end
  CH_EMAIL -->|Webhook| WF_ROUTER
  CH_CHAT -->|Webhook| WF_ROUTER
  CH_EDI -->|AS2| WF_ROUTER
  WF_ROUTER -.->|Event Bus| AG_SCRIBE
  AG_SCRIBE -->|JSON Payload| AG_INTENT
  AG_INTENT -.->|Policy Query API| DB_POLICY
  AG_INTENT -->|Validation RPC| WF_VALIDATOR
  WF_VALIDATOR -->|Schema Rules| WF_FORMAT
  AG_INTENT -->|Exception Context| AG_DISPUTE
  AG_DISPUTE -.->|Case Resolution API| ERP_VA01
  WF_FORMAT -.->|OData API| ERP_VA01
  ERP_VA01 -->|BAPI/OData| ERP_MD
  ERP_MD -.->|Master Data Read| DB_S4
  ERP_MD ==>|OData API| ERP_POST
  ERP_POST -->|Status Webhook| WF_ROUTER
  ]]></MermaidData>
</VisualArchitecture>"""
    with pytest.raises(ValueError):
        validate_mermaid_xml(xml)


def test_validate_strategy_report_rejects_short_report() -> None:
    with pytest.raises(ValueError):
        validate_strategy_report("## Executive Summary short", min_words=2000)
