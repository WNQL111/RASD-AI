@echo off
setlocal enabledelayedexpansion
title RASD AI Enterprise Security Operations Center (SOC) - رَصْد AI
color 0A
cls

:START_SYSTEM
echo ====================================================================
echo      STARTING RASD AI SECURITY OPERATIONS CENTER (SOC) - رَصْد AI
echo ====================================================================
echo.

REM 1. Clean up any stale processes from previous runs
echo [*] Clearing stale processes on ports 8001, 4000, 4001...
call "%~dp0stop.bat" >nul 2>&1

REM 2. Check if Docker is installed and running
set DOCKER_RUNNING=0
tasklist /fi "imagename eq Docker Desktop.exe" 2>nul | find /i "Docker Desktop.exe" >nul
if %errorlevel% equ 0 (
    echo [+] Docker Desktop process detected. Checking daemon connectivity...
    docker info >nul 2>&1
    if !errorlevel! equ 0 (
        set DOCKER_RUNNING=1
    )
)

if %DOCKER_RUNNING% equ 1 (
    echo [+] Docker Desktop Engine is active.
    echo [1/3] Launching Docker Microservices in background...
    docker-compose up -d
    if !errorlevel! neq 0 (
        echo [!] Docker compose encountered an issue. Falling back to Native Mode...
        set DOCKER_RUNNING=0
    )
)

if %DOCKER_RUNNING% equ 0 (
    echo [i] Starting RASD AI in Native High-Performance Mode...
    echo.
    echo [1/3] Starting Backend API Engine on port 8001...
    start "RASD AI Backend [Port 8001]" /min cmd /c "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
    
    echo [2/3] Starting Frontend SOC Dashboard on port 4000...
    start "RASD AI Frontend [Port 4000]" /min cmd /c "cd /d "%~dp0frontend" && npm run dev"
)

echo.
echo [3/3] Verifying services health and readiness...
python "%~dp0tools\check_health.py"

set ACTIVE_PORT=4000
if exist "%~dp0tools\active_port.txt" (
    set /p ACTIVE_PORT=<"%~dp0tools\active_port.txt"
)

cls
color 0B
echo ====================================================================
echo      RASD AI ENTERPRISE SOC PLATFORM IS ONLINE AND READY! (رَصْد AI)
echo ====================================================================
echo.
echo  [+] Web Dashboard URL:    http://localhost:!ACTIVE_PORT!
echo  [+] Backend API Docs:     http://localhost:8001/docs
echo  [+] AI Pipeline Engine:   Direct CUDA / Local Acceleration
echo  [+] Local Database:       SQLite (asis_v2.db)
echo.
echo ====================================================================
echo.
echo Opening RASD AI Dashboard in default browser...
start http://localhost:!ACTIVE_PORT!

echo.
echo ====================================================================
echo Platform is active and running in background.
echo Choose an option below (servers remain running):
echo ====================================================================

:MENU_LOOP
echo.
echo   [1] Open Dashboard in Browser (http://localhost:!ACTIVE_PORT!)
echo   [2] Open Backend API Swagger Docs (http://localhost:8001/docs)
echo   [3] Restart RASD AI Services
echo   [4] Stop All Services and Exit
echo.
set "USER_CHOICE="
set /p USER_CHOICE="RASD AI > "

if "!USER_CHOICE!"=="1" (
    start http://localhost:!ACTIVE_PORT!
    goto MENU_LOOP
)
if "!USER_CHOICE!"=="2" (
    start http://localhost:8001/docs
    goto MENU_LOOP
)
if "!USER_CHOICE!"=="3" (
    echo.
    echo [*] Restarting all services...
    call "%~dp0stop.bat"
    cls
    goto START_SYSTEM
)
if /i "!USER_CHOICE!"=="4" goto CLEAN_EXIT
if /i "!USER_CHOICE!"=="stop" goto CLEAN_EXIT
if /i "!USER_CHOICE!"=="exit" goto CLEAN_EXIT
if /i "!USER_CHOICE!"=="q" goto CLEAN_EXIT

goto MENU_LOOP

:CLEAN_EXIT
echo.
echo [*] Terminating RASD AI services...
call "%~dp0stop.bat"
echo.
echo ====================================================================
echo RASD AI (رَصْد AI) has been shut down cleanly. Goodbye!
echo ====================================================================
ping 127.0.0.1 -n 3 >nul
exit /b 0
