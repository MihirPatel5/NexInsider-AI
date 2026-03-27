"""
automation/routines.py — Automated trading lifecycle routines.
These functions coordinate multiple workers and modules for daily operations.
"""
from loguru import logger
import asyncio
from datetime import datetime

from backend.workers.data_worker import ingest_daily_market_data
from backend.workers.signal_worker import generate_signal
from risk.manager import RiskManager


async def run_pre_market():
    """8:45 AM — Sync symbols, fetch news, prepare watchlist."""
    logger.info("[routine] Starting PRE-MARKET synchronization...")
    # 1. Sync NSE Master
    # 2. Fetch News for sentiment
    # 3. Update watchlist based on yesterday's breakout/volume
    ingest_daily_market_data.delay()
    logger.success("[routine] Pre-market complete.")


async def run_market_open():
    """9:15 AM — Initialize live price listeners and enable order execution."""
    logger.info("[routine] MARKET OPEN — Initializing live execution engine.")
    # 1. Check broker connectivity
    # 2. Reset daily loss tracking in RiskManager
    # 3. Start intraday heartbeat


async def run_intraday_loop(watchlist: list):
    """5-minute re-score loop for all watchlist items + open positions."""
    logger.info(f"[routine] INTRADAY LOOP — Scoring {len(watchlist)} symbols.")
    for symbol in watchlist:
        # Generate signal asynchronously
        generate_signal.delay(symbol, interval="5min")


async def run_market_close():
    """3:30 PM — Flatten intraday positions and generate daily report."""
    logger.info("[routine] MARKET CLOSE — Finalising daily operations.")
    # 1. Square off MIS/Intraday positions
    # 2. Stop signal engine
    # 3. Trigger report generation


async def run_after_hours():
    """After 4 PM — DB maintenance and model retraining."""
    logger.info("[routine] AFTER-HOURS — Maintenance and training.")
    # 1. Vacuum DB tables
    # 2. Incremental model retraining on today's bars
