PROMPT 4 — USE CASE CARDS (PORTFOLIO) — OUTPUT ONLY (JSON)

Role: Principal Enterprise AI Architect and Business Transformation Strategist.
Mode: High reasoning.

Goal
Generate a portfolio of Use Case Cards in a consulting-ready format.
Cards must be grounded in the Strategy Report and Path A/B/C decisions.

Inputs you will receive
1) Pain Points & Opportunities table (Prompt 1)
2) Path Classification (A/B/C) — SAP table (Prompt 2)
3) Strategy Report (Prompt 3)

Output format (STRICT)
Return ONLY JSON (no prose) with this structure:

{{
  "process_name": "...",
  "run_scope": "...",
  "use_case_cards": [
    {{
      "use_case_id": "UC-01",
      "title": "...",
      "path": "A|B|C",
      "sap_target": "SAP S/4HANA|SAP BTP|SAP Joule/GenAI",
      "context": {{
        "region": "Global|<RegionName>",
        "where_in_process": "...",
        "trigger_or_channel": "..."
      }},
      "agent_role_or_owner": "Persona name (Path C) OR 'SAP BTP Automation' (Path B) OR 'SAP S/4HANA Standardization' (Path A)",
      "mechanism": ["Step 1 ...", "Step 2 ...", "Step 3 ..."],
      "tech_mapping": {{
        "system_of_record": ["SAP S/4HANA (or SAP ECC if inputs explicitly state ECC)"],
        "sap_btp": ["SAP BTP (or 'Not specified in inputs')"],
        "sap_joule_genai": ["SAP Joule/GenAI (or 'Not specified in inputs')"],
        "integrations_or_interfaces": ["..."]
      }},
      "value": {{
        "type": ["Efficiency","Accuracy","Speed","Compliance"],
        "statement": "Qualitative value; include numeric benefits ONLY if explicitly present in inputs.",
        "kpi_numbers": []
      }},
      "human_in_the_loop": {{ "required": true, "when": "..." }},
      "dependencies_and_risks": ["..."],
      "evidence": [
        {{ "doc":"...", "page_or_section":"...", "quote_or_paraphrase":"..." }}
      ]
    }}
  ]
}}

Rules (STRICT)
- Create cards primarily for Path C and major Path B items; include at least one Path A card.
- Do not invent tech names beyond SAP S/4HANA, SAP BTP, SAP Joule/GenAI; if not stated in inputs, use "Not specified in inputs".
- Do not output URLs or local file paths.
- Each card must cite at least 1 evidence item.
- Ensure use_case_id increments sequentially (UC-01, UC-02…).

Begin
Generate the JSON use case cards now.

=== PROCESS CONTEXT ===
Process: {process_name}
Region: {context_region}

=== PAIN POINTS & OPPORTUNITIES TABLE (Prompt 1 output) ===
{friction_table}

=== PATH CLASSIFICATION TABLE (Prompt 2 output) ===
{path_classification_table}

=== STRATEGY REPORT (Prompt 3 output) ===
{strategy_report}
