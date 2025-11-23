@echo off
REM NesHedgeFund - Windows Startup Script (Yahoo Finance)
REM Set Python and Node paths
set "PYTHON_PATH=C:\Program Files\Python311\python.exe"
set "NODE_PATH=C:\Program Files\nodejs"
set "PATH=%NODE_PATH%;%PATH%"

echo ========================================
echo   NesHedgeFund (Windows - Yahoo)
echo ========================================

REM Set environment for Yahoo Finance
set DATA_SOURCE=YAHOO

echo.
echo [1/2] Starting Python API (Port 8000)...
start "NesHedgeFund API" cmd /k "cd /d %~dp0trading_api && "%PYTHON_PATH%" -m uvicorn main:app --reload --port 8000"

timeout /t 3

echo.
echo [2/2] Starting Frontend (Port 3000)...
start "NesHedgeFund Web" cmd /k "cd /d %~dp0trading_web && npm.cmd run dev"

echo.
echo ========================================
echo   NesHedgeFund is running!
echo ========================================
echo   Dashboard: http://localhost:3000
echo   API: http://localhost:8000
echo   Data Source: Yahoo Finance
echo ========================================
echo.
echo Press any key to exit (services will keep running)
pause
