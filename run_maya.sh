#!/bin/bash

# MayaMCP Development Runner
# This script sets up the environment and runs Maya

set -e

echo "🍹 Starting Maya - AI Bartending Agent 🍹"
echo "========================================="

# MayaMCP always starts in BYOK mode.
# Users provide API keys via the UI for maximum security and privacy.
echo "ℹ️  Maya is running in BYOK (Bring Your Own Key) mode."
echo "   Please have your Gemini API key ready."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed!"
    exit 1
fi

# Determine virtual environment directory (prefer .venv, fallback to venv)
VENV_DIR=""
if [ -d ".venv" ]; then
    VENV_DIR=".venv"
elif [ -d "venv" ]; then
    VENV_DIR="venv"
else
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
    VENV_DIR=".venv"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment ($VENV_DIR)..."
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# Install in editable mode so imports work without path hacks
echo "📥 Installing project in editable mode..."
python -m pip install --upgrade pip setuptools wheel >/dev/null
python -m pip install -e .

# Create assets directory if it doesn't exist
mkdir -p assets

# Run the application via console script (fallback to python main.py)
echo "🚀 Launching Maya..."
if command -v mayamcp &> /dev/null; then
    mayamcp
else
    python main.py
fi