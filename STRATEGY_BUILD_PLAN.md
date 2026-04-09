# Strategy Building Plan - EXECUTION MODE

**Date:** April 9, 2026  
**Status:** 🚀 STARTING NOW  
**Goal:** Achieve Sharpe > 1.0 with existing daily data

---

## What We Have (READY)

✅ **Data:** 6 years daily (2020-2026), 3 symbols  
✅ **Features:** 27 technical indicators  
✅ **Infrastructure:** Complete and tested  
✅ **Corporate Actions:** Applied and verified  

---

## What I'll Build (3-4 hours)

### Phase 1: Rule-Based Strategies (1 hour)

**1.1 Trend Following Strategy**
- Entry: Price > SMA(50) AND RSI < 70 AND MACD > 0 AND ADX > 25
- Exit: Price < SMA(50) OR RSI > 80 OR MACD < 0
- Stop Loss: 7%
- Take Profit: 12%

**1.2 Mean Reversion Strategy**
- Entry: RSI < 30 AND Price touches lower Bollinger Band
- Exit: RSI > 70 AND Price touches upper Bollinger Band
- Stop Loss: 5%
- Take Profit: 10%

**1.3 Momentum Strategy**
- Entry: ADX > 25 AND +DI > -DI AND ROC > 0
- Exit: ADX < 20 OR +DI < -DI
- Trailing Stop: 5%

### Phase 2: ML Models (2 hours)

**2.1 XGBoost Classifier**
- Features: All 27 technical indicators
- Target: Future 5-day return (BUY/SELL/HOLD)
- Training: 80% data, Test: 20%
- Hyperparameters: max_depth=5, n_estimators=100

**2.2 Random Forest Classifier**
- Features: All 27 technical indicators
- Target: Future 5-day return (BUY/SELL/HOLD)
- Training: 80% data, Test: 20%
- Hyperparameters: n_estimators=100, max_depth=10

### Phase 3: Hybrid Strategy (1 hour)

**3.1 Ensemble Approach**
- Combine rule-based + ML predictions
- Weight: 40% rule-based, 60% ML
- Only trade when both agree (high confidence)
- Use regime detection for dynamic weighting

**3.2 Parameter Optimization**
- Tune confidence thresholds
- Optimize stop-loss/take-profit
- Test on different time periods

---

## Implementation Steps

### Step 1: Create Rule-Based Strategies (30 min)
- [ ] Implement TrendFollowingStrategy class
- [ ] Implement MeanReversionStrategy class
- [ ] Implement MomentumStrategy class
- [ ] Test each strategy individually

### Step 2: Train ML Models (1.5 hours)
- [ ] Prepare training data with 27 features
- [ ] Create labels (future returns)
- [ ] Train XGBoost model
- [ ] Train Random Forest model
- [ ] Save models to MLflow
- [ ] Validate on test set

### Step 3: Build Hybrid Strategy (30 min)
- [ ] Create HybridStrategy class
- [ ] Combine rule-based + ML signals
- [ ] Implement confidence scoring
- [ ] Add regime-aware weighting

### Step 4: Comprehensive Backtesting (30 min)
- [ ] Run backtests on all 3 symbols
- [ ] Test on 2024-2026 period
- [ ] Generate performance reports
- [ ] Compare strategies

---

## Expected Timeline

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Rule-Based Strategies | 1 hour | 🔄 Starting |
| 2 | ML Model Training | 2 hours | ⏳ Queued |
| 3 | Hybrid Strategy | 1 hour | ⏳ Queued |
| 4 | Backtesting | 30 min | ⏳ Queued |
| **Total** | | **4.5 hours** | |

---

## Success Criteria

✅ **Sharpe Ratio:** > 1.0  
✅ **Win Rate:** > 50%  
✅ **Trades/Year:** > 20  
✅ **Max Drawdown:** < 20%  

---

## Let's Go! 🚀

Starting with Phase 1: Rule-Based Strategies...
