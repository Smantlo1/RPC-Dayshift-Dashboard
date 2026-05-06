@echo off
REM RPC Operating Dashboard — Startup Script
REM Requests admin once to open firewall port 8001, then starts the server.

REM ── Check if we are already running as Administrator ──────────────────────
net session >nul 2>&1
if %errorlevel% == 0 goto :is_admin

REM ── Not admin — re-launch this script elevated via PowerShell UAC prompt ──
echo Requesting administrator access to open firewall port 8001...
powershell -Command "Start-Process cmd -ArgumentList '/c cd /d ""%~dp0"" && ""%~f0""' -Verb RunAs"
exit /b

:is_admin
REM ── Running as admin — ensure firewall rule exists ────────────────────────
powershell -Command ^
  "if (-not (Get-NetFirewallRule -DisplayName 'RPC Dashboard (port 8001)' -ErrorAction SilentlyContinue)) {" ^
  "  New-NetFirewallRule -DisplayName 'RPC Dashboard (port 8001)'" ^
  "    -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Any | Out-Null;" ^
  "  Write-Host 'Firewall rule created.'" ^
  "} else { Write-Host 'Firewall rule already exists.' }"

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
