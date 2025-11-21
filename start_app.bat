@echo off
set "PYTHON_PATH=C:\Program Files\Python311\python.exe"
set "NODE_PATH=C:\Program Files\nodejs"
set "PATH=%NODE_PATH%;%PATH%"

echo Starting Backend...
cd Trading_Api
start "Trading Bot Backend" "%PYTHON_PATH%" -m uvicorn main:app --reload
cd ..

echo Starting Frontend...
cd trading_web
start "Trading Bot Frontend" "%NODE_PATH%\npm.cmd" run dev
cd ..

echo Application started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
pause
