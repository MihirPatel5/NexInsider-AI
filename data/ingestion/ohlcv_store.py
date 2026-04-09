"""
ingestion/ohlcv_store.py — OHLCV persistence layer.
Fetches via the data router, applies corporate-action adjustment and
quality checks, then bulk-upserts into the TimescaleDB ohlcv table.
"""
from datetime import date

import pandas as pd
from loguru import logger
from sqlalchemy import text

from data.corporate_actions.pipeline import apply_backward_adjustment, get_adjustment_factors
from data.db import get_session
from data.ingestion.router import router
from data.quality.checker import validate_ohlcv_frame


async def fetch_and_store_ohlcv(
    symbol: str,
    exchange: str,
    interval: str,
    start: date,
    end: date,
    apply_adj: bool = True,
) -> int:
    """
    Full ingestion pipeline for one symbol:
      1. Fetch OHLCV via data router (jugaad → yfinance fallback)
      2. Run data quality checks (outliers, missing bars)
      3. Apply corporate-action backward adjustment (for daily data)
      4. Bulk-upsert into ohlcv table

    Returns number of rows upserted.
    """
    df = await router.fetch_ohlcv(symbol, exchange, interval, start, end)

    if df.empty:
        logger.warning(f"[ohlcv_store] No data for {symbol}/{interval} {start}→{end}")
        return 0

    # Quality check (logs issues but doesn't drop rows)
    df = await validate_ohlcv_frame(df, symbol, exchange, interval, df["source"].iloc[0])

    # Corporate action adjustment (only meaningful for daily / weekly)
    if apply_adj and interval in ("1d", "1w"):
        actions = await get_adjustment_factors(symbol, exchange)
        df = apply_backward_adjustment(df, actions)
    else:
        df["adj_close"] = df["close"]
        df["adj_factor"] = 1.0

    # Remove outlier rows rather than storing garbage prices
    if "is_outlier" in df.columns:
        n_outliers = df["is_outlier"].sum()
        if n_outliers:
            logger.warning(f"[ohlcv_store] Dropping {n_outliers} outlier rows for {symbol}")
        df = df[~df["is_outlier"]]

    rows = _df_to_rows(df, symbol, exchange, interval)
    if not rows:
        return 0

    count = await _bulk_upsert(rows)
    logger.info(f"[ohlcv_store] Upserted {count} rows for {symbol}/{interval}")
    return count


def _df_to_rows(df: pd.DataFrame, symbol: str, exchange: str, interval: str) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        t = r["time"]
        if hasattr(t, "to_pydatetime"):
            t = t.to_pydatetime()
            
        rows.append({
            "time":      t,
            "symbol":    symbol,
            "exchange":  exchange,
            "interval":  interval,
            "open":      float(r["open"]),
            "high":      float(r["high"]),
            "low":       float(r["low"]),
            "close":     float(r["close"]),
            "volume":    int(r["volume"]),
            "adj_close": float(r.get("adj_close", r["close"])),
            "adj_factor":float(r.get("adj_factor", 1.0)),
            "source":    str(r.get("source", "unknown")),
        })
    return rows


async def _bulk_upsert(rows: list[dict]) -> int:
    """Upsert rows into ohlcv hypertable, batched in chunks of 500."""
    CHUNK = 500
    total = 0
    upsert_sql = text("""
        INSERT INTO ohlcv
            (time, symbol, exchange, interval, open, high, low, close, volume, adj_close, adj_factor, source)
        VALUES
            (:time, :symbol, :exchange, :interval, :open, :high, :low, :close, :volume, :adj_close, :adj_factor, :source)
        ON CONFLICT (time, symbol, exchange, interval)
        DO UPDATE SET
            open       = EXCLUDED.open,
            high       = EXCLUDED.high,
            low        = EXCLUDED.low,
            close      = EXCLUDED.close,
            volume     = EXCLUDED.volume,
            adj_close  = EXCLUDED.adj_close,
            adj_factor = EXCLUDED.adj_factor,
            source     = EXCLUDED.source
    """)

    async with get_session() as session:
        for i in range(0, len(rows), CHUNK):
            chunk = rows[i : i + CHUNK]
            await session.execute(upsert_sql, chunk)
            total += len(chunk)

    return total


async def get_ohlcv(
    symbol: str,
    exchange: str,
    interval: str,
    start: date,
    end: date,
    use_adj: bool = True,
) -> pd.DataFrame:
    """
    Retrieve OHLCV data from DB for a symbol.
    Returns adjusted prices by default.
    """
    price_col = "adj_close" if use_adj else "close"
    async with get_session() as session:
        result = await session.execute(
            text(f"""
                SELECT time, open, high, low, {price_col} AS close, volume, adj_factor
                FROM ohlcv
                WHERE symbol   = :symbol
                  AND exchange = :exchange
                  AND interval = :interval
                  AND time BETWEEN :start AND :end
                ORDER BY time ASC
            """),
            {"symbol": symbol, "exchange": exchange, "interval": interval,
             "start": start, "end": end},
        )
        rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume", "adj_factor"])
    
    # Cast Decimal columns to float for Pandas compatibility
    for col in ["open", "high", "low", "close", "adj_factor"]:
        df[col] = df[col].astype(float)
        
    df["symbol"]   = symbol
    df["exchange"] = exchange
    df["interval"] = interval
    return df
