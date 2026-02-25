# Process-Re-Imagination-Agent

LangGraph implementation of the McCain Agentic Process Re-Imagination Architect.

## What this project does
- Ingests unstructured process inputs (PDF, PPTX, text, CSV).
- Runs mandatory 3-phase transformation:
1. Phase 1: Current Reality Synthesis.
2. Phase 2: Path A/B/C Suitability Assessment.
3. Phase 3: Strategy Report + XML/Mermaid Blueprint generation.
- Uses a non-linear graph with quality-control loop and confidence threshold `>95%`.
- Uses Trust Gap checkpointing with `MemorySaver` and `interrupt_before=["Blueprint_Node"]`.
- Enforces Clean Core + Side-Car architecture rules.

## Install
```powershell
python -m pip install -r requirements.txt
```

## Run
```powershell
python -m process_reimagination_agent run `
  --process-name "Order Intake" `
  --context-region "ANZ" `
  --pain-point "Manual email/PDF order entry" `
  --pain-point "Frequent order modifications" `
  --file "sample_inputs/order_intake_notes.txt" `
  --thread-id "demo-thread-001"
```

This command pauses before `Blueprint_Node` for manual approval and stores:
- `outputs/<thread_id>/pending_state.json`

## Resume after approval
```powershell
python -m process_reimagination_agent resume `
  --thread-id "demo-thread-001" `
  --approver "architect.user" `
  --notes "Trust gap review approved"
```

Final outputs:
- `outputs/<thread_id>/strategy_report.md`
- `outputs/<thread_id>/process_blueprint.xml` (`<VisualArchitecture version="2.0">` XML wrapper)
- `outputs/<thread_id>/process_blueprint.mmd` (raw Mermaid graph)
- `outputs/<thread_id>/process_blueprint.svg` (rendered image, auto-generated when `mmdc` or `npx` is available)

If SVG is not generated, set `CHROME_PATH` to your Chrome executable and rerun `resume`:
```powershell
$env:CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
```

## Regional rules hardcoded
- `ANZ VA01` is an exception fallback rule.
- `Uruguay Power Street` is an external channel adapter rule.
- Both are enforced in runtime routing metadata, not report-only text.
