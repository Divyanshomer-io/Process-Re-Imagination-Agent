# Install dependencies — run once before first run.ps1 / run.bat
# From: Process-Re-Imagination-Agent (repo root)

$Root = $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

Write-Host "Installing frontend dependencies (including mermaid)..."
Set-Location $Frontend
# Use pnpm if npm fails with ENOTEMPTY (e.g. OneDrive); pnpm handles node_modules differently
$npmOk = $false
try { npm install 2>$null; $npmOk = $true } catch {}
if (-not $npmOk) {
    Write-Host "Trying pnpm (works better on OneDrive paths)..."
    npx pnpm install
}
Set-Location $Root
Write-Host "Done. Run run.ps1 or run.bat to start the app."
