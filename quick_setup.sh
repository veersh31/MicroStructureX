#!/bin/bash
# Quick setup script for MicroStructureX

set -e  # Exit on error

echo "============================================================"
echo "  MicroStructureX - Quick Setup Script"
echo "============================================================"
echo ""

# Check Python version
echo "1️⃣  Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }
echo "✅ Python found"
echo ""

# Activate virtual environment if exists, create if not
echo "2️⃣  Setting up virtual environment..."
if [ -d "venv" ]; then
    echo "✅ Virtual environment already exists"
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created"
fi
echo ""

# Upgrade pip
echo "3️⃣  Upgrading pip..."
pip install --quiet --upgrade pip
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "4️⃣  Installing dependencies..."
echo "   (This may take 2-5 minutes...)"
pip install --quiet -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Verify installation
echo "5️⃣  Verifying installation..."
python -c "from src.engine.order_book import LimitOrderBook; print('✅ Core engine imported successfully')"
echo ""

# Run a quick test
echo "6️⃣  Running quick test..."
pytest tests/test_order_book.py::TestOrderBook::test_add_limit_order_no_match -v --tb=short
echo ""

echo "============================================================"
echo "  ✅ Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run a demo:"
echo "     python scripts/demo_basic_matching.py"
echo ""
echo "  3. Run all demos:"
echo "     python scripts/run_all_demos.py"
echo ""
echo "  4. Run tests:"
echo "     pytest tests/ -v"
echo ""
echo "  5. Start Jupyter:"
echo "     jupyter lab"
echo ""
echo "For detailed instructions, see: SETUP_AND_RUN.md"
echo ""
