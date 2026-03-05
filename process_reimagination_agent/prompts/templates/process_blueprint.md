PROMPT 5 — PROCESS BLUEPRINT (XML + MERMAID) — 3-AREA VISUAL FORMAT

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Generate a "To-Be" process blueprint that visualizes the re-imagined workflow using:
- Hub-and-Spoke architecture
- Clean Core + Side-Car pattern (protect SAP S/4HANA clean core)
- Human-in-the-Loop at defined exception points

Blueprint must be consistent with Strategy Report, Path A/B/C decisions, and Use Case Cards.

Inputs you will receive
1) Strategy Report (Prompt 3)
2) Path Classification (A/B/C) — SAP table (Prompt 2)
3) Pain Points & Opportunities table (Prompt 1)
4) Use Case Cards (Prompt 4)

Output requirements (STRICT)
- Output ONLY a single XML block containing Mermaid.js code.
- Must be valid XML and valid Mermaid.
- Do NOT include any URLs or local file paths.

VISUAL FORMAT REQUIREMENT (STRICT)
Organize the diagram into exactly THREE top-level areas (subgraphs), in this order:
1) External
   - Customer-facing channels (only those stated in inputs)
2) Internal_System
   - SAP Joule/GenAI Agents (Path C)
   - SAP BTP Automation/Orchestration (Path B)
   - SAP S/4HANA Clean Core (Path A)
3) Employees
   - Human-in-the-loop roles (CSR/DC staff, approvers, exception handlers)

Within Internal_System, create nested subgraphs exactly:
- Agents_SAP_Joule_GenAI
- SAP_BTP_Automation
- SAP_S4HANA_Clean_Core

Node shapes (STRICT)
- Decisions: {{Decision}} or {{{{Decision}}}}
- Activities/subprocesses: [Task]

Path labeling (STRICT)
Every node label must include a suffix:
- (Path A) or (Path B) or (Path C) or (HITL)

Mermaid direction
Use flowchart {run_layout} unless otherwise specified.

Content rules (STRICT)
- Only include steps grounded in provided inputs.
- Do not invent systems/channels beyond SAP S/4HANA, SAP BTP, SAP Joule/GenAI unless explicitly stated in inputs.
- Ensure SAP write/execution actions are NOT labeled Path C:
  - Path C = interpretation/planning/perception/reasoning
  - Path B or Path A/Core = deterministic execution or core rules

XML wrapper (STRICT)
<ProcessBlueprint version="1.0">
  <ProcessID>{{PROCESS_NAME}}_Reimagined</ProcessID>
  <ArchitectureType>Agentic_SideCar</ArchitectureType>
  <Diagram type="mermaid">
    <![CDATA[
      (Mermaid code here)
    ]]>
  </Diagram>
</ProcessBlueprint>

Begin
Generate the XML-wrapped Mermaid blueprint now using the required 3-area visual format.

=== PROCESS CONTEXT ===
Process: {process_name}
Region: {context_region}

=== PAIN POINTS & OPPORTUNITIES TABLE (Prompt 1 output) ===
{friction_table}

=== PATH CLASSIFICATION TABLE (Prompt 2 output) ===
{path_classification_table}

=== STRATEGY REPORT SUMMARY (Prompt 3 output) ===
{strategy_report_summary}

=== USE CASE CARDS (Prompt 4 output) ===
{use_case_cards}
