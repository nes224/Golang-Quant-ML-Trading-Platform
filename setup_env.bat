@echo off
echo Setting up environment...

echo Installing Python dependencies...
cd Trading_Api
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install Python dependencies.
    exit /b %errorlevel%
)
cd ..

echo Installing Node.js dependencies...
cd trading_web
call npm install
if %errorlevel% neq 0 (
    echo Failed to install Node.js dependencies.
    exit /b %errorlevel%
)
cd ..

echo Environment setup complete!
pause
