@echo off
REM Process-Re-Imagination-Agent — Quick run
REM From: Process-Re-Imagination-Agent (repo root)
REM First-time: run "cd frontend && npm install"

cd /d "%~dp0"

echo Starting backend on http://localhost:8001...
start "Backend" /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001

timeout /t 2 /nobreak >nul

echo Starting frontend at http://localhost:5173...
cd frontend
if exist "node_modules\.bin\vite.cmd" (
    call node_modules\.bin\vite.cmd
) else (
    call npm run dev
)
