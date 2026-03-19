@echo off
REM Install dependencies — run once before first run.bat
cd /d "%~dp0\frontend"
echo Installing frontend dependencies (including mermaid)...
call npm install
echo Done. Run run.bat to start the app.
