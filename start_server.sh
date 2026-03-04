#!/bin/bash
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║      FreePlayZone — Starting Server      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found!"
    echo "Install it: https://www.python.org/downloads/"
    exit 1
fi

echo "[OK] Python3 found"
echo ""
echo "Installing dependencies..."
pip3 install flask flask-cors werkzeug --quiet

echo "[OK] Dependencies ready"
echo ""
echo "══════════════════════════════════════════════"
echo "Server running at: http://localhost:5000"
echo "Admin login:       pgnr_58 / admin123"
echo "Press CTRL+C to stop"
echo "══════════════════════════════════════════════"
echo ""

# Open browser
sleep 2 && open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null &

python3 server.py
