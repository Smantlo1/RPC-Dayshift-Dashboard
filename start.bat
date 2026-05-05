@echo off
REM RPC Operating Dashboard — Startup Script
echo Starting RPC Operating Dashboard...
cd /d "%~dp0"
start "" "http://127.0.0.1:8001/"
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
