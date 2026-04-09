"""
quality/checker.py — Data quality anomaly detection.
Detects stale ticks, outlier prices, and missing bars.
Logs issues to the data_quality_log table and optionally alerts.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from loguru import logger
from sqlalchemy import text

from data.db import get_session

IST = ZoneInfo("Asia/Kolkata")


class DataQualityChecker:
    """
    Handles data quality checks and anomaly detection.
    """

    def __init__(self):
        pass

    async def log_issue(self, **kwargs):
        """Wrapper for log_quality_issue."""
        await log_quality_issue(**kwargs)

    def detect_outliers(self, df: pd.DataFrame, z_threshold: float = 3.0) -> pd.DataFrame:
        """Wrapper for detect_outlier_prices."""
        return detect_outlier_prices(df, z_threshold)

    def detect_missing(self, df: pd.DataFrame, interval: str) -> list[datetime]:
        """Wrapper for detect_missing_bars."""
        return detect_missing_bars(df, interval)

    async def check_stale(self, symbol: str, exchange: str, last_tick: datetime) -> bool:
        """Wrapper for check_stale_feed."""
        return await check_stale_feed(symbol, exchange, last_tick)

    async def validate_df(self, df: pd.DataFrame, symbol: str, exchange: str, interval: str, source: str) -> pd.DataFrame:
        """Wrapper for validate_ohlcv_frame."""
        return await validate_ohlcv_frame(df, symbol, exchange, interval, source)


async def log_quality_issue(
    issue_type: str,
    severity: str = "WARNING",
    symbol: str | None = None,
    exchange: str | None = None,
    source: str | None = None,
    interval: str | None = None,
    affected_time: datetime | None = None,
    detail: str | None = None,
) -> None:
    if affected_time is not None:
        # Localize naive timestamps to UTC
        if hasattr(affected_time, "tzinfo") and affected_time.tzinfo is None:
            if hasattr(affected_time, "tz_localize"):
                affected_time = affected_time.tz_localize("UTC")
            else:
                affected_time = affected_time.replace(tzinfo=ZoneInfo("UTC"))
        
        # Convert pandas Timestamp to python datetime
        if hasattr(affected_time, "to_pydatetime"):
            affected_time = affected_time.to_pydatetime()

    async with get_session() as session:
        await session.execute(
            text("""
                INSERT INTO data_quality_log
                    (symbol, exchange, source, issue_type, severity, interval, affected_time, detail)
                VALUES (:symbol, :exchange, :source, :issue_type, :severity, :interval, :affected_time, :detail)
            """),
            dict(
                symbol=symbol, exchange=exchange, source=source,
                issue_type=issue_type, severity=severity, interval=interval,
                affected_time=affected_time, detail=detail,
            ),
        )
    logger.warning(f"[data_quality] {severity} | {issue_type} | {symbol} | {detail}")


def detect_outlier_prices(df: pd.DataFrame, z_threshold: float = 3.0) -> pd.DataFrame:
    """
    Flag bars where close price deviates more than z_threshold standard
    deviations from the rolling 20-bar mean.
    Returns DataFrame with 'is_outlier' column added.
    """
    df = df.copy()
    rolling_mean = df["close"].rolling(window=20, min_periods=5).mean()
    rolling_std  = df["close"].rolling(window=20, min_periods=5).std()
    z_scores = (df["close"] - rolling_mean).abs() / rolling_std.replace(0, float("nan"))
    df["is_outlier"] = z_scores > z_threshold
    n_outliers = df["is_outlier"].sum()
    if n_outliers:
        logger.warning(f"[quality] Detected {n_outliers} outlier price bars")
    return df


def detect_missing_bars(
    df: pd.DataFrame,
    interval: str,
    market_open: str = "09:15",
    market_close: str = "15:30",
) -> list[datetime]:
    """
    Detect missing bars in an intraday OHLCV series.
    Returns list of expected-but-missing timestamps.
    NOTE: Only meaningful for intraday intervals.
    """
    if interval not in ("1min", "5min", "15min", "30min", "1h"):
        return []

    freq_map = {"1min": "1min", "5min": "5min", "15min": "15min", "30min": "30min", "1h": "1h"}
    freq = freq_map.get(interval)
    if not freq or df.empty:
        return []

    df = df.sort_values("time")
    dates = df["time"].dt.date.unique()
    missing = []

    for d in dates:
        expected = pd.date_range(
            start=f"{d} {market_open}",
            end=f"{d} {market_close}",
            freq=freq,
            tz="Asia/Kolkata",
        )
        actual = set(df[df["time"].dt.date == d]["time"])
        missing.extend([ts for ts in expected if ts not in actual])

    if missing:
        logger.warning(f"[quality] {len(missing)} missing bars detected")
    return missing


async def check_stale_feed(
    symbol: str,
    exchange: str,
    last_tick_time: datetime,
    stale_threshold_minutes: int = 5,
) -> bool:
    """
    Return True (and log to DB) if the last tick is older than threshold
    during trading hours (09:15–15:30 IST, Mon–Fri).
    """
    now = datetime.now(tz=IST)
    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    if not (market_open <= now <= market_close) or now.weekday() >= 5:
        return False  # outside trading hours

    age = now - last_tick_time
    if age > timedelta(minutes=stale_threshold_minutes):
        await log_quality_issue(
            issue_type="STALE_TICK",
            severity="CRITICAL",
            symbol=symbol,
            exchange=exchange,
            affected_time=last_tick_time,
            detail=f"Last tick {age.total_seconds():.0f}s ago (threshold {stale_threshold_minutes*60}s)",
        )
        return True
    return False


async def validate_ohlcv_frame(
    df: pd.DataFrame,
    symbol: str,
    exchange: str,
    interval: str,
    source: str,
) -> pd.DataFrame:
    """
    Run all quality checks on a fetched OHLCV DataFrame.
    Logs issues to DB and returns the DataFrame with 'is_outlier' column.
    Does NOT drop outliers — let downstream decide.
    """
    if df.empty:
        await log_quality_issue(
            issue_type="MISSING_BAR",
            severity="WARNING",
            symbol=symbol,
            exchange=exchange,
            source=source,
            interval=interval,
            affected_time=datetime.now(tz=IST),  # Use current time when no data available
            detail="fetch returned empty DataFrame",
        )
        return df

    # Outlier detection
    df = detect_outlier_prices(df)
    for _, row in df[df["is_outlier"]].iterrows():
        await log_quality_issue(
            issue_type="OUTLIER_PRICE",
            severity="WARNING",
            symbol=symbol,
            exchange=exchange,
            source=source,
            interval=interval,
            affected_time=row["time"],
            detail=f"close={row['close']:.2f} flagged as outlier (>3σ from 20-bar mean)",
        )

    # Missing bar detection
    missing = detect_missing_bars(df, interval)
    if missing:
        for ts in missing[:10]:  # log first 10 to avoid spam
            await log_quality_issue(
                issue_type="MISSING_BAR",
                severity="WARNING",
                symbol=symbol,
                exchange=exchange,
                source=source,
                interval=interval,
                affected_time=ts,
                detail=f"Expected bar at {ts} not found in feed",
            )

    return df
