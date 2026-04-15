# CRITICAL ISSUE: Model Training Data Mismatch

## Problem Identified

**CRITICAL MISMATCH**: Models trained on DAILY data but need to work on INTRADAY (5-minute) data.

### Current State
- **Training data**: Daily candles (1d interval)
- **Prediction horizon**: 5-day forward returns
- **Trade frequency**: 4.4 trades/YEAR
- **Use case**: Intraday trading (need 5-15 trades/DAY)

### Why This Doesn't Work

1. **Time Scale Mismatch**
   - Daily models predict multi-day moves
   - Intraday needs minute-to-minute predictions
   - Features calculated on daily data don't capture intraday patterns

2. **Signal Frequency**
   - Daily: 1 signal per day maximum
   - Intraday: Need signals every 5 minutes
   - Current: 4.4 trades/year = 0.018 trades/day ❌

3. **Market Dynamics**
   - Daily: Captures overnight gaps, daily trends
   - Intraday: Captures intraday volatility, momentum, mean reversion
   - Different patterns, different features needed

## The Solution

### RETRAIN MODELS ON 5-MINUTE INTRADAY DATA

You already have:
- **66,412 candles** of 5-minute data
- **6 months** of intraday history
- **7 symbols** ready to use

### What Needs to Change

1. **Training Data**: Use `ohlcv_intraday` table (5-minute candles)
2. **Prediction Horizon**: Predict next 15-30 minute moves (not 5 days)
3. **Features**: Calculate on 5-minute timeframe
4. **Labels**: 
   - BUY: If price up >0.3% in next 6 candles (30 min)
   - SELL: If price down >0.3% in next 6 candles
   - HOLD: Otherwise

### Expected Results After Retraining

- **Trade frequency**: 5-15 trades/day ✅
- **Prediction frequency**: Every 5 minutes
- **Suitable for**: Intraday scalping/momentum trading

## Action Required

1. Create `scripts/train_intraday_models.py` - Train on 5-min data
2. Update prediction horizon to 15-30 minutes
3. Adjust features for intraday timeframe
4. Retrain XGBoost and Random Forest
5. Backtest on 5-minute data
6. Deploy to live intraday strategy

## Timeline

- Training: 5-10 minutes
- Backtesting: 10-15 minutes
- Total: 20-30 minutes to production-ready intraday models

---

**BOTTOM LINE**: The current models are CORRECT for daily trading but WRONG for intraday. Need to retrain on 5-minute data immediately.
