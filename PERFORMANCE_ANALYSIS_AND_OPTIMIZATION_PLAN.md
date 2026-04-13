# Performance Analysis & Optimization Plan

**Date:** April 10, 2026  
**Current Status:** System Working, Needs Optimization  

---

## Current Performance (60 Days Backtest)

### Portfolio Metrics
```
Initial Value:        ₹100,000.00
Final Value:          ₹121,303.07
Total Return:         +21.30%
Sharpe Ratio:         0.351
Max Drawdown:         4.43%
```

### Trading Activity
```
Total Trades:         22
Trading Days:         60
Trades/Day:           0.37 (0.4 rounded)
Won Trades:           15
Lost Trades:          7
Win Rate:             68.2%
Avg Profit/Trade:     0.968%
```

### Target Achievement
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Trades/Day | ≥ 5 | 0.37 | ❌ |
| Win Rate | ≥ 50% | 68.2% | ✅ |
| Max Drawdown | ≤ 2% | 4.43% | ❌ |
| Total Return | > 0% | 21.30% | ✅ |

**TARGETS MET: 2/4** ⚠️ PARTIAL SUCCESS

---

## Comparison: Previous vs Current

| Metric | Previous (Feb) | Current (Apr) | Change |
|--------|---------------|---------------|--------|
| **Return** | 12.58% | 21.30% | +69% ✅ |
| **Trades** | 34 | 22 | -35% ⚠️ |
| **Trades/Day** | 0.57 | 0.37 | -35% ⚠️ |
| **Win Rate** | 52.9% | 68.2% | +29% ✅ |
| **Sharpe** | 0.204 | 0.351 | +72% ✅ |
| **Drawdown** | 6.47% | 4.43% | -32% ✅ |

### Analysis
- **Returns IMPROVED** significantly (+69%)
- **Win Rate IMPROVED** dramatically (+29%)
- **Sharpe Ratio IMPROVED** (+72%)
- **Drawdown IMPROVED** (-32%)
- **Trade Frequency DECREASED** (-35%) ⚠️

**Conclusion:** Strategy quality improved but trade frequency dropped!

---

## Root Cause Analysis

### Why Only 22 Trades in 60 Days?

**Current Configuration:**
```python
ml_confidence_threshold = 0.35  # From config
```

**The Problem:**
1. Models are TOO selective (confidence threshold 0.35)
2. Only trades when BOTH models agree strongly
3. Results in high win rate (68.2%) but few trades (0.37/day)
4. Need 5-15 trades/day for intraday system

**The Trade-off:**
```
High Threshold (0.35) → Few Trades (0.37/day) + High Win Rate (68.2%)
Low Threshold (0.25)  → More Trades (2-5/day) + Good Win Rate (55-65%)
```

For intraday trading, we need MORE TRADES even if win rate drops slightly.

---

## Optimization Strategy

### Phase 1: Lower Confidence Threshold (IMMEDIATE)

**Change:**
```yaml
# config/live_trading_config.yaml
strategy:
  ml_confidence_threshold: 0.25  # Down from 0.35
```

**Expected Results:**
- Trades/day: 1-3 (vs 0.37 currently)
- Win rate: 55-65% (vs 68.2% currently)
- Still profitable with more volume
- Better daily consistency

**Time:** 2 minutes to change + 5 minutes to re-run backtest

---

### Phase 2: Adjust Position Sizing (QUICK WIN)

**Current:**
```yaml
max_position_pct: 0.30  # 30% of capital per trade
```

**Problem:** With ₹100,000 capital and Nifty at ₹42,000:
- 30% = ₹30,000
- Can only buy 0.7 shares (rounds to 1)
- Limited position sizing flexibility

**Solution:** Increase capital or adjust position size
```yaml
max_position_pct: 0.50  # 50% of capital per trade
```

**Expected:** More aggressive trading, higher returns

---

### Phase 3: Optimize Risk Parameters

**Current Settings:**
```yaml
stop_loss_pct: 0.008      # 0.8%
take_profit_pct: 0.015    # 1.5%
trailing_stop_pct: 0.005  # 0.5%
```

**Analysis from Trades:**
- Average profit per trade: 0.968%
- Take profit at 1.5% is good
- Stop loss at 0.8% is tight (good for risk)
- Trailing stop at 0.5% might be too tight

**Optimization Options:**

**Option A: Widen Trailing Stop**
```yaml
trailing_stop_pct: 0.008  # 0.8% (from 0.5%)
```
- Let winners run longer
- Reduce premature exits
- May improve avg profit/trade

**Option B: Adjust Stop Loss**
```yaml
stop_loss_pct: 0.010  # 1.0% (from 0.8%)
```
- Give trades more room
- Reduce false stops
- May improve win rate

**Option C: Adjust Take Profit**
```yaml
take_profit_pct: 0.020  # 2.0% (from 1.5%)
```
- Capture bigger moves
- May reduce win rate but increase avg profit

---

### Phase 4: Retrain Models with More Data

**Current Training:**
- 4,500 candles (60 days)
- 27 features
- 61-62% accuracy

**Improvement Options:**

**Option A: Get More Historical Data**
- Fetch 6-12 months of 5-minute data
- More training samples
- Better pattern recognition

**Option B: Feature Engineering**
- Add volume-based indicators
- Add market regime indicators
- Add time-of-day features

**Option C: Ensemble Methods**
- Add more models (LightGBM, CatBoost)
- Weighted voting
- May improve accuracy to 65-70%

---

### Phase 5: Add More Trading Signals

**Current:** Only ML-based signals

**Additional Signals to Consider:**

**1. Volume Breakouts**
```python
if volume > avg_volume * 2 and price_change > 0.5%:
    # High volume breakout signal
    confidence += 0.1
```

**2. Support/Resistance Levels**
```python
if price near support and ML says BUY:
    # Confluence signal
    confidence += 0.15
```

**3. Market Regime Filter**
```python
if market_regime == "trending" and ML confidence > 0.25:
    # Trade in trending markets only
    execute_trade()
```

**Expected:** More high-quality signals, better trade frequency

---

## Recommended Action Plan

### Immediate Actions (Today - 30 minutes)

**1. Lower Confidence Threshold** ⭐ HIGHEST PRIORITY
```bash
# Edit config/live_trading_config.yaml
ml_confidence_threshold: 0.25  # From 0.35

# Re-run backtest
venv/bin/python3 scripts/backtest_intraday.py
```

**Expected Impact:**
- Trades/day: 1-3 (3x improvement)
- Win rate: 55-65% (still good)
- Return: 15-30% (maintain or improve)

**2. Adjust Position Sizing**
```yaml
max_position_pct: 0.40  # From 0.30
```

**Expected Impact:**
- More aggressive trading
- Higher returns per trade
- Slightly higher risk

---

### Short-term Actions (This Week - 2-3 hours)

**3. Optimize Risk Parameters**
- Test different stop loss values (0.8%, 1.0%, 1.2%)
- Test different trailing stop values (0.5%, 0.8%, 1.0%)
- Find optimal balance

**4. Add Volume Filter**
```python
# Only trade when volume > average
if current_volume > avg_volume_20:
    # Higher quality signal
    proceed_with_trade()
```

**5. Paper Trade with Real Data**
- Run live system for 1 week
- Monitor actual performance
- Compare with backtest

---

### Medium-term Actions (Next 2 Weeks - 5-10 hours)

**6. Retrain Models with More Data**
- Fetch 6 months of historical data
- Retrain XGBoost and Random Forest
- Target 65-70% accuracy

**7. Add More Features**
- Volume indicators (OBV, VWAP)
- Market regime indicators
- Time-of-day features

**8. Implement Ensemble**
- Add LightGBM model
- Weighted voting (XGB 40%, RF 30%, LGB 30%)
- May improve accuracy

**9. Add Support/Resistance Detection**
- Identify key price levels
- Use as confluence signals
- Improve entry/exit timing

---

### Long-term Actions (Next Month - 10-20 hours)

**10. Walk-Forward Optimization**
- Test on rolling windows
- Validate robustness
- Ensure no overfitting

**11. Multi-Symbol Trading**
- Add Bank Nifty
- Add top 5 Nifty stocks
- Diversify risk

**12. Advanced Risk Management**
- Portfolio-level stops
- Correlation analysis
- Position sizing based on volatility

---

## Expected Performance After Optimization

### Conservative Estimate (After Phase 1 & 2)
```
Return:               20-30% (60 days)
Trades/Day:           1-3
Win Rate:             55-65%
Sharpe Ratio:         0.4-0.6
Max Drawdown:         3-5%
```

### Optimistic Estimate (After All Phases)
```
Return:               30-50% (60 days)
Trades/Day:           3-8
Win Rate:             60-70%
Sharpe Ratio:         0.8-1.2
Max Drawdown:         2-4%
```

---

## Risk Assessment

### Current Risks
1. **Low Trade Frequency** - Only 0.37 trades/day
2. **High Drawdown** - 4.43% vs target 2%
3. **Model Overfitting** - Trained on limited data
4. **Single Symbol** - No diversification

### Mitigation Strategies
1. **Lower threshold** - Increase trade frequency
2. **Tighter stops** - Reduce drawdown
3. **More data** - Reduce overfitting
4. **Multi-symbol** - Diversify risk

---

## Success Metrics

### Phase 1 Success (After Threshold Adjustment)
- ✅ Trades/day > 1.0
- ✅ Win rate > 55%
- ✅ Return > 15%
- ✅ Sharpe > 0.3

### Phase 2 Success (After Risk Optimization)
- ✅ Trades/day > 2.0
- ✅ Win rate > 60%
- ✅ Return > 20%
- ✅ Sharpe > 0.5
- ✅ Drawdown < 4%

### Final Success (After All Optimizations)
- ✅ Trades/day > 3.0
- ✅ Win rate > 60%
- ✅ Return > 30%
- ✅ Sharpe > 0.8
- ✅ Drawdown < 3%

---

## Next Steps

### RIGHT NOW (5 minutes)
```bash
# 1. Edit config
nano config/live_trading_config.yaml
# Change ml_confidence_threshold from 0.35 to 0.25

# 2. Re-run backtest
venv/bin/python3 scripts/backtest_intraday.py

# 3. Compare results
cat INTRADAY_BACKTEST_RESULTS.csv
```

### TODAY (30 minutes)
1. Lower confidence threshold to 0.25
2. Adjust position sizing to 0.40
3. Re-run backtest
4. Analyze new results
5. If good, deploy to paper trading

### THIS WEEK (2-3 hours)
1. Optimize risk parameters
2. Add volume filter
3. Paper trade for 1 week
4. Monitor and adjust

### NEXT 2 WEEKS (5-10 hours)
1. Retrain models with more data
2. Add more features
3. Implement ensemble
4. Add support/resistance

---

## Conclusion

**Current State:**
- ✅ System is profitable (21.30% return)
- ✅ High win rate (68.2%)
- ✅ Good Sharpe ratio (0.351)
- ⚠️ Low trade frequency (0.37/day)
- ⚠️ High drawdown (4.43%)

**The Problem:**
Models are TOO selective. We're missing profitable opportunities.

**The Solution:**
Lower confidence threshold from 0.35 to 0.25 to generate more trades while maintaining profitability.

**Expected Outcome:**
- 3x more trades (1-3/day vs 0.37/day)
- Still profitable (55-65% win rate)
- Better daily consistency
- Path to 5-15 trades/day target

**Action Required:**
Change ONE line in config and re-run backtest. Takes 5 minutes.

---

**Status:** Ready for Optimization ✅  
**Priority:** HIGH - Low trade frequency limiting profits  
**Time to Fix:** 5 minutes  
**Expected Impact:** 3x more trades, maintain profitability  

**LET'S DO IT!** 🚀
