#!/bin/bash
# setup.sh - One-command setup for Finance Research Agent

set -e  # Exit on error

echo "🚀 Finance Research Agent - Setup Script"
echo "========================================"
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version || { echo "❌ Python 3 not found. Please install Python 3.8+"; exit 1; }
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
fi
echo ""

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "✓ Installing dependencies..."
pip install -q -r requirements.txt
echo ""

# Show setup complete
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Set your API key (choose one):"
echo "   • OpenAI: export OPENAI_API_KEY='sk-...'"
echo "   • Grok: export OPENAI_API_KEY='grok_...' && export OPENAI_BASE_URL='https://api.x.ai/v1'"
echo ""
echo "2. Run a query:"
echo "   python main.py \"Should I invest in Apple?\""
echo ""
echo "3. Check output:"
echo "   ls output/  # See generated reports"
echo ""
echo "📖 For more help, see README.md or QUICKSTART.md"
