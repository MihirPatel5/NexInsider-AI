"""
features/store.py — Feature store writer.
Saves computed feature snapshots to the feature_store table keyed by
(symbol, exchange, time, interval, feature_version).
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from loguru import logger
from sqlalchemy import text

from data.config import settings
from data.db import get_session

IST = ZoneInfo("Asia/Kolkata")


async def save_features(
    symbol: str,
    exchange: str,
    bar_time: datetime,
    interval: str,
    features: dict,
    feature_version: str | None = None,
) -> None:
    """
    Upsert a single feature snapshot into the feature store.
    feature_version defaults to settings.feature_version.
    """
    version = feature_version or settings.feature_version
    async with get_session() as session:
        await session.execute(
            text("""
                INSERT INTO feature_store
                    (symbol, exchange, time, interval, feature_version, features)
                VALUES (:symbol, :exchange, :time, :interval, :feature_version, :features)
                ON CONFLICT (symbol, exchange, time, interval, feature_version)
                DO UPDATE SET features = EXCLUDED.features, created_at = NOW()
            """),
            dict(
                symbol=symbol,
                exchange=exchange,
                time=bar_time,
                interval=interval,
                feature_version=version,
                features=json.dumps(features, default=str),
            ),
        )


async def save_features_batch(
    df: pd.DataFrame,
    symbol: str,
    exchange: str,
    interval: str,
    feature_version: str | None = None,
) -> int:
    """
    Save all rows of a featured DataFrame to the feature store.
    Columns in df (excluding time/symbol/exchange/interval) become
    the feature JSONB dict.

    Returns count of saved rows.
    """
    version = feature_version or settings.feature_version
    meta_cols = {"time", "symbol", "exchange", "interval", "open", "high", "low", "close", "volume"}
    feature_cols = [c for c in df.columns if c not in meta_cols]

    rows = []
    for _, row in df.iterrows():
        feature_dict = {col: (None if pd.isna(row[col]) else float(row[col])) for col in feature_cols}
        rows.append({
            "symbol":          symbol,
            "exchange":        exchange,
            "time":            row["time"],
            "interval":        interval,
            "feature_version": version,
            "features":        json.dumps(feature_dict, default=str),
        })

    if not rows:
        return 0

    async with get_session() as session:
        await session.execute(
            text("""
                INSERT INTO feature_store
                    (symbol, exchange, time, interval, feature_version, features)
                SELECT :symbol, :exchange, :time::timestamptz, :interval, :feature_version, :features::jsonb
                FROM (VALUES (:symbol, :exchange, :time, :interval, :feature_version, :features)) AS t
                ON CONFLICT (symbol, exchange, time, interval, feature_version)
                DO UPDATE SET features = EXCLUDED.features
            """),
            rows,
        )

    logger.info(f"[feature_store] Saved {len(rows)} feature snapshots for {symbol}/{interval} v{version}")
    return len(rows)


async def get_latest_features(
    symbol: str,
    exchange: str,
    interval: str,
    feature_version: str | None = None,
    limit: int = 1,
) -> list[dict]:
    """Retrieve the N most recent feature snapshots for a symbol."""
    version = feature_version or settings.feature_version
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT time, features
                FROM feature_store
                WHERE symbol = :symbol
                  AND exchange = :exchange
                  AND interval = :interval
                  AND feature_version = :feature_version
                ORDER BY time DESC
                LIMIT :limit
            """),
            {"symbol": symbol, "exchange": exchange, "interval": interval,
             "feature_version": version, "limit": limit},
        )
        rows = result.fetchall()
    return [{"time": r[0], **json.loads(r[1])} for r in rows]
