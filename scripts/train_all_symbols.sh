#!/bin/bash
# Train models for all symbols

SYMBOLS=("NIFTY50" "BANKNIFTY" "RELIANCE" "TCS" "HDFCBANK" "INFY" "ICICIBANK")

echo "=================================="
echo "Training models for all symbols"
echo "=================================="
echo ""

for symbol in "${SYMBOLS[@]}"; do
    echo "Training $symbol..."
    venv/bin/python3 scripts/train_intraday_models.py --symbol "$symbol"
    
    if [ $? -eq 0 ]; then
        echo "✅ $symbol training complete"
    else
        echo "❌ $symbol training failed"
    fi
    echo ""
done

echo "=================================="
echo "All training complete!"
echo "=================================="
