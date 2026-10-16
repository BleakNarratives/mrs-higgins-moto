#!/usr/bin/env bash
# Author: BleakNarratives
# Filename: setup.sh
# Run this from Termux to get the whole pipeline scaffolded and LNbits running.

set -euo pipefail

PROJECT_DIR="/storage/ED7B-AD5A/root_2026/moto-2024-sd-r26"
LNBITS_PORT=5000
LNBITS_LOG="$HOME/lnbits.log"
CONFIG="$PROJECT_DIR/front_desk_config.json"

echo ""
echo "════════════════════════════════════════"
echo "  Mrs. Higgins Setup — Vertical AI"
echo "════════════════════════════════════════"

# ── 1. Directory structure ────────────────
echo ""
echo "[1/5] Scaffolding project directories..."
mkdir -p "$PROJECT_DIR"/{saas_packages,copy_output,logs}
echo "  ✓ $PROJECT_DIR"
echo "  ✓ saas_packages/ copy_output/ logs/"

# ── 2. Python deps ────────────────────────
echo ""
echo "[2/5] Checking Python..."
python3 -c "import json,os,sys,argparse,urllib" && echo "  ✓ stdlib OK" || echo "  ✗ Python issue"

# ── 3. LNbits ─────────────────────────────
echo ""
echo "[3/5] LNbits..."

if ! pip show lnbits > /dev/null 2>&1; then
  echo "  Installing LNbits (this may take a minute)..."
  pip install lnbits --quiet --break-system-packages 2>&1 | tail -5
else
  echo "  ✓ LNbits already installed"
fi

# Kill any stuck instance
pkill -f "lnbits" 2>/dev/null && echo "  ↺ Restarting LNbits..." || true

# Start LNbits in background
nohup lnbits --port $LNBITS_PORT > "$LNBITS_LOG" 2>&1 &
LNBITS_PID=$!
echo "  ✓ LNbits starting (PID $LNBITS_PID) → $LNBITS_LOG"
echo "  Waiting for it to come up..."
sleep 6

# Check it
if curl -s "http://localhost:$LNBITS_PORT/api/v1/health" > /dev/null 2>&1; then
  echo "  ✓ LNbits is UP at http://localhost:$LNBITS_PORT"
else
  echo "  ⚠ LNbits may still be starting. Check: curl http://localhost:$LNBITS_PORT"
  echo "    Logs: tail -f $LNBITS_LOG"
fi

# ── 4. Config template ────────────────────
echo ""
echo "[4/5] Config..."

if [ -f "$CONFIG" ]; then
  echo "  ✓ front_desk_config.json already exists — not overwriting"
else
  cat > "$CONFIG" << 'EOF'
{
  "lightning_account_id": "bleaknarratives@speed.app",
  "lnbits_url": "http://localhost:5000",
  "lnbits_invoice_key": "PASTE_YOUR_INVOICE_KEY_HERE"
}
EOF
  echo "  ✓ Config template written to $CONFIG"
fi

# ── 5. Ollama ─────────────────────────────
echo ""
echo "[5/5] Ollama..."
if pgrep -x ollama > /dev/null; then
  echo "  ✓ Ollama already running"
else
  echo "  Starting Ollama..."
  nohup ollama serve > "$HOME/ollama.log" 2>&1 &
  sleep 3
  echo "  ✓ Ollama started"
fi

# ── Done ──────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "  DONE. Next steps:"
echo ""
echo "  1. Open browser → http://localhost:$LNBITS_PORT"
echo "  2. Create a wallet, go to API Info"
echo "  3. Copy the Invoice/read key"
echo "  4. Paste it into:"
echo "     $CONFIG"
echo ""
echo "  Then run: python briefing.py"
echo "════════════════════════════════════════"
echo ""
