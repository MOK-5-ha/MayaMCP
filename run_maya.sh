#!/bin/bash

# MayaMCP Development Runner
# This script sets up the environment and runs Maya

set -e

echo "🍹 Starting Maya - AI Bartending Agent 🍹"
echo "========================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your API keys:"
    echo "GEMINI_API_KEY=your_google_api_key"
    echo "CARTESIA_API_KEY=your_cartesia_api_key"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed!"
    exit 1
fi

# Check if virtual environment should be created
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create assets directory if it doesn't exist
mkdir -p assets

# Run the application
echo "🚀 Launching Maya..."
python main.py