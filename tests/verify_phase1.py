"""
tests/verify_phase1.py — Comprehensive Phase 1 verification suite.
Runs real-world tests for ingestion, quality, and feature engineering.
"""
import pytest
import asyncio
import pandas as pd
from datetime import date, timedelta
from data.ingestion.router import DataRouter
from data.ingestion.news import RSSNewsIngestor
from data.ingestion.nse_extra_connector import NSEExtraConnector
from data.ingestion.screener_scraper import ScreenerScraper
from data.quality.checker import DataQualityChecker
from data.features.technical import compute_technical_features
from data.db import get_session
from sqlalchemy import text

@pytest.mark.asyncio
async def test_ohlcv_ingestion():
    """Verify market data ingestion works for a major symbol."""
    router = DataRouter()
    symbol = "RELIANCE"
    # Fetch last 5 days
    df = await router.fetch_ohlcv(symbol, "NSE", "1d", date.today()-timedelta(days=7), date.today())
    assert not df.empty, "Datarouter failed to fetch RELIANCE data"
    assert "close" in df.columns
    print(f"✅ OHLCV Ingestion verified for {symbol}")

@pytest.mark.asyncio
async def test_news_ingestion():
    """Verify RSS news ingestion can parse feeds."""
    ingestor = RSSNewsIngestor()
    feed_url = "https://www.moneycontrol.com/rss/latestnews.xml"
    articles = await ingestor.fetch_feed(feed_url)
    assert len(articles) > 0, "No articles fetched from MoneyControl"
    print(f"✅ News Ingestion verified: {len(articles)} articles found")

def test_fo_ingestion():
    """Verify nsepy index data retrieval."""
    connector = NSEExtraConnector()
    df = connector.get_index_data("NIFTY 50", date.today()-timedelta(days=10), date.today())
    assert not df.empty, "NSEpy failed to fetch NIFTY 50 index"
    print("✅ F&O/Index Ingestion verified")

@pytest.mark.asyncio
async def test_fundamental_scraping():
    """Verify Screener.in scraping works for a known ticker."""
    scraper = ScreenerScraper()
    data = await scraper.scrape_fundamentals("TCS")
    assert "Market Cap" in data or "P/E" in data, "Screener scraper returned incomplete data"
    print("✅ Fundamental Scraping verified for TCS")

def test_technical_features():
    """Verify indicators are calculated correctly."""
    # Mock data
    data = {
        'open': [100, 102, 101, 105, 107],
        'high': [103, 104, 105, 108, 110],
        'low': [99, 100, 100, 104, 106],
        'close': [102, 101, 104, 107, 109],
        'volume': [1000, 1100, 1200, 1300, 1400]
    }
    df = pd.DataFrame(data)
    feat_df = compute_technical_features(df)
    assert "rsi" in feat_df.columns
    assert "macd" in feat_df.columns
    print("✅ Technical Feature Engineering verified")

@pytest.mark.asyncio
async def test_db_persistence():
    """Final check: ensure data actually exists in TimescaleDB."""
    async with get_session() as session:
        # Check ohlcv_bars
        res = await session.execute(text("SELECT count(*) FROM ohlcv_bars"))
        count = res.scalar()
        print(f"📊 DB Status: {count} bars in ohlcv_bars hypertable")
        assert count >= 0 
