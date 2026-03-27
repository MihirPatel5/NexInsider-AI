"""
pipeline/phase1_runner.py — Phase 1 data pipeline orchestrator.
This is the main entrypoint for the data ingestion + feature build pipeline.

Run manually:
    poetry run python -m data.pipeline.phase1_runner

Or via Celery data-worker (configured in Phase 5).

Pipeline steps:
  1. Symbol master sync (daily)
  2. OHLCV ingestion (daily + intraday for watchlist)
  3. Corporate action check
  4. Feature engineering + feature store write
  5. News ingestion
  6. Data quality report
"""
import asyncio
from datetime import date, timedelta

from loguru import logger

from data.config import settings
from data.features.fundamental import get_fundamental_features, get_fii_dii_latest
from data.features.regime import compute_regime_features
from data.features.store import save_features_batch
from data.features.technical import compute_technical_features, compute_returns, label_signals
from data.ingestion.news import fetch_and_store_news
from data.ingestion.ohlcv_store import fetch_and_store_ohlcv, get_ohlcv
from data.symbol_master.sync import sync_nse_equity_symbols

# ─── Configuration ─────────────────────────────────────────────────────────────
WATCHLIST = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "HINDUNILVR", "BAJFINANCE", "KOTAKBANK", "SBIN", "LT",
    "WIPRO", "AXISBANK", "MARUTI", "ASIANPAINT", "ULTRACEMCO",
]
NIFTY_SYMBOL = "NIFTY 50"
DAILY_LOOKBACK_DAYS = 365 * 5   # 5 years for model training
INTRADAY_LOOKBACK_DAYS = 60     # 60 days (yfinance intraday limit)
INTERVALS_DAILY     = ["1d"]
INTERVALS_INTRADAY  = ["5min", "15min"]


async def run_symbol_sync() -> None:
    logger.info("═══ [Phase 1] Step 1: Symbol Master Sync ═══")
    n = await sync_nse_equity_symbols()
    logger.success(f"[phase1] Symbol sync complete: {n} symbols")


async def run_ohlcv_ingestion(symbols: list[str], force_full: bool = False) -> None:
    logger.info("═══ [Phase 1] Step 2: OHLCV Ingestion ═══")
    end   = date.today()
    start_daily     = end - timedelta(days=DAILY_LOOKBACK_DAYS)
    start_intraday  = end - timedelta(days=INTRADAY_LOOKBACK_DAYS)

    for symbol in symbols:
        # Daily data — 5 years
        for interval in INTERVALS_DAILY:
            try:
                n = await fetch_and_store_ohlcv(
                    symbol=symbol, exchange="NSE",
                    interval=interval,
                    start=start_daily if force_full else end - timedelta(days=7),
                    end=end,
                )
                logger.info(f"[ohlcv] {symbol} {interval}: {n} rows")
            except Exception as exc:
                logger.error(f"[ohlcv] Failed {symbol} {interval}: {exc}")

        # Intraday — 60 days
        for interval in INTERVALS_INTRADAY:
            try:
                n = await fetch_and_store_ohlcv(
                    symbol=symbol, exchange="NSE",
                    interval=interval,
                    start=start_intraday,
                    end=end,
                    apply_adj=False,  # intraday data not adjusted
                )
                logger.info(f"[ohlcv] {symbol} {interval}: {n} rows")
            except Exception as exc:
                logger.error(f"[ohlcv] Failed {symbol} {interval}: {exc}")

    logger.success("[phase1] OHLCV ingestion complete")


async def run_feature_engineering(
    symbols: list[str],
    interval: str = "1d",
    lookback_days: int = 365,
    vix: float = 15.0,
) -> None:
    logger.info("═══ [Phase 1] Step 4: Feature Engineering ═══")
    end   = date.today()
    start = end - timedelta(days=lookback_days)

    # Get Nifty data for regime detection
    nifty_df = await get_ohlcv("NIFTY", "NSE", "1d", start, end)

    for symbol in symbols:
        try:
            df = await get_ohlcv(symbol, "NSE", interval, start, end)
            if df.empty or len(df) < 30:
                logger.warning(f"[features] Insufficient data for {symbol} — skipping")
                continue

            # Technical features
            df = compute_technical_features(df)
            df = compute_returns(df)
            df = label_signals(df, horizon=5, buy_threshold=0.01, sell_threshold=-0.01)

            # Fundamental features (scalar — same for all bars, latest snapshot)
            fund = await get_fundamental_features(symbol, "NSE")
            fii_dii = await get_fii_dii_latest("NSE")

            # Regime features
            regime_feats = compute_regime_features(nifty_df, vix) if not nifty_df.empty else {}

            # Merge scalar features into each bar row
            for col, val in {**fund, **fii_dii, **regime_feats}.items():
                df[col] = val

            # Save to feature store
            await save_features_batch(df, symbol, "NSE", interval)
            logger.success(f"[features] {symbol}/{interval}: {len(df)} feature rows saved")

        except Exception as exc:
            logger.error(f"[features] Failed {symbol}: {exc}")

    logger.success("[phase1] Feature engineering complete")


async def run_news_ingestion() -> None:
    logger.info("═══ [Phase 1] Step 5: News Ingestion ═══")
    n = await fetch_and_store_news()
    logger.success(f"[phase1] News ingestion: {n} new articles")


async def run_full_pipeline(
    symbols: list[str] | None = None,
    force_full_history: bool = False,
    vix: float = 15.0,
) -> None:
    """
    Run the complete Phase 1 data pipeline.

    Args:
        symbols:            Watchlist symbols (default: WATCHLIST constant above)
        force_full_history: If True, fetch 5 years OHLCV (slow — first run only)
        vix:                Current India VIX (passed from live fetch in production)
    """
    watchlist = symbols or WATCHLIST
    logger.info(f"[phase1] Starting pipeline for {len(watchlist)} symbols | env={settings.environment}")

    await run_symbol_sync()
    await run_ohlcv_ingestion(watchlist, force_full=force_full_history)
    await run_news_ingestion()
    await run_feature_engineering(watchlist, interval="1d", vix=vix)

    logger.success("═══ [Phase 1] Pipeline Complete ═══")


if __name__ == "__main__":
    import sys
    force = "--full" in sys.argv
    asyncio.run(run_full_pipeline(force_full_history=force))
