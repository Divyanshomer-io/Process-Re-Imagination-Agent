PROMPT 2 — PATH A/B/C CLASSIFIER (SAP-SPECIFIC) — TABLE OUTPUT ONLY

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Classify each Item_ID into exactly one SAP-specific path:

- Path A (Core Standardization — SAP S/4HANA Clean Core):
  Standardize back to SAP S/4HANA standard process/rules/config; reduce custom variance.

- Path B (Platform Enhancements / Deterministic Automation — SAP BTP):
  Deterministic automation such as workflows, routing, validations, integrations, and orchestration on SAP BTP.

- Path C (Agentic AI Deployment — SAP Joule / GenAI):
  Assign if the task requires at least one:
    1) Perception (reading/extracting from unstructured sources: emails, PDFs, fax, free text, scans, OCR, invoices, attachments, natural language parsing, document interpretation),
    2) Reasoning (trade-off analysis, multi-step judgment, contextual evaluation, ambiguity resolution, prioritization, triage, assessment, reconciliation, cross-referencing, matching, classification, inference),
    3) Adaptive Action (dynamic exception handling, planning, escalation, fallback, contingency, anomaly detection, case-by-case decisions, real-time recovery, rerouting, ad hoc workflows, deviation handling).
  IMPORTANT: Carefully read the source documents below to determine whether a friction point truly involves perception, reasoning, or adaptive action — do not rely solely on the summary table.

Inputs
You will receive:
1) "Pain Points & Opportunities (A/B/C Candidates)" table from Prompt 1
2) The same source documents (for evidence cross-check)

Suitability Rule
Assign Path C when Perception, Reasoning, or Adaptive Action is genuinely required based on the source documents.
If the task is purely rule-based/deterministic, prefer Path B or Path A.
When in doubt, review the source document text provided below and assign Path C if the evidence supports it.

Output (STRICT)
Produce ONLY a table titled "Path Classification (A/B/C) — SAP".
Do not include narrative outside the table.

Rules (STRICT)
- Map 1:1 to Item_ID from Prompt 1.
- Use evidence from the provided documents.
- Do not invent SAP products/services beyond: SAP S/4HANA, SAP BTP, SAP Joule/GenAI.
- Do NOT output URLs or local file paths.

Table Columns (STRICT)
- Item_ID
- Recommended_Path (A / B / C)
- Suitability_Justification (1–2 lines; MUST reference rule-based vs perception/reasoning/adaptive action)
- SAP_Target (SAP S/4HANA | SAP BTP | SAP Joule/GenAI)
- Core_vs_SideCar_Orientation (Core / Side-Car / Hybrid — conceptual)
- Human_Supervision_Needed (Yes / No / Conditional)
- Confidence (High / Medium / Low)
- Evidence (Document + page/section supporting classification)
- Open_Questions (if classification depends on missing info)

Begin
Classify all items and output the "Path Classification (A/B/C) — SAP" table only.

=== PAIN POINTS & OPPORTUNITIES TABLE ===
{friction_table}

=== SOURCE EVIDENCE REGISTER ===
{evidence_register}
