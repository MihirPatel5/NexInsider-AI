# Phase 3: Strategy Optimization Plan

**Date:** April 9, 2026  
**Status:** IN PROGRESS  
**Priority:** CRITICAL

---

## Objective

Improve ML trading strategy performance from current underperforming state to meet Phase 3 targets before proceeding to Phase 4 (Paper Trading).

---

## Current Performance Baseline

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Sharpe Ratio | -1.49 | >1.0 | -2.49 |
| Total Return | -0.35% | >5% annually | -5.35% |
| Win Rate | 36.7% | >50% | -13.3% |
| Max Drawdown | 1.41% | <20% | ✅ PASS |
| Total Trades | 17 (2 years) | N/A | Too low |

---

## Multi-Phase Optimization Strategy

### Phase A: Parameter Tuning (IMMEDIATE - Day 1)
**Goal:** Quick wins through parameter optimization  
**Timeline:** 4-6 hours  
**Risk:** Low

**Changes:**
1. **Confidence Threshold:** 0.65 → 0.55 (allow more trades)
2. **Stop Loss:** 5% → 7% (give trades room to breathe)
3. **Take Profit:** 10% → 12% (capture larger moves)
4. **Trailing Stop:** 3% → 4% (protect profits better)
5. **Position Sizing:** Test 10% → 15% of portfolio

**Expected Impact:**
- More trades (17 → 30-40 trades)
- Higher win rate (36.7% → 45-50%)
- Better risk-adjusted returns

---

### Phase B: Regime Weight Optimization (Day 1-2)
**Goal:** Tune ensemble weights for NSE market characteristics  
**Timeline:** 6-8 hours  
**Risk:** Low

**Changes:**
1. **Analyze regime distribution** in backtest period
2. **Test different weight combinations** per regime
3. **Implement adaptive weights** based on recent performance
4. **Add regime transition smoothing** to reduce whipsaw

**Expected Impact:**
- Better regime-specific performance
- Reduced false signals during regime transitions
- Improved confidence scores

---

### Phase C: Feature Engineering Enhancement (Day 2-3)
**Goal:** Improve ML model inputs for better predictions  
**Timeline:** 8-12 hours  
**Risk:** Medium

**Changes:**
1. **Add volume-based features:**
   - Volume momentum
   - Volume-price divergence
   - On-balance volume (OBV)
   
2. **Add volatility features:**
   - ATR (Average True Range)
   - Bollinger Band width
   - Historical volatility

3. **Add momentum features:**
   - RSI (Relative Strength Index)
   - MACD
   - Rate of change

4. **Add market microstructure:**
   - Bid-ask spread proxy
   - Price impact estimation

**Expected Impact:**
- Higher quality ML predictions
- Better confidence scores
- More accurate entry/exit timing

---

### Phase D: Walk-Forward Optimization (Day 3-4)
**Goal:** Implement proper model retraining during backtest  
**Timeline:** 8-10 hours  
**Risk:** Medium

**Changes:**
1. **Enable walk-forward validation** with model retraining
2. **Use rolling 6-month training windows**
3. **Test on 3-month forward periods**
4. **Track per-window performance**

**Expected Impact:**
- Models adapt to changing market conditions
- Reduced overfitting
- More realistic performance estimates

---

### Phase E: Additional Data Collection (Day 4-5)
**Goal:** Expand training dataset for better model generalization  
**Timeline:** 6-8 hours  
**Risk:** Low

**Changes:**
1. **Download 5+ years of historical data** for all symbols
2. **Load data into database**
3. **Retrain models** with expanded dataset
4. **Re-run backtests** on longer period

**Expected Impact:**
- Better model generalization
- More robust predictions
- Validation across multiple market cycles

---

### Phase F: Risk Management Refinement (Day 5)
**Goal:** Optimize risk parameters for better risk-adjusted returns  
**Timeline:** 4-6 hours  
**Risk:** Low

**Changes:**
1. **Dynamic position sizing** based on volatility
2. **Correlation-based position limits** (avoid overexposure)
3. **Time-based stops** (exit stale positions)
4. **Profit target scaling** based on regime

**Expected Impact:**
- Better capital utilization
- Reduced correlation risk
- Improved Sharpe ratio

---

## Implementation Order

### Day 1 (Today)
- [x] Create optimization plan (this document)
- [ ] **Phase A:** Parameter tuning (4-6 hours)
- [ ] Run backtests with new parameters
- [ ] Analyze results
- [ ] **Phase B:** Start regime weight optimization (2-3 hours)

### Day 2
- [ ] **Phase B:** Complete regime weight optimization (4-5 hours)
- [ ] Run backtests with optimized weights
- [ ] **Phase C:** Start feature engineering (4-5 hours)

### Day 3
- [ ] **Phase C:** Complete feature engineering (4-6 hours)
- [ ] **Phase D:** Implement walk-forward optimization (4-5 hours)

### Day 4
- [ ] **Phase D:** Complete walk-forward testing (4-5 hours)
- [ ] **Phase E:** Download additional historical data (3-4 hours)
- [ ] Load data into database (2-3 hours)

### Day 5
- [ ] **Phase E:** Retrain models with expanded data (3-4 hours)
- [ ] **Phase F:** Risk management refinement (4-6 hours)
- [ ] Final comprehensive backtest
- [ ] Results analysis and documentation

---

## Success Criteria

### Minimum Acceptable Performance (GO Decision)
Must achieve **at least 2 of 3:**
- ✅ Sharpe Ratio > 1.0
- ✅ Total Return > 5% annually
- ✅ Win Rate > 50%

**AND:**
- ✅ Max Drawdown < 20%

### Stretch Goals
- Sharpe Ratio > 1.5
- Total Return > 10% annually
- Win Rate > 55%
- Max Drawdown < 15%
- Profit Factor > 2.0

---

## Testing Strategy

### After Each Phase
1. **Run comprehensive backtest** on 3 symbols (RELIANCE, TCS, HDFCBANK)
2. **Compare metrics** to baseline
3. **Document improvements** or regressions
4. **Decide:** Continue, adjust, or rollback

### Final Validation
1. **Test on all available symbols** (expand beyond 3)
2. **Test across multiple time periods** (2023-2026)
3. **Test different market regimes** (bull, bear, sideways)
4. **Validate walk-forward results**
5. **Compare with buy-and-hold benchmark**

---

## Risk Mitigation

### Version Control
- **Tag baseline version** before changes
- **Commit after each phase** with clear messages
- **Keep rollback scripts** ready

### Testing
- **Run all 36 existing tests** after each change
- **Add new tests** for new features
- **Validate no regressions**

### Documentation
- **Track all parameter changes**
- **Document rationale** for each decision
- **Record results** in structured format

---

## Deliverables

### Code Changes
1. `backtesting/strategies/ml_strategy.py` - Optimized strategy
2. `ml/regime_ensemble.py` - Tuned regime weights
3. `data/features/technical.py` - Enhanced features (new)
4. `scripts/optimize_parameters.py` - Parameter optimization script (new)
5. `scripts/comprehensive_backtest.py` - Updated backtest runner

### Documentation
1. `PHASE3_OPTIMIZATION_RESULTS.md` - Results summary
2. `PHASE3_PARAMETER_TUNING.md` - Parameter changes log
3. `PHASE3_FEATURE_ENGINEERING.md` - New features documentation
4. Updated `PHASE3_PROGRESS_TRACKER.md`

### Test Results
1. Backtest results CSV for each phase
2. Performance comparison charts
3. Walk-forward validation results
4. Final go/no-go recommendation

---

## Progress Tracking

| Phase | Status | Start | End | Duration | Result |
|-------|--------|-------|-----|----------|--------|
| A: Parameters | 🔄 NEXT | - | - | - | - |
| B: Regime Weights | ⏸️ PENDING | - | - | - | - |
| C: Features | ⏸️ PENDING | - | - | - | - |
| D: Walk-Forward | ⏸️ PENDING | - | - | - | - |
| E: More Data | ⏸️ PENDING | - | - | - | - |
| F: Risk Mgmt | ⏸️ PENDING | - | - | - | - |

---

## Next Steps

1. **Start Phase A** - Parameter tuning (NOW)
2. Create parameter optimization script
3. Test multiple parameter combinations
4. Run backtests with best parameters
5. Analyze and document results
6. Proceed to Phase B

---

**Status:** READY TO START  
**Next Action:** Phase A - Parameter Tuning  
**Timeline:** 5 days to complete all phases  
**Confidence:** HIGH (systematic approach with multiple optimization vectors)

