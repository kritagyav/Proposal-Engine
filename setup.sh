#!/bin/bash
# Proposal Engine — One-time setup script
# Run once: bash setup.sh

echo "========================================"
echo "Proposal Engine — Setup"
echo "========================================"

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup complete."
echo ""
echo "NEXT STEPS:"
echo "1. Add your Anthropic API key to .env"
echo "2. Run ingestion:  source venv/bin/activate && python ingest/run_ingestion.py"
echo "3. Launch app:     source venv/bin/activate && streamlit run app.py"
echo "========================================"
