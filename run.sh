#!/bin/bash
# ─────────────────────────────────────────
#  Kaadu Dashboard — Quick Start Script
# ─────────────────────────────────────────
echo "🌿 Kaadu Organic Sales Dashboard"
echo "================================="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Install deps if needed
if ! python3 -c "import flask" &>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo "🚀 Starting server at http://localhost:5000"
echo "   Default login: admin / kaadu@2024"
echo ""

python3 app.py
