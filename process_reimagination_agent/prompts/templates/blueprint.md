TASK: Re-Imagined Strategy Report Generation (Markdown Output Only)

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Generate a comprehensive Re-Imagined Strategy Report for the process
transformation. The report must be authoritative, technical, and actionable.

Inputs
1) Process name and region context.
2) Cognitive Friction Analysis table (friction points identified in Phase 1).
3) Path Design Decisions (A/B/C classifications from Phase 2).
4) Regional nuances and policy registry.
5) Source evidence register from uploaded documents.

Output (STRICT)
Produce a Markdown strategy report with AT LEAST 2000 words containing these sections in order:
1. **Executive Summary** — "One Big Move" synthesis (3-5 sentences).
2. **Cognitive Friction Analysis** — The friction table (reproduce as-is).
3. **Source Evidence Register** — Reference table from uploaded artifacts.
4. **Architecture of the Future State** — Hub-and-spoke operating model with agent personas.
5. **Technical Stack** — System of Intelligence, System of Record, integration contracts.
6. **Integration Design Deep Dive** — Staged processing contract (intake, classification, ERP posting).
7. **Agent Persona Reasoning Model** — Intake Scribe, Intent Analyzer, Dispute Judge boundaries.
8. **The Trust Gap Protocol** — Shadow / Co-Pilot / Autopilot phases with confidence thresholds.
9. **Path Design Decisions** — Bullet list of each friction point's path assignment with rationale.
10. **Regional Policy Registry** — JSON block of regional nuances.
11. **Delivery and Rollout Plan** — Wave 1/2/3 with KPIs, exit criteria, and governance.
12. **Appendix: Control and Operability Baseline** — Schema validation, retries, idempotency, governance.
13. **Executive Simplified Summary** — Exactly 3 sentences for non-technical stakeholders.

Rules
- Use ONLY what is supported by the provided inputs.
- Keep Clean Core enforcement explicit: all custom logic in Side-Car, never in ERP kernel.
- Each section must add substantive content, not repeat other sections.
- The report title must be: "# Re-Imagined Strategy Report: {process_name}"
- The Appendix section heading must appear exactly once.
- The Executive Simplified Summary must contain exactly 3 sentences.

Begin
Read the inputs and generate the strategy report in Markdown.

=== PROCESS CONTEXT ===
Process: {process_name}
Region: {context_region}
Trust Gap Phase: {trust_gap_phase}

=== COGNITIVE FRICTION TABLE ===
{friction_table}

=== PATH DESIGN DECISIONS ===
{path_decisions}

=== REGIONAL NUANCES ===
{regional_nuances}

=== SOURCE EVIDENCE REGISTER ===
{evidence_register}
