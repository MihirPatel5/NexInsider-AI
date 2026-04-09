# Phase 2: ML/AI Engine - Action Checklist

**Date:** April 8, 2026  
**Purpose:** Clear actionable tasks to complete Phase 2

---

## 🔴 CRITICAL TASKS (Must Complete Before Paper Trading)

### Task 1: Implement Model Drift Detection
**Priority:** CRITICAL  
**Estimated Time:** 12-16 hours

**Subtasks:**
- [ ] Create `ml/drift_detection.py` with PSI calculation
- [ ] Implement feature drift monitoring
- [ ] Implement prediction drift monitoring
- [ ] Add auto-pause on drift threshold (PSI > 0.2)
- [ ] Integrate with alerting system
- [ ] Write unit tests (`tests/test_drift_detection.py`)
- [ ] Test with synthetic data (no drift, moderate drift, significant drift)
- [ ] Test with historical data
- [ ] Document drift thresholds and response procedures

**Acceptance Criteria:**
- PSI calculation works correctly
- Detects drift in synthetic data
- Auto-pauses model on significant drift
- Alerts sent on drift detection
- All tests passing

**Command to Test:**
```bash
python3 -m pytest tests/test_drift_detection.py -v
```

---

### Task 2: Implement Holdout Dataset Protocol
**Priority:** CRITICAL  
**Estimated Time:** 8-12 hours

**Subtasks:**
- [ ] Create `ml/data_split.py` with temporal splitting
- [ ] Split data into train (60%), val (20%), holdout (20%)
- [ ] Implement strict access controls for holdout
- [ ] Create `ml/holdout_validator.py`
- [ ] Run final validation on holdout set
- [ ] Document holdout results
- [ ] Write tests (`tests/test_holdout_protocol.py`)
- [ ] Verify no data leakage

**Acceptance Criteria:**
- Data split correctly (temporal order preserved)
- Holdout set never touched during development
- Validation results documented
- Model meets minimum criteria (accuracy > 0.55)
- All tests passing

**Command to Run:**
```bash
python3 -c "
from ml.holdout_validator import HoldoutValidator
from ml.ensemble import EnsembleModel

model = EnsembleModel.load('latest')
validator = HoldoutValidator(model)
results = validator.validate(holdout_features, holdout_labels)
print(results)
"
```

---

### Task 3: Implement Model Performance Monitoring
**Priority:** CRITICAL  
**Estimated Time:** 8 hours

**Subtasks:**
- [ ] Create `ml/monitoring/performance_monitor.py`
- [ ] Implement prediction logging
- [ ] Implement actual vs predicted tracking
- [ ] Calculate rolling performance metrics
- [ ] Add performance degradation alerts
- [ ] Create database tables for monitoring
- [ ] Write tests (`tests/test_performance_monitoring.py`)
- [ ] Create monitoring dashboard queries

**Acceptance Criteria:**
- All predictions logged
- Actual outcomes tracked
- Rolling metrics calculated (accuracy, precision, recall)
- Alerts sent on degradation
- All tests passing

**Database Schema:**
```sql
CREATE TABLE model_predictions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    prediction INTEGER NOT NULL,  -- 0=SELL, 1=HOLD, 2=BUY
    confidence NUMERIC(5,4) NOT NULL,
    features JSONB NOT NULL,
    actual_outcome INTEGER,  -- Filled later
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_predictions_timestamp ON model_predictions(timestamp DESC);
CREATE INDEX idx_predictions_symbol ON model_predictions(symbol);
```

---

### Task 4: Test Models on Recent Data
**Priority:** HIGH  
**Estimated Time:** 4 hours

**Subtasks:**
- [ ] Load models
- [ ] Prepare recent data (last 3 months)
- [ ] Run inference on recent data
- [ ] Calculate performance metrics
- [ ] Compare to backtest performance
- [ ] Document results
- [ ] Identify any issues

**Acceptance Criteria:**
- Models tested on last 3 months
- Performance metrics calculated
- Results documented
- Performance acceptable (within 20% of backtest)

**Command to Run:**
```bash
python3 scripts/test_recent_performance.py --start-date 2026-01-01 --end-date 2026-04-08
```

---

### Task 5: Benchmark Inference Speed
**Priority:** HIGH  
**Estimated Time:** 2 hours

**Subtasks:**
- [ ] Create benchmark script
- [ ] Test single symbol inference
- [ ] Test batch inference (500 symbols)
- [ ] Test concurrent inference
- [ ] Measure memory usage
- [ ] Document results
- [ ] Optimize if needed

**Acceptance Criteria:**
- Single symbol: < 100ms
- Batch (500 symbols): < 50 seconds (< 100ms per symbol)
- Memory usage: < 2GB
- Results documented

**Command to Run:**
```bash
python3 scripts/benchmark_inference.py
```

---

## ⚠️ IMPORTANT TASKS (Should Complete Soon)

### Task 6: Implement Regime Detection
**Priority:** MEDIUM  
**Estimated Time:** 12-16 hours

**Subtasks:**
- [ ] Create `ml/regime_detection.py`
- [ ] Implement regime detection algorithm (VIX, trend, volatility)
- [ ] Define regimes (bull, bear, sideways, high-vol)
- [ ] Train regime-specific model variants
- [ ] Implement model switching logic
- [ ] Add regime transition handling
- [ ] Write tests (`tests/test_regime_detection.py`)
- [ ] Test with historical data

**Acceptance Criteria:**
- Regime detection works
- Model switching works
- Performance improves in different regimes
- All tests passing

---

### Task 7: Implement Automated Retraining Pipeline
**Priority:** MEDIUM  
**Estimated Time:** 12-16 hours

**Subtasks:**
- [ ] Create `ml/retraining/scheduler.py`
- [ ] Implement incremental retraining (weekly)
- [ ] Implement full retraining (monthly)
- [ ] Add retraining triggers (drift, performance)
- [ ] Implement model versioning
- [ ] Create rollback mechanism
- [ ] Write tests (`tests/test_retraining.py`)
- [ ] Document retraining procedures

**Acceptance Criteria:**
- Retraining runs automatically
- Models versioned correctly
- Rollback works
- All tests passing

---

### Task 8: Test Model Robustness
**Priority:** MEDIUM  
**Estimated Time:** 4 hours

**Subtasks:**
- [ ] Test with missing features
- [ ] Test with stale data
- [ ] Test with outliers
- [ ] Test with data quality issues
- [ ] Document behavior
- [ ] Implement graceful degradation if needed

**Acceptance Criteria:**
- Model handles missing data gracefully
- Model handles outliers
- Behavior documented
- No crashes

---

### Task 9: Implement Model Versioning
**Priority:** MEDIUM  
**Estimated Time:** 4 hours

**Subtasks:**
- [ ] Enhance MLflow integration
- [ ] Implement model rollback procedure
- [ ] Create A/B testing framework
- [ ] Implement gradual rollout
- [ ] Write tests
- [ ] Document procedures

**Acceptance Criteria:**
- Models versioned in MLflow
- Rollback works
- A/B testing possible
- All tests passing

---

## 💡 OPTIONAL TASKS (Nice to Have)

### Task 10: Add Model Explainability
**Priority:** LOW  
**Estimated Time:** 8 hours

**Subtasks:**
- [ ] Implement SHAP values
- [ ] Calculate feature importance
- [ ] Create prediction explanations
- [ ] Add to monitoring dashboard
- [ ] Document interpretation

**Acceptance Criteria:**
- SHAP values calculated
- Feature importance available
- Explanations useful

---

## 📊 PROGRESS TRACKER

### Critical Tasks (5 tasks)
- [ ] Model drift detection (12-16h)
- [ ] Holdout dataset protocol (8-12h)
- [ ] Performance monitoring (8h)
- [ ] Test on recent data (4h)
- [ ] Benchmark inference speed (2h)

**Total Critical Time:** 34-42 hours (~5-6 days)

### Important Tasks (4 tasks)
- [ ] Regime detection (12-16h)
- [ ] Automated retraining (12-16h)
- [ ] Test robustness (4h)
- [ ] Model versioning (4h)

**Total Important Time:** 32-40 hours (~4-5 days)

### Optional Tasks (1 task)
- [ ] Model explainability (8h)

**Total Optional Time:** 8 hours (~1 day)

---

## 🎯 RECOMMENDED SCHEDULE

### Week 1: Critical Tasks (Days 1-6)

**Day 1-2: Drift Detection**
- Morning: Implement PSI calculation
- Afternoon: Implement feature drift monitoring
- Evening: Write tests

**Day 3: Holdout Protocol**
- Morning: Implement data splitting
- Afternoon: Create holdout validator
- Evening: Run holdout validation

**Day 4: Performance Monitoring**
- Morning: Implement prediction logging
- Afternoon: Implement metrics calculation
- Evening: Write tests

**Day 5: Testing**
- Morning: Test on recent data
- Afternoon: Benchmark inference speed
- Evening: Document results

**Day 6: Integration & Bug Fixes**
- All day: Integrate components, fix bugs, run all tests

**End of Week 1:** All critical tasks complete ✅

---

### Week 2: Important Tasks (Days 7-11)

**Day 7-8: Regime Detection**
- Day 7: Implement regime detection algorithm
- Day 8: Train regime-specific models, write tests

**Day 9-10: Automated Retraining**
- Day 9: Implement retraining scheduler
- Day 10: Implement versioning and rollback

**Day 11: Testing & Documentation**
- Morning: Test robustness
- Afternoon: Implement model versioning
- Evening: Documentation

**End of Week 2:** All important tasks complete ✅

---

### Week 3: Optional & Final Validation (Days 12-15)

**Day 12: Optional Tasks**
- Implement model explainability (if time permits)

**Day 13-14: Comprehensive Testing**
- Run all tests
- Integration testing
- Performance testing
- Edge case testing

**Day 15: Documentation & Handoff**
- Update all documentation
- Create runbooks
- Training materials
- Final review

**End of Week 3:** Phase 2 complete ✅

---

## ✅ COMPLETION CRITERIA

### Phase 2 Complete When:
- [x] All ML models implemented
- [ ] Drift detection working and tested
- [ ] Holdout validation passed
- [ ] Performance monitoring in place
- [ ] Recent data testing complete
- [ ] Inference speed acceptable
- [ ] All critical tests passing
- [ ] Documentation complete

### Ready for Paper Trading When:
- [ ] All critical tasks complete
- [ ] Holdout validation shows acceptable performance
- [ ] Drift detection tested with historical data
- [ ] Performance monitoring working
- [ ] All tests passing (>90% coverage)
- [ ] Team trained on operations

---

## 📝 DAILY CHECKLIST

### Every Day:
- [ ] Run all tests before committing
- [ ] Update progress tracker
- [ ] Document any issues
- [ ] Commit code with clear messages
- [ ] Update this checklist

### End of Each Task:
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Task marked complete

---

## 🚨 BLOCKERS & RISKS

### Current Blockers:
- None (all dependencies available)

### Potential Risks:
1. **Holdout validation fails** - May need to retrain models
2. **Inference too slow** - May need optimization
3. **Drift detection too sensitive** - May need threshold tuning
4. **Recent data performance poor** - May need model updates

### Mitigation:
- Start with critical tasks first
- Test early and often
- Have backup plans
- Document all decisions

---

## 📚 RESOURCES

### Code References:
- `ml/models/` - Existing ML models
- `ml/ensemble.py` - Ensemble implementation
- `ml/validation.py` - Validation framework
- `ml/training_pipeline.py` - Training pipeline

### Documentation:
- `PHASE2_ASSESSMENT_AND_PLAN.md` - Detailed plan
- `PHASE2_ISSUES_AND_GAPS.md` - Known issues
- `PRODUCTION_STATUS.md` - Overall status

### Tools:
- MLflow - Experiment tracking
- pytest - Testing framework
- pandas - Data manipulation
- scikit-learn - ML utilities

---

**Last Updated:** April 8, 2026  
**Next Review:** End of Week 1
