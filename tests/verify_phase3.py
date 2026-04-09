"""
tests/verify_phase3.py — Comprehensive Phase 3 verification suite.
Validates the execution flow from the Automation routines all the way down to PaperBroker DB logging.
"""
import pytest
import asyncio
from sqlalchemy import text
from datetime import date

from automation.routines import run_intraday_loop
from data.db import get_session
from data.config import settings
from data.ingestion.ohlcv_store import fetch_and_store_ohlcv

@pytest.mark.asyncio
async def test_live_execution_loop():
    """
    Test the full intraday orchestration heartbeat.
    Ensures that for a given watchlist, signals are evaluated synchronously 
    and mock executions propagate via RiskManager -> OrderWorker -> DB.
    """
    print("\n[verify_phase3] Step 1: Initializing & Cleaning Paper Trading tables...")
    async with get_session() as session:
        # Scaffold tables for headless testing
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                exchange VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                quantity INT NOT NULL,
                entry_price NUMERIC NOT NULL,
                entry_time TIMESTAMPTZ NOT NULL
            )
        """))
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_positions (
                symbol VARCHAR(50) PRIMARY KEY,
                quantity INT NOT NULL,
                avg_price NUMERIC NOT NULL
            )
        """))
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS data_quality_log (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                exchange VARCHAR(20) NOT NULL,
                source VARCHAR(50) NOT NULL,
                issue_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                affected_time TIMESTAMPTZ NOT NULL,
                detail TEXT
            )
        """))
        await session.execute(text("DELETE FROM trade_history WHERE symbol LIKE 'MOCK_%'"))
        await session.execute(text("DELETE FROM paper_positions WHERE symbol LIKE 'MOCK_%'"))
        await session.execute(text("DELETE FROM ohlcv WHERE symbol LIKE 'MOCK_%'"))
        await session.commit()
        
    print("[verify_phase3] Step 2: Seeding Mock Database with price history...")
    from datetime import timedelta
    # Seeding MOCK_RELIANCE as an NSE symbol for signal_worker compatibility
    await fetch_and_store_ohlcv("MOCK_RELIANCE", "NSE", "1d", date.today() - timedelta(days=500), date.today())
        
    print("[verify_phase3] Step 3: Firing Intraday Automation Loop (Sync Mode)...")
    # Using 'MOCK_' prefix ensures the router intercepts and bypasses real API calls
    watchlist = ["MOCK_RELIANCE"]
    
    # Run the loop synchronously so we can await completion without firing Celery broker
    results = await run_intraday_loop(watchlist, sync=True)
    
    # Wait lightly for background place_order_task async tasks to settle
    await asyncio.sleep(1)
    
    print("[verify_phase3] Step 4: Verifying Signal Generation...")
    assert len(results) == 1, "Automation loop failed to return results"
    signal_res = results[0]
    assert signal_res is not None, "Signal worker returned None - check inference logic"
    
    # Determine what *should* have happened based on generated signal
    signal = signal_res['signal']
    confidence = signal_res['confidence']
    print(f"  ↳ Generated Signal: {signal} (Conf: {confidence:.2f})")
    
    print("[verify_phase3] Step 5: Verifying Trade History DB Persistance...")
    async with get_session() as session:
        trades = await session.execute(text("SELECT symbol, side, quantity, entry_price FROM trade_history WHERE symbol = 'MOCK_RELIANCE'"))
        trades = trades.fetchall()
        
        if signal in ['BUY', 'SELL'] and confidence >= settings.signal_confidence_threshold:
            assert len(trades) > 0, "Signal was actionable but NO trades logged in DB. PaperBroker integration failed!"
            for t in trades:
                print(f"  ↳ Executed: {t.side} {t.quantity} {t.symbol} @ {t.entry_price}")
        else:
            assert len(trades) == 0, f"Signal was non-actionable ({signal}, conf: {confidence:.2f}) but trades were executed!"
            print("  ↳ Correctly skipped trade execution due to low confidence or HOLD signal.")
            
    print("✅ Phase 3 Live Execution & Automation Verified.")

if __name__ == "__main__":
    asyncio.run(test_live_execution_loop())
