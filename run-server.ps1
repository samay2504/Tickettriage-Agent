#!/usr/bin/env pwsh
Write-Host "Starting Ticket Triage Agent Backend Server..." -ForegroundColor Cyan
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Green
Write-Host "UI available at: http://localhost:8000/ui" -ForegroundColor Green
Write-Host ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
