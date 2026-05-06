@echo off
REM One-time firewall fix — right-click this file and choose "Run as administrator"
REM After this runs once you never need it again (start.bat handles it going forward).

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please right-click this file and choose "Run as administrator"
    pause
    exit /b 1
)

echo Opening port 8001 in Windows Firewall...
powershell -Command ^
  "if (-not (Get-NetFirewallRule -DisplayName 'RPC Dashboard (port 8001)' -ErrorAction SilentlyContinue)) {" ^
  "  New-NetFirewallRule -DisplayName 'RPC Dashboard (port 8001)'" ^
  "    -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Any | Out-Null;" ^
  "  Write-Host 'Done — port 8001 is now open.' -ForegroundColor Green" ^
  "} else { Write-Host 'Already open — nothing to do.' -ForegroundColor Green }"

echo.
echo Tell your RPC to try http://LEUS12517215942:8001 again now.
echo.
pause
