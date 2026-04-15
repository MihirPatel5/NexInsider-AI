#!/bin/bash
# Check if live trading is running and restart if needed

echo "================================"
echo "Live Trading Health Check"
echo "================================"
echo "Time: $(date)"
echo ""

# Check if process is running
if pgrep -f "start_live_trading" > /dev/null; then
    echo "✅ Live trading is running"
    echo ""
    echo "Process info:"
    ps aux | grep start_live_trading | grep -v grep
else
    echo "⚠️  Live trading is NOT running"
    echo ""
    echo "Checking database for recent data..."
    
    # Check if data was saved recently (last 5 minutes)
    RECENT_DATA=$(PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -t -c "
        SELECT COUNT(*) 
        FROM ohlcv_intraday 
        WHERE time >= NOW() - INTERVAL '5 minutes'
    " 2>/dev/null)
    
    if [ ! -z "$RECENT_DATA" ] && [ "$RECENT_DATA" -gt 0 ]; then
        echo "✅ Found $RECENT_DATA candles in last 5 minutes"
    else
        echo "⚠️  No recent data found"
    fi
    
    echo ""
    echo "Would you like to restart? (y/n)"
    read -r response
    
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        echo ""
        echo "Starting live trading with robust script..."
        cd /home/ts/MIG/prod-grade
        source venv/bin/activate
        python3 scripts/start_live_trading_robust.py
    fi
fi

echo ""
echo "================================"
