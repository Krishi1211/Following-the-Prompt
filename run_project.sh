#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  AI Routing Infrastructure Project Setup "
echo "=========================================="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 could not be found. Please install Python 3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "[*] Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "[*] Installing dependencies..."
pip install -r requirements.txt -q

# Setup .env if missing
if [ ! -f ".env" ]; then
    echo ""
    echo "[!] .env file not found. We need your RIPE Atlas API Key."
    read -p "Please enter your RIPE Atlas API Key: " api_key
    echo "RIPE_ATLAS_API_KEY=$api_key" > .env
    echo "[*] Saved API Key to .env"
fi

echo ""
echo "=========================================="
echo " Environment is ready!"
echo "=========================================="
echo ""
echo "What would you like to run?"
echo "1) Collect new global RIPE Atlas data"
echo "2) Collect local top-sites data"
echo "3) Enrich RIPE data with CAIDA ASN mappings"
echo "4) Analyze current dataset"
echo "5) Generate traceroute graphs"
echo "q) Quit"

read -p "Select an option (1-5, or q): " choice
echo ""

case $choice in
    1) python scripts/ripe_atlas_collection.py ;;
    2) python scripts/collect_top_sites.py ;;
    3) python scripts/enrich_ripe_data.py ;;
    4) python scripts/analyze_ripe_data.py ;;
    5) python scripts/generate_traceroute_graph.py ;;
    q|Q) echo "Exiting..."; exit 0 ;;
    *) echo "Invalid option." ;;
esac

echo ""
echo "[*] Done. To deactivate the environment, type 'deactivate'."
