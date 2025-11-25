#!/bin/bash

# NesHedgeFund - MacOS Startup Script
# Uses Yahoo Finance as data source

echo "🚀 Starting NesHedgeFund (MacOS - Yahoo Finance)..."

# Set environment
export DATA_SOURCE=YAHOO

# Start API Server
echo "📡 Starting API Server..."
cd "$(dirname "$0")/trading_api"
python3 run.py &
API_PID=$!

# Wait for API to start
sleep 10

# Start Frontend
echo "🌐 Starting Frontend..."
cd ../trading_web
npm run dev &
WEB_PID=$!

echo ""
echo "✅ NesHedgeFund is running!"
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API: http://localhost:8000"
echo "📈 Data Source: Yahoo Finance"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait
