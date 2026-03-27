"""
backend/workers/data_worker.py — Data ingestion worker.
Executes scheduled and on-demand OHLCV + News fetching.
"""
from backend.celery_app import celery
from data.pipeline.phase1_runner import run_full_pipeline
from loguru import logger
import asyncio


@celery.task(name="backend.workers.data_worker.ingest_daily_market_data")
def ingest_daily_market_data(symbols: list = None):
    """Fetch daily bars and fundamentals for target symbols."""
    logger.info(f"[data_worker] Starting daily ingestion for {len(symbols) if symbols else 'watchlist'}")
    asyncio.run(run_full_pipeline(symbols=symbols))
    return {"status": "SUCCESS"}


@celery.task(name="backend.workers.data_worker.ingest_intraday_data")
def ingest_intraday_data(symbol: str, interval: str = "5min"):
    """Fetch latest intraday bars for live signal processing."""
    from data.ingestion.ohlcv_store import fetch_and_store_ohlcv
    from datetime import date, timedelta
    
    logger.info(f"[data_worker] Fetching intraday {symbol} {interval}")
    asyncio.run(
        fetch_and_store_ohlcv(
            symbol, "NSE", interval, 
            start=date.today() - timedelta(days=1), 
            end=date.today(),
            apply_adj=False
        )
    )
    return {"status": "SUCCESS"}
