@echo off
title Discord Bot Moonlit

echo.
echo ========================================
echo   Discord Bot Moonlit
echo   Domain: moonlit-bot.my.id
echo ========================================
echo.

REM Check if cloudflared is installed
where cloudflared >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] cloudflared not found!
    echo Please install Cloudflare Tunnel first.
    echo Download: https://github.com/cloudflare/cloudflared/releases
    echo.
    pause
    exit /b 1
)

echo [1/3] Starting Cloudflare Tunnel...
start "Cloudflare Tunnel" cmd /c "cloudflared tunnel --config cloudflared.yml run"
timeout /t 3 >nul

echo [2/3] Activating Python virtual environment...
call .venv\Scripts\Activate.bat

echo [3/3] Starting Discord Bot...
echo.

python run.py

REM Cleanup when bot stops
echo.
echo Bot stopped. Closing Cloudflare Tunnel...
taskkill /F /IM cloudflared.exe 2>nul
deactivate

pause
