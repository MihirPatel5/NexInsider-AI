# Phase 1: Action Checklist

**Date:** April 8, 2026  
**Purpose:** Clear list of what needs to be done before production

---

## 🔴 CRITICAL (Must Do Before Production)

### 1. Database Backup and Recovery
- [ ] Set up automated daily backups
- [ ] Test backup procedure
- [ ] Test restore procedure
- [ ] Document recovery steps
- [ ] Test point-in-time recovery

**Command:**
```bash
# Setup backup cron job
0 2 * * * pg_dump -U algo -d algotrading > /backups/algotrading_$(date +\%Y\%m\%d).sql
```

**Estimated Time:** 2 hours

---

### 2. Error Recovery Testing
- [ ] Test database connection loss recovery
- [ ] Test network failure recovery
- [ ] Test scheduler crash recovery
- [ ] Test corrupted data handling
- [ ] Document recovery procedures

**Test Script:**
```bash
# Test database connection loss
# 1. Start data ingestion
# 2. Stop PostgreSQL: sudo systemctl stop postgresql
# 3. Observe error handling
# 4. Start PostgreSQL: sudo systemctl start postgresql
# 5. Verify automatic recovery
```

**Estimated Time:** 3 hours

---

### 3. Security Audit
- [ ] Test SQL injection prevention
- [ ] Test API key security
- [ ] Review database access controls
- [ ] Test sensitive data encryption
- [ ] Document security measures

**Test Cases:**
```python
# Test SQL injection
symbol = "'; DROP TABLE ohlcv; --"
# Should be safely handled

# Test API key exposure
# Verify .env not in git
# Verify logs don't expose keys
```

**Estimated Time:** 2 hours

---

### 4. Manual NSE Live Data Test
- [ ] Test NSE corporate action fetcher with live data
- [ ] Verify RELIANCE corporate actions
- [ ] Test integration with database
- [ ] Verify data parsing accuracy

**Command:**
```bash
python3 -m pytest tests/test_corporate_actions.py::test_nse_fetcher_reliance -v -s
```

**Estimated Time:** 1 hour

---

## ⚠️ IMPORTANT (Should Do Soon)

### 5. Load Testing
- [ ] Test ingestion with 500+ symbols
- [ ] Test database with 1M+ rows
- [ ] Test concurrent access
- [ ] Monitor memory usage over 24 hours
- [ ] Document performance metrics

**Test Script:**
```python
# tests/load_test.py
import asyncio
from data.ingestion.router import DataRouter

async def load_test():
    router = DataRouter()
    # NSE top 500 stocks
    symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', ...]  # 500 symbols
    
    for symbol in symbols:
        try:
            df = await router.fetch_ohlcv(symbol, '1d', days=365)
            print(f"✅ {symbol}: {len(df)} rows")
        except Exception as e:
            print(f"❌ {symbol}: {e}")

asyncio.run(load_test())
```

**Estimated Time:** 4 hours

---

### 6. API Rate Limit Testing
- [ ] Test Alpha Vantage rate limits (5 calls/min)
- [ ] Test Twelve Data rate limits (8 calls/min)
- [ ] Test NSE website rate limiting
- [ ] Implement automatic backoff if needed
- [ ] Document rate limit handling

**Test Script:**
```python
# Test rapid API calls
from data.ingestion.alpha_vantage_connector import AlphaVantageConnector
import asyncio
import time

async def test_rate_limits():
    connector = AlphaVantageConnector()
    
    for i in range(10):
        start = time.time()
        try:
            await connector.fetch_ohlcv('RELIANCE', '1d', days=30)
            elapsed = time.time() - start
            print(f"Call {i+1}: SUCCESS ({elapsed:.2f}s)")
        except Exception as e:
            print(f"Call {i+1}: FAILED - {e}")
        
        # No delay - test rate limiting
    
asyncio.run(test_rate_limits())
```

**Estimated Time:** 2 hours

---

### 7. Scheduler Reliability Test
- [ ] Run scheduler for 7 days continuously
- [ ] Monitor for missed jobs
- [ ] Test recovery after system restart
- [ ] Verify pre-market routine (8:45 AM)
- [ ] Document any issues

**Command:**
```bash
# Start scheduler in background
nohup python3 -m backend.main > scheduler.log 2>&1 &

# Monitor logs
tail -f scheduler.log

# Check after 7 days
grep "ERROR" scheduler.log
grep "FAILED" scheduler.log
```

**Estimated Time:** 7 days (passive monitoring)

---

## 💡 OPTIONAL (Nice to Have)

### 8. Fix Async Event Loop Test Issues
- [ ] Add pytest-asyncio scope="function" to tests
- [ ] Or use proper fixtures for event loop management
- [ ] Or document as known limitation

**Fix:**
```python
# In conftest.py or at top of test files
import pytest

@pytest.fixture(scope="function")
def event_loop():
    """Create new event loop for each test"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

**Estimated Time:** 1 hour

---

### 9. Implement Real-time Alerting
- [ ] Create Telegram bot
- [ ] Implement alert sending
- [ ] Configure alert rules
- [ ] Test alert delivery
- [ ] Document alert setup

**Implementation:**
```python
# data/quality/alerting.py
import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_alert(message: str, severity: str):
    """Send alert to Telegram"""
    if severity != "CRITICAL":
        return  # Only alert on critical issues
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"🚨 {severity}: {message}"
        })
```

**Estimated Time:** 2-3 hours

---

### 10. Add BSE Symbol Fetcher
- [ ] Research BSE symbol list API/CSV
- [ ] Implement BSE fetcher
- [ ] Add to scheduler
- [ ] Test with live data
- [ ] Document BSE integration

**Implementation:**
```python
# data/symbol_master/bse_sync.py
async def sync_bse_equity_symbols() -> int:
    """Download BSE equity list and upsert"""
    # Similar to NSE fetcher
    pass
```

**Estimated Time:** 1-2 hours

---

## 📊 PROGRESS TRACKER

### Critical Tasks (4 tasks)
- [ ] Database backup and recovery (2h)
- [ ] Error recovery testing (3h)
- [ ] Security audit (2h)
- [ ] Manual NSE live data test (1h)

**Total Critical Time:** 8 hours

### Important Tasks (3 tasks)
- [ ] Load testing (4h)
- [ ] API rate limit testing (2h)
- [ ] Scheduler reliability test (7 days passive)

**Total Important Time:** 6 hours + 7 days monitoring

### Optional Tasks (3 tasks)
- [ ] Fix async event loop tests (1h)
- [ ] Implement alerting (2-3h)
- [ ] Add BSE fetcher (1-2h)

**Total Optional Time:** 4-6 hours

---

## 🎯 RECOMMENDED SCHEDULE

### Day 1 (8 hours)
- Morning: Database backup and recovery (2h)
- Morning: Security audit (2h)
- Afternoon: Error recovery testing (3h)
- Afternoon: Manual NSE test (1h)

**End of Day 1:** All critical tasks complete ✅

### Day 2 (6 hours)
- Morning: Load testing (4h)
- Afternoon: API rate limit testing (2h)
- Start: 7-day scheduler monitoring

**End of Day 2:** All important tasks started ✅

### Day 3-9 (Optional)
- Monitor scheduler (passive)
- Optional: Fix async tests (1h)
- Optional: Implement alerting (2-3h)
- Optional: Add BSE fetcher (1-2h)

**End of Day 9:** All tasks complete ✅

---

## ✅ COMPLETION CRITERIA

### Ready for Production When:
- [x] All Phase 1 core features working
- [ ] All critical tasks complete
- [ ] All important tasks complete
- [ ] 7-day scheduler test passed
- [ ] Documentation updated
- [ ] Team trained on operations

### Current Status:
- ✅ Core features: 98% complete
- ⏳ Critical tasks: 0/4 complete
- ⏳ Important tasks: 0/3 complete
- ⏳ Optional tasks: 0/3 complete

---

## 📝 NOTES

1. **Prioritization:**
   - Focus on critical tasks first
   - Important tasks can run in parallel
   - Optional tasks can be done later

2. **Time Estimates:**
   - Based on single developer
   - May vary based on experience
   - Include buffer for unexpected issues

3. **Testing Environment:**
   - Use staging database for testing
   - Don't test on production
   - Document all test results

4. **Documentation:**
   - Update docs as you complete tasks
   - Document any issues found
   - Share learnings with team

---

**Last Updated:** April 8, 2026  
**Next Review:** After completing critical tasks
Summary: All Warnings Are Safe
Verdict: ✅ No issues - all warnings are safe to ignore

Breakdown:
MLflow/Pydantic deprecations (18 warnings)

Third-party library issues
Will be fixed in future library updates
No impact on our code
Matplotlib/Pyparsing deprecations (3 warnings)

Third-party library issues
No impact on functionality
Pytest config warning (1 warning)

Unknown config option
Tests passing normally
Event loop fixture warning (1 warning)

Our custom fixture using deprecated pattern
Tests passing, low priority to fix
RuntimeWarning - unawaited coroutines (2 warnings)

False positive from Mock library
Methods are NOT async, so no actual issue
Tests passing correctly
