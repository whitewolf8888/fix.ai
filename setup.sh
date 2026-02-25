#!/bin/bash
# VulnSentinel Quick Start Script

echo "=================================="
echo "   VulnSentinel Quick Start"
echo "=================================="
echo ""

# Backend
echo "1️⃣  Setting up Backend..."
cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing backend dependencies..."
pip install -q -r requirements.txt
pip install -q semgrep

# Check .env
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env with your API keys before running!"
fi

echo "✓ Backend setup complete"
echo ""

# Frontend
echo "2️⃣  Setting up Frontend..."
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (this may take a minute)..."
    npm install
else
    echo "✓ Dependencies already installed"
fi

echo "✓ Frontend setup complete"
echo ""

# Instructions
echo "=================================="
echo "   Setup Complete! 🎉"
echo "=================================="
echo ""
echo "To start the application:"
echo ""
echo "Terminal 1 (Backend):"
echo "  cd /workspaces/fix.ai/backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Terminal 2 (Frontend):"
echo "  cd /workspaces/fix.ai/frontend"
echo "  npm run dev"
echo ""
echo "Then visit: http://localhost:3000"
echo ""
echo "Don't forget to configure your .env files!"
echo "=================================="
