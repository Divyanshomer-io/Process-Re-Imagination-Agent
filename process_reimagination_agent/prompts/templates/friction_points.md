PROMPT 1 — PAIN POINTS & OPPORTUNITIES EXTRACTOR (A/B/C CANDIDATES) — TABLE OUTPUT ONLY

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Extract a comprehensive list of pain points and improvement opportunities from the provided process inputs, including:
- Standardization gaps (candidates for SAP S/4HANA Clean Core standardization),
- Deterministic automation candidates (candidates for SAP BTP workflows/orchestration),
- Agentic candidates (candidates for SAP Joule / GenAI where perception, reasoning, or adaptive action is required).

Inputs
You will receive process maps, process documentation, regional nuances, and benchmark/best-practice material (if provided).

Output (STRICT)
Produce ONLY a table titled "Pain Points & Opportunities (A/B/C Candidates)".
Do not include narrative explanation outside the table.

Rules (STRICT)
- Use ONLY what is explicitly supported by the provided documents.
- If a detail is not stated, write "Not specified" and add it as an open question.
- Each row represents ONE discrete pain point/opportunity (one issue, one variance, one exception type, one control gap, or one deviation).
- Provide evidence per row: document name + page/section + short quote/paraphrase.
- Do NOT assign Path A/B/C in this prompt (classification happens in Prompt 2).
- Do NOT output URLs or local file paths.

Table Columns (STRICT)
- Item_ID (P-001, P-002…)
- Issue_or_Opportunity (short label)
- Current_Observed_Practice (what happens today; can be manual, exception, workaround, variance, or delay)
- Where_in_Process (step/activity name as stated)
- Trigger_or_Input_Channel (only if stated)
- Region_Impacted (Global or specific regions only if stated)
- Systems_or_Tools_Mentioned (only what is stated; else "Not specified")
- Why_It_Matters (1–2 lines: delay, errors, rework, compliance risk, fragmentation, cost)
- Evidence (Document + page/section + quote/paraphrase)
- Open_Questions (only when needed)

Begin
Read the inputs and output the "Pain Points & Opportunities (A/B/C Candidates)" table only.
