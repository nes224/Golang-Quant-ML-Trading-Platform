@echo off
set "PYTHON_PATH=C:\Program Files\Python311\python.exe"
set "NODE_PATH=C:\Program Files\nodejs"
set "PATH=%NODE_PATH%;%PATH%"
@echo off
echo ========================================
echo   Trading Bot - Multi-Service Startup
echo ========================================

echo.
echo [1/3] Starting Golang Analysis Service (Port 8001)...
start "Golang Analysis API" cmd /k start_go.bat

timeout /t 5

echo.
echo [2/3] Starting Python API (Port 8000)...
start "Python API" cmd /k "cd Trading_Api && python -m uvicorn main:app --reload"

timeout /t 3

echo.
echo [3/3] Starting Frontend (Port 3000)...
start "Frontend" cmd /k "cd trading_web && npm.cmd run dev"

echo.
echo ========================================
echo   All services started!
echo   - Golang API: http://localhost:8001
echo   - Python API: http://localhost:8000
echo   - Frontend: http://localhost:3000
echo ========================================
pause
