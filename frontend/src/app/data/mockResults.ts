export const mockFrictionData = [
  {
    id: "F001",
    manualAction: "Manual data entry from paper forms into GX-Core",
    whereInProcess: "Field visit data capture",
    region: "North America",
    whyItMatters: "Causes delays, rework, and error risk when automation breaks. Manual entry and intervention are required for exceptions, new SKUs, or data sync failures.",
    evidenceText: "L4 - Enter Order Into System, p.5 (NORTH AMERICA) — \"Manual entry and intervention are required for exceptions, new SKUs, or data sync failures\"",
    openQuestions: "Volume/frequency of exceptions not specified",
    evidenceCount: 3,
    relatedPainPoints: ["Time-consuming manual entry", "High error rate"],
    evidence: ["Field-Visit-Form-Template.pdf", "Error-Report-Q4.xlsx"],
    pathClassification: "C"
  },
  {
    id: "F002",
    manualAction: "Email-based approval routing for recommendations",
    whereInProcess: "Recommendation approval",
    region: "All Regions",
    whyItMatters: "Increases processing time and risk of inconsistent handling for exports. For export manual changes are required on specific scenarios.",
    evidenceText: "L4 - Enter Order Into System, p.5 (NORTH AMERICA) — \"For export manual changes are required on specific scenarios ex. Same sold to/ship to and different incoterms depending on l...\"",
    openQuestions: "Which scenarios recur most not specified",
    evidenceCount: 2,
    relatedPainPoints: ["Delayed approvals", "Lost emails"],
    evidence: ["Email-Thread-Sample.pdf"],
    pathClassification: "B"
  },
  {
    id: "F003",
    manualAction: "Manual reconciliation of grower records across systems",
    whereInProcess: "Data synchronization",
    region: "Europe",
    whyItMatters: "Data inconsistencies across systems lead to time-intensive reconciliation, delayed decisions, and risk of acting on stale data.",
    evidenceText: "Reconciliation-Report.xlsx, System-Comparison.pdf — \"Grower records diverge across GX-Core and Ag-Core within 48 hours of manual entry\"",
    openQuestions: "Frequency of reconciliation cycles and acceptable staleness threshold not defined",
    evidenceCount: 4,
    relatedPainPoints: ["Data inconsistencies", "Time-intensive reconciliation"],
    evidence: ["Reconciliation-Report.xlsx", "System-Comparison.pdf"],
    pathClassification: "A"
  },
];

export const mockPathData = [
  {
    item: "F001",
    path: "C",
    suitabilityReason: "Requires perception (OCR, handwriting), reasoning (validation), and adaptive action",
    notes: "Shadow mode with human verification initially"
  },
  {
    item: "F002",
    path: "B",
    suitabilityReason: "Deterministic workflow with clear rules and thresholds",
    notes: "Can be automated with Salesforce Flow or similar"
  },
  {
    item: "F003",
    path: "A",
    suitabilityReason: "Core standardization needed - single source of truth",
    notes: "Consolidate to Ag-Core as master system"
  },
  {
    item: "Grower profile creation",
    path: "C",
    suitabilityReason: "Requires data enrichment, validation, and intelligent field mapping",
    notes: "Agent can learn from patterns and suggest improvements"
  },
];

export const mockStrategyReport = `# Executive Summary: One Big Move

**Transform field operations from manual data orchestration to intelligent, agent-assisted workflows**

The analysis reveals that 60% of field rep time is spent on data middleware activities—manual entry, reconciliation, and routing. By deploying a coordinated system of Agentic AI and platform automation, we can reclaim this time for high-value grower interactions while improving data quality and decision speed.

## Architecture of the Future State

### Agent Personas

**1. Field Data Agent**
- **Role:** Capture, validate, and enrich field visit data
- **Capabilities:** OCR, handwriting recognition, contextual validation, auto-fill from historical patterns
- **Trust Protocol:** Shadow → Co-Pilot → Autopilot over 6 months

**2. Recommendation Agent**
- **Role:** Generate and route agronomic recommendations
- **Capabilities:** Pattern matching against best practices, regulatory compliance checking, automated routing
- **Trust Protocol:** Co-Pilot with human approval required

**3. Data Reconciliation Agent**
- **Role:** Synchronize grower records across systems
- **Capabilities:** Intelligent matching, conflict resolution, master data governance
- **Trust Protocol:** Autopilot for standard cases, escalate edge cases

## Technical Stack

### System of Intelligence (Side-Car Pattern)

**AI Orchestration Layer:**
- LangChain/LangGraph for agent orchestration
- Vector database (Pinecot/Weaviate) for context and memory
- LLM: GPT-4 or Claude for reasoning tasks

**Integration Middleware:**
- Event-driven architecture (Kafka/RabbitMQ)
- API gateway for system-of-record connectivity
- Real-time sync with bi-directional data flow

### System of Record (Existing)

- **GX-Core (Salesforce):** Customer master, field activities
- **Farmlink/Passport:** Operational data
- **Ag-Core:** Data warehouse and analytics
- **Outsystems (RQI/Farmvisit):** Field visit workflows

## Trust Gap Protocol

### Shadow Mode (Months 1-2)
- Agents operate in parallel with human processes
- Output logged but not acted upon
- Human teams review and provide feedback
- Success metrics: 95% accuracy vs human baseline

### Co-Pilot Mode (Months 3-4)
- Agents provide suggestions and pre-filled forms
- Humans review and approve before execution
- Feedback loop refines agent behavior
- Success metrics: 80% acceptance rate, 50% time savings

### Autopilot Mode (Months 5+)
- Agents execute routine tasks autonomously
- Human supervision for edge cases only
- Continuous monitoring and quality checks
- Success metrics: 70% full automation, <2% error rate

## Implementation Roadmap

**Phase 1 (Months 1-3):** Field Data Agent pilot in North America
**Phase 2 (Months 4-6):** Recommendation Agent rollout + expand Field Data Agent
**Phase 3 (Months 7-9):** Data Reconciliation Agent + full regional expansion
**Phase 4 (Months 10-12):** Optimization and advanced capabilities

## Expected Outcomes

- **60% reduction** in manual data entry time
- **40% improvement** in data quality and consistency
- **3x faster** recommendation turnaround
- **Field rep time reallocation:** 10+ hours/week to grower engagement
`;

export const mockBlueprintXML = `<process-blueprint>
  <metadata>
    <process-name>Field Operations Re-imagination</process-name>
    <generated-date>2026-02-18</generated-date>
  </metadata>
  <mermaid>
graph TB
  subgraph External["External Channel Layer"]
    Grower[Grower]
    FieldRep[Field Rep]
  end
  
  subgraph AgentLayer["AI Agent Layer (Agentic Orchestration)"]
    FieldAgent[Field Data Agent<br/>Path C]
    RecAgent[Recommendation Agent<br/>Path C]
    DataAgent[Data Reconciliation Agent<br/>Path C]
  end
  
  subgraph Automation["Platform Automation Layer"]
    ApprovalFlow[Approval Workflow<br/>Path B]
    NotificationEngine[Notification Engine<br/>Path B]
  end
  
  subgraph CoreSystem["Core System Layer"]
    GXCore[GX-Core<br/>Salesforce]
    Farmlink[Farmlink/Passport]
    AgCore[Ag-Core]
  end
  
  FieldRep -->|Field Visit Data| FieldAgent
  FieldAgent -->|Validated Data| GXCore
  FieldAgent -->|Enriched Context| RecAgent
  RecAgent -->|Recommendation| ApprovalFlow
  ApprovalFlow -->|Approved| NotificationEngine
  NotificationEngine -->|Alert| Grower
  GXCore -->|Grower Records| DataAgent
  Farmlink -->|Operational Data| DataAgent
  DataAgent -->|Reconciled Data| AgCore
  </mermaid>
</process-blueprint>`;

export const mockUseCases = [
  {
    id: "UC001",
    context: "Field rep completes grower visit and needs to capture data on mobile device",
    agentRole: "Field Data Agent",
    mechanism: "OCR + handwriting recognition on photos of paper forms, contextual validation against historical data, auto-population of standard fields",
    tech: "GPT-4 Vision, Custom OCR, Mobile SDK",
    value: "Reduce data entry time from 20 min to 2 min per visit; improve accuracy from 85% to 98%"
  },
  {
    id: "UC002",
    context: "Agronomic recommendation needs to be generated and routed for approval",
    agentRole: "Recommendation Agent",
    mechanism: "Pattern matching against best practices library, regulatory compliance check, intelligent routing based on complexity and value",
    tech: "LangChain, Vector DB, Rules Engine",
    value: "Reduce recommendation turnaround from 48 hours to 4 hours; ensure 100% compliance"
  },
  {
    id: "UC003",
    context: "Grower record exists in multiple systems with conflicting data",
    agentRole: "Data Reconciliation Agent",
    mechanism: "Fuzzy matching across systems, confidence scoring, automated resolution for high-confidence matches, escalation for edge cases",
    tech: "Dedupe Libraries, ML Matching Models, Workflow Engine",
    value: "Eliminate 15 hours/week of manual reconciliation; achieve single source of truth"
  },
];
