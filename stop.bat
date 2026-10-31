@echo off
title Stopping RASD AI Platform - رَصْد AI
color 0C
cls

echo ====================================================================
echo      STOPPING RASD AI SERVICES AND WORKSTATION - رَصْد AI
echo ====================================================================
echo.

echo [*] Terminating Backend and Frontend services on ports 8001, 4000, 4001...
powershell -NoProfile -Command "$ports = @(8001, 4000, 4001); foreach ($p in $ports) { try { $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue; foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host ('   [+] Terminated process PID ' + $c.OwningProcess + ' on port ' + $p) } } catch {} }"

REM If Docker was running, also ensure containers are stopped
where docker >nul 2>&1
if %errorlevel% equ 0 (
    docker info >nul 2>&1
    if %errorlevel% equ 0 (
        echo [*] Stopping any running Docker containers...
        docker-compose down >nul 2>&1
    )
)

echo.
echo ====================================================================
echo   [OK] All RASD AI services have been stopped successfully.
echo ====================================================================
ping 127.0.0.1 -n 3 >nul
