#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "  RIPE Atlas — LLM Routing Analytics"
echo "========================================"
echo ""
echo "What would you like to do?"
echo ""
echo "  Data collection:"
echo "  1) Collect US RIPE Atlas traceroutes"
echo "  2) Collect international RIPE Atlas traceroutes"
echo "  3) Collect local traceroutes (no RIPE account needed)"
echo ""
echo "  Analysis:"
echo "  4) Run pipeline  →  resolves IPs, computes analytics, exports JSON + HTML"
echo ""
echo "  Dashboard:"
echo "  5) Start React dashboard  (http://localhost:5173)"
echo "  6) Build dashboard for production"
echo ""
echo "  q) Quit"
echo ""
read -p "Select (1-6, or q): " choice
echo ""

activate_venv() {
    if [ ! -d "$ROOT/venv" ]; then
        echo "[*] Creating Python virtual environment..."
        python3 -m venv "$ROOT/venv"
    fi
    source "$ROOT/venv/bin/activate"
    pip install -r "$ROOT/requirements.txt" -q
}

check_env() {
    if [ ! -f "$ROOT/.env" ]; then
        echo "[!] .env not found."
        read -p "Enter your RIPE Atlas API Key: " api_key
        echo "RIPE_ATLAS_API_KEY=$api_key" > "$ROOT/.env"
        echo "[*] Saved to .env"
    fi
}

case $choice in
    1)
        activate_venv
        check_env
        python3 "$ROOT/pipeline/collect/RipeAtlasCollection.py"
        ;;
    2)
        activate_venv
        check_env
        python3 "$ROOT/pipeline/collect/InternationalCollection.py"
        ;;
    3)
        activate_venv
        python3 "$ROOT/pipeline/collect/LocalCollection.py"
        ;;
    4)
        activate_venv
        python3 "$ROOT/pipeline/run.py"
        echo ""
        echo "[*] Dashboard data  →  dashboard/public/data/"
        echo "[*] Standalone HTML →  outputs/html/"
        ;;
    5)
        if [ ! -d "$ROOT/dashboard/node_modules" ]; then
            echo "[*] Installing dashboard dependencies..."
            cd "$ROOT/dashboard" && npm install
        fi
        echo "[*] Starting dashboard at http://localhost:5173 ..."
        cd "$ROOT/dashboard" && npm run dev
        ;;
    6)
        if [ ! -d "$ROOT/dashboard/node_modules" ]; then
            echo "[*] Installing dashboard dependencies..."
            cd "$ROOT/dashboard" && npm install
        fi
        cd "$ROOT/dashboard" && npm run build
        echo "[*] Production build  →  dashboard/dist/"
        ;;
    q|Q)
        echo "Bye."
        exit 0
        ;;
    *)
        echo "[!] Invalid option."
        exit 1
        ;;
esac

echo ""
echo "[*] Done."
