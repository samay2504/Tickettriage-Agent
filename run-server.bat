@echo off
echo Starting Ticket Triage Agent Backend Server...
echo.
cd /d "%~dp0"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
