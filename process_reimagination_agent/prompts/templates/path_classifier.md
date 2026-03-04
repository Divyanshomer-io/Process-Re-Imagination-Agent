TASK: Path Classification (A/B/C) for Friction Points (Table Output Only)

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Classify each friction point into exactly one of three paths:
- Path A (Core Standardization): revert/force to standard ERP/CRM functionality.
- Path B (Platform Automation): deterministic automation (workflows/RPA).
- Path C (Agentic AI Deployment): probabilistic reasoning (GenAI agents).

Inputs
You will receive:
1) A "Cognitive Friction Analysis" table of friction points
2) The same source documents (for evidence cross-check)

Suitability Rule (STRICT — must be explicit in justification)
Assign Path C ONLY if the task requires at least one:
- Perception (reading/extracting unstructured inputs like emails/PDF/free text)
- Reasoning (trade-off analysis, multi-step judgment)
- Adaptive Action (dynamic exception handling/planning)
If not, prefer Path B or Path A.

Output (STRICT)
Produce ONLY a JSON array titled "path_classifications".
Each element must have these keys:
- friction_id
- recommended_path (A / B / C)
- suitability_justification (1–2 lines; MUST reference rule-based vs perception/reasoning/adaptive action)
- core_vs_sidecar_orientation (Core / Side-Car / Hybrid)
- human_supervision_needed (Yes / No / Conditional)
- confidence (High / Medium / Low)
- evidence (Document + page/section supporting classification)
- open_questions (if classification depends on missing info, else empty string)

Rules
- Map 1:1 to the Friction_IDs from the friction table.
- Use evidence from the provided documents.
- Do not invent technologies or tools not stated in the documents.
- Keep "Core vs Side-Car" conceptual (no vendor/tool names unless stated).

Begin
Classify all friction points and output the JSON array only.

=== COGNITIVE FRICTION TABLE ===
{friction_table}

=== SOURCE EVIDENCE REGISTER ===
{evidence_register}
