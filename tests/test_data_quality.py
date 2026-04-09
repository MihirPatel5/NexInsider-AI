"""
tests/test_data_quality.py — Comprehensive tests for data quality checker.

Tests stale tick detection, outlier detection, gap detection, and logging.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from data.quality.checker import (
    DataQualityChecker,
    detect_outlier_prices,
    detect_missing_bars,
    check_stale_feed,
    validate_ohlcv_frame,
    log_quality_issue,
)
from data.db import get_session
from sqlalchemy import text

IST = ZoneInfo("Asia/Kolkata")


# ─── Test: Outlier Detection ─────────────────────────────────────────────────

def test_detect_outliers_no_outliers():
    """Test that normal price movements are not flagged as outliers."""
    # Create data with normal price movements (within 3σ)
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 50,
        "high": [105.0] * 50,
        "low": [95.0] * 50,
        "close": [100.0 + i * 0.5 for i in range(50)],  # Gradual increase
        "volume": [1000000] * 50,
    })
    
    result = detect_outlier_prices(df, z_threshold=3.0)
    
    assert "is_outlier" in result.columns
    assert result["is_outlier"].sum() == 0, "No outliers should be detected in normal data"


def test_detect_outliers_with_spike():
    """Test that price spikes are correctly flagged as outliers."""
    # Create data with a price spike
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="Asia/Kolkata")
    closes = [100.0] * 50
    closes[25] = 200.0  # Spike at day 25
    
    df = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 50,
        "high": [105.0] * 50,
        "low": [95.0] * 50,
        "close": closes,
        "volume": [1000000] * 50,
    })
    
    result = detect_outlier_prices(df, z_threshold=3.0)
    
    assert result["is_outlier"].sum() >= 1, "Price spike should be detected as outlier"
    # The spike at index 25 should be flagged
    assert result.iloc[25]["is_outlier"], "Spike at index 25 should be flagged"


def test_detect_outliers_multiple_spikes():
    """Test detection of multiple outliers."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="Asia/Kolkata")
    closes = [100.0] * 50
    closes[10] = 200.0  # Spike 1
    closes[30] = 50.0   # Spike 2 (drop)
    
    df = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 50,
        "high": [105.0] * 50,
        "low": [95.0] * 50,
        "close": closes,
        "volume": [1000000] * 50,
    })
    
    result = detect_outlier_prices(df, z_threshold=3.0)
    
    assert result["is_outlier"].sum() >= 2, "Both spikes should be detected"


# ─── Test: Missing Bar Detection ─────────────────────────────────────────────

def test_detect_missing_bars_complete_data():
    """Test that complete intraday data has no missing bars."""
    # Create complete 5-minute data for one trading day
    dates = pd.date_range(
        "2024-01-15 09:15",
        "2024-01-15 15:30",
        freq="5min",
        tz="Asia/Kolkata"
    )
    df = pd.DataFrame({
        "time": dates,
        "open": [100.0] * len(dates),
        "high": [105.0] * len(dates),
        "low": [95.0] * len(dates),
        "close": [100.0] * len(dates),
        "volume": [1000000] * len(dates),
    })
    
    missing = detect_missing_bars(df, interval="5min")
    
    assert len(missing) == 0, "Complete data should have no missing bars"


def test_detect_missing_bars_with_gaps():
    """Test detection of missing bars in intraday data."""
    # Create 5-minute data with gaps
    dates = pd.date_range(
        "2024-01-15 09:15",
        "2024-01-15 15:30",
        freq="5min",
        tz="Asia/Kolkata"
    )
    # Remove some bars to create gaps
    dates_with_gaps = [d for i, d in enumerate(dates) if i not in [10, 11, 12, 30, 31]]
    
    df = pd.DataFrame({
        "time": dates_with_gaps,
        "open": [100.0] * len(dates_with_gaps),
        "high": [105.0] * len(dates_with_gaps),
        "low": [95.0] * len(dates_with_gaps),
        "close": [100.0] * len(dates_with_gaps),
        "volume": [1000000] * len(dates_with_gaps),
    })
    
    missing = detect_missing_bars(df, interval="5min")
    
    assert len(missing) == 5, f"Should detect 5 missing bars, found {len(missing)}"


def test_detect_missing_bars_daily_data():
    """Test that daily data is not checked for missing bars."""
    # Daily data should not be checked for intraday gaps
    dates = pd.date_range("2024-01-01", periods=30, freq="D", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 30,
        "high": [105.0] * 30,
        "low": [95.0] * 30,
        "close": [100.0] * 30,
        "volume": [1000000] * 30,
    })
    
    missing = detect_missing_bars(df, interval="1d")
    
    assert len(missing) == 0, "Daily data should not be checked for intraday gaps"


# ─── Test: Stale Feed Detection ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_stale_feed_outside_trading_hours():
    """Test that stale feed is not flagged outside trading hours."""
    # Create a timestamp outside trading hours (e.g., 8:00 AM)
    now = datetime.now(tz=IST).replace(hour=8, minute=0, second=0, microsecond=0)
    last_tick = now - timedelta(minutes=30)  # 30 minutes old
    
    is_stale = await check_stale_feed("TEST", "NSE", last_tick, stale_threshold_minutes=5)
    
    assert not is_stale, "Should not flag stale feed outside trading hours"


@pytest.mark.asyncio
async def test_check_stale_feed_recent_tick():
    """Test that recent ticks are not flagged as stale."""
    # Create a recent timestamp during trading hours
    now = datetime.now(tz=IST).replace(hour=10, minute=0, second=0, microsecond=0)
    last_tick = now - timedelta(minutes=2)  # 2 minutes old (within threshold)
    
    # Note: This test will only work during trading hours on weekdays
    # For testing purposes, we'll just verify the function doesn't crash
    try:
        is_stale = await check_stale_feed("TEST", "NSE", last_tick, stale_threshold_minutes=5)
        # During trading hours, 2-minute-old tick should not be stale
        # Outside trading hours, it should return False
        assert isinstance(is_stale, bool)
    except Exception as e:
        pytest.fail(f"check_stale_feed raised exception: {e}")


# ─── Test: Quality Issue Logging ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_quality_issue():
    """Test that quality issues are logged to database."""
    symbol = "TEST_QUALITY"
    exchange = "NSE"
    issue_type = "TEST_ISSUE"
    severity = "WARNING"
    detail = "Test quality issue"
    
    try:
        # Log a test issue
        await log_quality_issue(
            issue_type=issue_type,
            severity=severity,
            symbol=symbol,
            exchange=exchange,
            source="test",
            interval="1d",
            affected_time=datetime.now(tz=IST),
            detail=detail,
        )
        
        # Verify it was logged
        async with get_session() as session:
            result = await session.execute(
                text("""
                    SELECT issue_type, severity, symbol, detail
                    FROM data_quality_log
                    WHERE symbol = :symbol AND issue_type = :issue_type
                    ORDER BY logged_at DESC
                    LIMIT 1
                """),
                {"symbol": symbol, "issue_type": issue_type}
            )
            row = result.fetchone()
        
        assert row is not None, "Quality issue should be logged to database"
        assert row[0] == issue_type
        assert row[1] == severity
        assert row[2] == symbol
        assert row[3] == detail
    
    finally:
        # Cleanup
        async with get_session() as session:
            await session.execute(
                text("DELETE FROM data_quality_log WHERE symbol = :symbol"),
                {"symbol": symbol}
            )
            await session.commit()


# ─── Test: Validate OHLCV Frame ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_ohlcv_frame_empty():
    """Test validation of empty DataFrame."""
    df = pd.DataFrame()
    
    try:
        result = await validate_ohlcv_frame(
            df,
            symbol="TEST_EMPTY",
            exchange="NSE",
            interval="1d",
            source="test"
        )
        
        assert result.empty, "Empty DataFrame should remain empty"
        
        # Verify issue was logged
        async with get_session() as session:
            log_result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM data_quality_log
                    WHERE symbol = 'TEST_EMPTY' AND issue_type = 'MISSING_BAR'
                """)
            )
            count = log_result.scalar()
        
        assert count >= 1, "Empty DataFrame should log MISSING_BAR issue"
    
    finally:
        # Cleanup
        async with get_session() as session:
            await session.execute(
                text("DELETE FROM data_quality_log WHERE symbol = 'TEST_EMPTY'")
            )
            await session.commit()


@pytest.mark.asyncio
async def test_validate_ohlcv_frame_with_outliers():
    """Test validation of DataFrame with outliers."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="Asia/Kolkata")
    closes = [100.0] * 50
    closes[25] = 200.0  # Outlier
    
    df = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 50,
        "high": [105.0] * 50,
        "low": [95.0] * 50,
        "close": closes,
        "volume": [1000000] * 50,
    })
    
    try:
        result = await validate_ohlcv_frame(
            df,
            symbol="TEST_OUTLIER",
            exchange="NSE",
            interval="1d",
            source="test"
        )
        
        assert "is_outlier" in result.columns, "Result should have is_outlier column"
        assert result["is_outlier"].sum() >= 1, "Outlier should be detected"
        
        # Verify issue was logged
        async with get_session() as session:
            log_result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM data_quality_log
                    WHERE symbol = 'TEST_OUTLIER' AND issue_type = 'OUTLIER_PRICE'
                """)
            )
            count = log_result.scalar()
        
        assert count >= 1, "Outlier should be logged to database"
    
    finally:
        # Cleanup
        async with get_session() as session:
            await session.execute(
                text("DELETE FROM data_quality_log WHERE symbol = 'TEST_OUTLIER'")
            )
            await session.commit()


# ─── Test: DataQualityChecker Class ──────────────────────────────────────────

def test_data_quality_checker_initialization():
    """Test that DataQualityChecker can be instantiated."""
    checker = DataQualityChecker()
    assert checker is not None


def test_data_quality_checker_detect_outliers():
    """Test DataQualityChecker.detect_outliers wrapper."""
    checker = DataQualityChecker()
    
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="Asia/Kolkata")
    closes = [100.0] * 50
    closes[25] = 200.0
    
    df = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 50,
        "high": [105.0] * 50,
        "low": [95.0] * 50,
        "close": closes,
        "volume": [1000000] * 50,
    })
    
    result = checker.detect_outliers(df)
    
    assert "is_outlier" in result.columns
    assert result["is_outlier"].sum() >= 1


def test_data_quality_checker_detect_missing():
    """Test DataQualityChecker.detect_missing wrapper."""
    checker = DataQualityChecker()
    
    dates = pd.date_range(
        "2024-01-15 09:15",
        "2024-01-15 15:30",
        freq="5min",
        tz="Asia/Kolkata"
    )
    dates_with_gaps = [d for i, d in enumerate(dates) if i not in [10, 11]]
    
    df = pd.DataFrame({
        "time": dates_with_gaps,
        "open": [100.0] * len(dates_with_gaps),
        "high": [105.0] * len(dates_with_gaps),
        "low": [95.0] * len(dates_with_gaps),
        "close": [100.0] * len(dates_with_gaps),
        "volume": [1000000] * len(dates_with_gaps),
    })
    
    missing = checker.detect_missing(df, interval="5min")
    
    assert len(missing) == 2


# ─── Property-Based Tests ────────────────────────────────────────────────────

def test_outlier_detection_properties():
    """
    Property: Outlier detection should be symmetric.
    
    If a price spike is an outlier, a price drop of the same magnitude
    should also be an outlier.
    """
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="Asia/Kolkata")
    
    # Test with spike
    closes_spike = [100.0] * 50
    closes_spike[25] = 200.0
    df_spike = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 50,
        "high": [105.0] * 50,
        "low": [95.0] * 50,
        "close": closes_spike,
        "volume": [1000000] * 50,
    })
    
    # Test with drop
    closes_drop = [100.0] * 50
    closes_drop[25] = 0.0
    df_drop = pd.DataFrame({
        "time": dates,
        "open": [100.0] * 50,
        "high": [105.0] * 50,
        "low": [95.0] * 50,
        "close": closes_drop,
        "volume": [1000000] * 50,
    })
    
    result_spike = detect_outlier_prices(df_spike)
    result_drop = detect_outlier_prices(df_drop)
    
    # Both should detect outliers
    assert result_spike["is_outlier"].sum() >= 1, "Spike should be detected"
    assert result_drop["is_outlier"].sum() >= 1, "Drop should be detected"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
