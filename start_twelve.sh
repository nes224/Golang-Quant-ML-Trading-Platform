#!/bin/bash

# NesHedgeFund - Twelve Data Startup Script
# Uses Twelve Data API as data source

echo "🚀 Starting NesHedgeFund (Twelve Data API)..."

# Set environment
export DATA_SOURCE=TWELVE

# Start API Server
echo "📡 Starting API Server..."
cd "$(dirname "$0")/trading_api"
python3 run.py &
API_PID=$!

# Wait for API to start
sleep 3

# Start Frontend
echo "🌐 Starting Frontend..."
cd ../trading_web
npm run dev &
WEB_PID=$!

echo ""
echo "✅ NesHedgeFund is running!"
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API: http://localhost:8000"
echo "📈 Data Source: Twelve Data API"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait
