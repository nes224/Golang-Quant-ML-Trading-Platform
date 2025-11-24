#!/bin/bash

# NesHedgeFund - MacOS Stop Script

echo "🛑 Stopping NesHedgeFund..."

# Kill processes on ports 8000 and 3000
echo "Stopping API Server (port 8000)..."
lsof -ti:8000 | xargs kill -9 2>/dev/null

echo "Stopping Frontend (port 3000)..."
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Also kill by process name as backup
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "next dev" 2>/dev/null

echo "✅ All services stopped!"
