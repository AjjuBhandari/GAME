@echo off
title FreePlayZone Server
color 0A
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      FreePlayZone — Starting Server      ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found!
    echo  Download from: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit
)

echo  [OK] Python found
echo.

:: Install dependencies
echo  Installing dependencies...
pip install flask flask-cors werkzeug --quiet
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install packages.
    pause
    exit
)
echo  [OK] Dependencies ready
echo.

:: Start server
echo  ══════════════════════════════════════════════
echo  Server running at: http://localhost:5000
echo  Admin login:       pgnr_58 / admin123
echo  Press CTRL+C to stop the server
echo  ══════════════════════════════════════════════
echo.

:: Open browser after 2 seconds
start /b timeout /t 2 /nobreak >nul ^& start http://localhost:5000

python server.py
pause
