TASK: Pain Points & Opportunities Refinement (JSON Output Only)

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Refine the existing Pain Points & Opportunities analysis based on quality feedback.
Strengthen evidence mapping, clarify descriptions, and ensure
every row is grounded in source documents.

Inputs
1) The current Pain Points & Opportunities table (may have weak evidence or vague descriptions).
2) Quality feedback identifying gaps.
3) Source evidence register from uploaded documents.

Output (STRICT)
Produce ONLY a JSON array of refined friction items.
Each element must have these keys:
- friction_id (Item_ID, e.g. P-001)
- issue_or_opportunity (short label)
- current_manual_action (improved description of current observed practice)
- where_in_process (step/activity name; "Not specified" if unknown)
- trigger_or_input_channel (only if stated; else "Not specified")
- region_impacted (Global or specific region)
- systems_or_tools_mentioned (only what is stated; else "Not specified")
- why_its_friction (1-2 lines: delay, rework, errors, compliance risk)
- source_evidence (document name + page/section + quote/paraphrase)
- open_questions (only when needed; else empty string)
- friction_type (category of friction)
- proposed_path (A, B, or C)
- rationale (1-2 lines justifying path assignment)
- expected_kpi_shift (expected improvement)
- requires_perception (true/false)
- requires_reasoning (true/false)
- requires_adaptive_action (true/false)

Rules
- Preserve all existing friction_ids; do not add or remove rows.
- Improve descriptions and evidence grounding based on the quality feedback.
- If evidence is weak, note this in open_questions.
- Use ONLY what is supported by the provided documents.

Begin
Read the inputs and output the refined JSON array only.

=== CURRENT FRICTION TABLE ===
{friction_table}

=== QUALITY FEEDBACK ===
{quality_feedback}

=== SOURCE EVIDENCE REGISTER ===
{evidence_register}
