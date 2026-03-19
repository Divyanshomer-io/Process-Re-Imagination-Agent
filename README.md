# Process-Re-Imagination-Agent

This repository implements the McCain Agentic Process Re-Imagination workflow using LangGraph.

The goal is simple: convert messy process artifacts (PDFs, PPTX, notes, CSV, images) into a structured, evidence-backed transformation package that can be reviewed and actioned by business and technical teams.

## Why This Project Exists

Most process redesign efforts fail because inputs are fragmented and outputs are generic. This project is opinionated and operational:

- It enforces a fixed 3-phase methodology (not ad-hoc prompting).
- It requires Trust Gap approval before blueprint generation.
- It ties recommendations to source evidence (`DOC#` references).
- It enforces Clean Core + Side-Car constraints in generated architecture outputs.

## What The Agent Produces

For each run, the pipeline generates:

- Current-state friction analysis (markdown + JSON)
- Path suitability classification (A/B/C)
- Strategy report (structured and validated)
- Blueprint XML + Mermaid graph (+ SVG when renderer is available)
- Optional use-case cards JSON when present in model output

## End-To-End Flow

1. Ingestion: parse files and extract text (with OCR fallback where available).
2. Phase 1: synthesize current reality and friction points.
3. Phase 2: classify each friction point into Path A/B/C suitability.
4. Quality gate loop: enforce confidence and methodology constraints.
5. Trust Gap checkpoint: execution pauses before `Blueprint_Node`.
6. Manual approval (`resume`): generate final blueprint and report.

## Quick Start (UI — Frontend + Backend)

From the `Process-Re-Imagination-Agent` folder (repo root):

1. **Install** (once):
   ```powershell
   .\install.ps1
   ```
   Or: `cd frontend` then `npm install` (or `npx pnpm install` if npm fails on OneDrive paths)

2. **Run**:
   ```powershell
   .\run.ps1
   ```
   Or on Windows: `run.bat`

- Backend: http://localhost:8001  
- Frontend: http://localhost:5173  

If `npm install` fails with `ENOTEMPTY` or `EPERM` (common on OneDrive), use `npx pnpm install` in the frontend folder instead.

## Repository Layout

- `process_reimagination_agent/` core application code
- `process_reimagination_agent/prompts/` prompt modules and templates
- `sample_inputs/` example input files
- `outputs/` per-thread run outputs
- `artifacts/` persisted state, dead letters, and resumable snapshots
- `tests/` unit/integration tests

## Run Locally (New User Guide)

### 1. Prerequisites

- Python 3.11+ (3.12 recommended)
- `pip`
- One configured LLM backend:
  - DAIA (`DAIA_CLIENT_ID`, `DAIA_CLIENT_SECRET`) or
  - Azure OpenAI (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`) or
  - OpenAI (`OPENAI_API_KEY`)
- Optional for better document extraction:
  - Tesseract OCR on PATH
  - Poppler on PATH (for PDF OCR via `pdf2image`)
- Optional for Mermaid SVG rendering:
  - `mmdc` or `npx` + Chrome/Chromium

### 2. Clone + virtual environment

```powershell
git clone https://github.com/Divyanshomer-io/Process-Re-Imagination-Agent.git
cd Process-Re-Imagination-Agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and configure at least one backend.

DAIA example:

```dotenv
DAIA_BASE_URL=https://daia.privatelink.azurewebsites.net
DAIA_CLIENT_ID=your-client-id
DAIA_CLIENT_SECRET=your-client-secret
DAIA_MODEL=gpt-5
# Optional if your enterprise cert chain requires it:
# DAIA_CA_BUNDLE=certs/mccain_ca_bundle.pem
```

Azure OpenAI example:

```dotenv
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21
```

OpenAI example:

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 4. Run the workflow

Use repeatable `--file` arguments for multiple inputs:

```powershell
python -m process_reimagination_agent run `
  --process-name "Order Intake" `
  --context-region "Global" `
  --pain-point "Manual order entry from email/PDF" `
  --file "sample_inputs/order_intake_notes.txt" `
  --file "sample_inputs/diagram_flow_sample.txt" `
  --thread-id "demo-order-intake-001"
```

Notes:

- `--process-name` is required.
- `--context-region` is required.
- `--pain-point` is optional and repeatable.
- `--file` is optional and repeatable.
- If `--thread-id` is omitted, one is auto-generated.

### 5. Approve checkpoint and continue

`run` pauses before blueprint generation. Continue with:

```powershell
python -m process_reimagination_agent resume `
  --thread-id "demo-order-intake-001" `
  --approver "your.name" `
  --notes "Trust gap review approved"
```

### 6. Final output files

Generated under `outputs/<thread_id>/`:

- `strategy_report.md`
- `process_blueprint.xml`
- `process_blueprint.mmd`
- `process_blueprint.svg` (if renderer is available)
- `friction_points.md`
- `friction_points.json`
- `path_classification.md`
- `use_case_cards.json` (if available)
- `final_state.json`
- `metrics*.json` and `slo_dashboard.md` (if metrics enabled)

## Run With Your Own PDFs (Example)

```powershell
python -m process_reimagination_agent run `
  --process-name "Order Intake" `
  --context-region "Global" `
  --file "C:\Users\<you>\Downloads\L4 - Enter Order Into System - 1.0.0 (1).pdf" `
  --file "C:\Users\<you>\Downloads\L3 - Perform Order Intake vf (1) (1).pdf" `
  --thread-id "two-pdf-global-001"
```

Then approve:

```powershell
python -m process_reimagination_agent resume `
  --thread-id "two-pdf-global-001" `
  --approver "<you>"
```

### `CERTIFICATE_VERIFY_FAILED` with DAIA

Set a valid CA bundle path:

```powershell
$env:DAIA_CA_BUNDLE="C:\path\to\ca_bundle.pem"
$env:REQUESTS_CA_BUNDLE=$env:DAIA_CA_BUNDLE
$env:SSL_CERT_FILE=$env:DAIA_CA_BUNDLE
```

### SVG not generated

Install `mmdc` or Node.js + `npx`, and ensure Chrome path is available:

```powershell
$env:CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
```

Then rerun `resume`.

## Developer Commands

```powershell
python -m process_reimagination_agent run --help
python -m process_reimagination_agent resume --help
pytest -q
```
