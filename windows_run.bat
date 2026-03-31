@echo off
chcp 65001 >nul 2>&1
cd /d %~dp0
mkdir workspace 2>nul
mkdir workspace\obsidian_vault 2>nul
mkdir Skills 2>nul
mkdir Tools 2>nul
icacls workspace /grant %USERNAME%:(OI)(CI)M /T
icacls Skills /grant %USERNAME%:(OI)(CI)M /T
icacls Tools /grant %USERNAME%:(OI)(CI)M /T

echo ========================================
echo   Starting ScienceClaw release services...
echo ========================================
docker compose -f docker-compose-release.yml up -d

echo.
echo Waiting for services to become ready. Checking every 2 seconds...
echo.

:check_loop
timeout /t 2 /nobreak >nul

curl -fsS http://127.0.0.1:5173 >nul 2>&1
if %errorlevel% neq 0 (
    echo [%time%] Services are still starting...
    goto check_loop
)

echo.
echo ========================================
echo   ScienceClaw is ready. Opening the browser...
echo ========================================
start http://127.0.0.1:5173
