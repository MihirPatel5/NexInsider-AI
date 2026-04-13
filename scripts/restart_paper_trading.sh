#!/bin/bash
# scripts/restart_paper_trading.sh - Restart paper trading with data saving

echo "=========================================="
echo "Restarting Paper Trading with Data Saving"
echo "=========================================="
echo ""

# Stop old processes
echo "1. Stopping old paper trading processes..."
pkill -f "start_live_trading.py"
sleep 2

# Verify stopped
if pgrep -f "start_live_trading.py" > /dev/null; then
    echo "⚠️  Some processes still running. Force killing..."
    pkill -9 -f "start_live_trading.py"
    sleep 1
fi

echo "✅ Old processes stopped"
echo ""

# Start new process with fixed code
echo "2. Starting paper trading with data saving..."
echo ""

venv/bin/python3 scripts/start_live_trading.py

echo ""
echo "=========================================="
echo "Paper Trading Stopped"
echo "=========================================="
