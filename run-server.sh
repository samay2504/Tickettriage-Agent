#!/bin/bash
echo "Starting Ticket Triage Agent Backend Server..."
echo ""
echo "Server will be available at: http://localhost:8000"
echo "UI available at: http://localhost:8000/ui"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
