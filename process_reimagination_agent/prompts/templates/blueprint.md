PROMPT 3 — RE-IMAGINED STRATEGY REPORT (MARKDOWN OUTPUT ONLY)
SAP CLEAN CORE (S/4HANA) + SAP BTP SIDE-CAR + SAP JOULE/GENAI (AGENTIC)

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Generate a comprehensive Strategy Report that re-imagines the provided process
into a "Zero-Touch Agentic Ecosystem" using:
- Clean Core (SAP S/4HANA as System of Record),
- Side-Car (SAP BTP for orchestration/automation),
- Agentic AI (SAP Joule/GenAI) only where suitability requires it.

The report must use Path A/B/C decisions as the organizing logic.

Inputs you will receive
1) Pain Points & Opportunities table (Prompt 1)
2) Path Classification (A/B/C) — SAP table (Prompt 2)
3) Source documents (As-Is + regional practices + benchmark/best practices if provided)

Evidence rules (STRICT)
- Do NOT output any URLs or local file paths.
- Every major recommendation must cite Evidence as: {{Document Name, Page/Section, short quote/paraphrase}}.
- Do not invent technologies not present in inputs; if uncertain, state "Not specified in inputs".

Output requirements (STRICT)
- Output ONLY a Markdown document.
- Tone: authoritative, technical, strategic. Avoid marketing fluff.
- Length: 2000+ words unless REPORT_MODE is DEMO; if DEMO, 900-1200 words. Current REPORT_MODE: {report_mode}.
- The report title must be: "# Re-Imagined Strategy Report: {process_name}"
- Must include sections in this exact order:

1) **Executive Summary** — "One Big Move"
2) **Current Reality Synthesis**
   - include "Hotspots" listing top 5 Item_IDs with evidence
3) **Strategy: Layered Re-Imagination using Path A/B/C**
   - Path A: SAP S/4HANA Core Standardization (Foundation)
   - Path B: SAP BTP Platform Enhancements / Deterministic Automation (Bridge)
   - Path C: SAP Joule/GenAI Agentic AI Deployment (Game Changer)
4) **Architecture of the Future State**
   - Hub-and-Spoke operating model
   - Define at least 3 Agent Personas with: responsibilities, inputs, decisions, outputs, and escalation triggers
5) **Technical Stack**
   - System of Record: SAP S/4HANA
   - Side-Car: SAP BTP orchestration/automation
   - Agentic: SAP Joule/GenAI
6) **The Trust Gap Protocol**
   - Shadow -> Co-Pilot -> Autopilot operationalization
7) **Risks, Guardrails, and Open Questions**

Additional rules
- Use ONLY what is supported by the provided inputs.
- Keep Clean Core enforcement explicit: all custom logic in Side-Car, never embedded in the ERP kernel.
- Each section must add substantive content, not repeat other sections.

Begin
Write the Strategy Report now, grounded in the tables and source documents with citations as specified.

=== PROCESS CONTEXT ===
Process: {process_name}
Region: {context_region}
Trust Gap Phase: {trust_gap_phase}

=== PAIN POINTS & OPPORTUNITIES TABLE ===
{friction_table}

=== PATH DESIGN DECISIONS ===
{path_decisions}

=== REGIONAL NUANCES ===
{regional_nuances}

=== SOURCE EVIDENCE REGISTER ===
{evidence_register}
