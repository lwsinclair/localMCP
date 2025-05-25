#!/bin/bash

# Universal MCP Host - React + FastAPI Version with Live Logs
# This script starts both services and shows logs in real-time

echo "🤖 Starting Universal MCP Host with Live Logs"
echo "=============================================="

# Check dependencies
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Setup frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# Setup backend
echo "🐍 Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r ../requirements.txt
cd ..

# Cleanup function
cleanup() {
    echo -e "\n🛑 Stopping all services..."
    pkill -f "python.*main.py" 2>/dev/null
    pkill -f "npm start" 2>/dev/null
    pkill -f "react-scripts start" 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "\n🚀 Starting services..."

# Start backend in background
cd backend
source venv/bin/activate
echo "📡 Backend starting on port 8000..."
python main.py 2>&1 | sed 's/^/[BACKEND] /' &
BACKEND_PID=$!
cd ..

# Wait for backend
sleep 3

# Start frontend in background  
cd frontend
echo "⚛️  Frontend starting on port 3000..."
npm start 2>&1 | sed 's/^/[FRONTEND] /' &
FRONTEND_PID=$!
cd ..

echo -e "\n✅ Services started!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔗 Backend: http://localhost:8000"
echo -e "\n📋 Live logs (Press Ctrl+C to stop):"
echo "====================================="

# Wait for services
wait
