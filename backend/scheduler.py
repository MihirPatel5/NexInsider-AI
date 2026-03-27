"""
backend/scheduler.py — Market routine scheduler.
Uses APScheduler to trigger Celery tasks at specific IST times.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from datetime import datetime
from pytz import timezone

from backend.workers.data_worker import ingest_daily_market_data
from backend.workers.signal_worker import generate_signal

IST = timezone('Asia/Kolkata')
scheduler = AsyncIOScheduler(timezone=IST)

# ─── Pre-Market (8:45 AM IST) ─────────────────────────────────────────────────
@scheduler.scheduled_job(CronTrigger(hour=8, minute=45, day_of_week='mon-fri'))
def pre_market_routine():
    logger.info("[scheduler] Starting PRE-MARKET routine...")
    # Trigger symbol sync and news fetch
    ingest_daily_market_data.delay()

# ─── Market Open (9:15 AM IST) ────────────────────────────────────────────────
@scheduler.scheduled_job(CronTrigger(hour=9, minute=15, day_of_week='mon-fri'))
def market_open_routine():
    logger.info("[scheduler] MARKET OPEN — Activating signal engine.")
    # Initialize live feeds

# ─── Intraday Scanning (Every 15 mins) ────────────────────────────────────────
@scheduler.scheduled_job(CronTrigger(minute='*/15', hour='9-15', day_of_week='mon-fri'))
def intraday_scan():
    logger.info("[scheduler] Triggering intraday signal scan...")
    # generate_signal.delay("RELIANCE") 

# ─── Market Close (3:30 PM IST) ───────────────────────────────────────────────
@scheduler.scheduled_job(CronTrigger(hour=15, minute=30, day_of_week='mon-fri'))
def market_close_routine():
    logger.info("[scheduler] MARKET CLOSE — Generating reports.")
    # Post-market analysis tasks
