# Process-Re-Imagination-Agent — Start Frontend + Backend
# Run from: Process-Re-Imagination-Agent (repo root)
#
# First-time: Run "npm install" in frontend/ or run install.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

# Start backend (port 8001) in background
Write-Host "Starting backend on http://localhost:8001..."
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001" -WorkingDirectory $Root

Start-Sleep -Seconds 2

# Start frontend (Vite dev server)
Write-Host "Starting frontend at http://localhost:5173..."
Set-Location $Frontend
$vitePath = Join-Path $Frontend "node_modules\.bin\vite"
if (Test-Path $vitePath) {
    & $vitePath
} elseif (Test-Path (Join-Path $Frontend "pnpm-lock.yaml")) {
    pnpm run dev
} else {
    npm run dev
}
