@echo off
chcp 65001 >nul 2>&1
cd /d %~dp0
mkdir workspace 2>nul
mkdir Skills 2>nul
mkdir Tools 2>nul
icacls workspace /grant %USERNAME%:(OI)(CI)M /T
icacls Skills /grant %USERNAME%:(OI)(CI)M /T
icacls Tools /grant %USERNAME%:(OI)(CI)M /T

echo ========================================
echo   正在启动 DeepScience 服务...
echo ========================================
docker compose -f docker-compose-release.yml up -d

echo.
echo 正在等待服务启动，每 2 秒检测一次...
echo.

:check_loop
timeout /t 2 /nobreak >nul

curl -fsS http://127.0.0.1:5173 >nul 2>&1
if %errorlevel% neq 0 (
    echo [%time%] 服务尚未就绪，继续等待...
    goto check_loop
)

echo.
echo ========================================
echo   服务启动成功！正在打开浏览器...
echo ========================================
start http://127.0.0.1:5173
