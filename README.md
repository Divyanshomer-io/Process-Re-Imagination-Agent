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
- `outputs/<thread_id>/friction_points.json` (Phase 1 synthesis artifact)
- `outputs/<thread_id>/path_classification.json` (Phase 2 pathing/confidence artifact)

Blueprint zoning contract (strict):
- `subgraph External_Intake [...]`
- `subgraph Agentic_SideCar [...]`
- `subgraph Clean_Core_ERP [...]`

Strategy report contract (strict):
- `## Appendix: Control and Operability Baseline` appears exactly once.
- Final section must be `## Executive Simplified Summary` with exactly 3 sentences.
- Report explicitly states custom logic is isolated in Side-Car and never embedded in ERP kernel.

If SVG is not generated, set `CHROME_PATH` to your Chrome executable and rerun `resume`:
```powershell
$env:CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
```

## OCR support
- Standalone image ingestion with OCR: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`, `.tif`.
- PDF ingestion includes text-layer extraction plus OCR for scanned/image-heavy pages with short text.
- PPTX ingestion includes OCR for inserted picture shapes in addition to regular text boxes.

System dependencies:
- Tesseract OCR must be installed and available on `PATH` for OCR extraction.
- Poppler is required for PDF page rendering via `pdf2image` (used for PDF OCR).
- If Tesseract or Poppler is missing, ingestion degrades gracefully and records warnings/errors; the workflow does not crash.

## Regional rules hardcoded
- `ANZ VA01` is an exception fallback rule.
- `Uruguay Power Street` is an external channel adapter rule.
- Both are enforced in runtime routing metadata, not report-only text.
