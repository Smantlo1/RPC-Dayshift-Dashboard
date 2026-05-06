@echo off
REM RPC Operating Dashboard — Startup Script
echo.
echo  ====================================================
echo   RPC Daily Operating Dashboard
echo  ====================================================
echo   Your dashboard (local):   http://127.0.0.1:8001
echo   Shareable on Walmart net: http://LEUS12517215942:8001
echo  ====================================================
echo.
echo  Anyone on Walmart VPN or Eagle WiFi can use the
echo  shareable link above while this window is open.
echo.
cd /d "%~dp0"
start "" "http://127.0.0.1:8001/"
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
