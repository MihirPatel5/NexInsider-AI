"""
data/ingestion/mock_connector.py — Mock connector for verification in restricted environments.
"""
import pandas as pd
import numpy as np
from datetime import date, timedelta
from loguru import logger
from data.ingestion.base import BaseConnector, Quote

class MockConnector(BaseConnector):
    """
    Returns realistic synthetic OHLCV data.
    Ensures that verification tests can run even if all APIs fail.
    """
    def fetch_ohlcv(
        self, 
        symbol: str, 
        exchange: str, 
        interval: str, 
        start: date, 
        end: date
    ) -> pd.DataFrame:
        logger.info(f"[mock] Generating synthetic data for {symbol} ({start} → {end})")
        
        # Create a range of dates and localize to UTC
        dates = pd.date_range(start, end, freq="B", tz="UTC") # Business days
        if len(dates) == 0:
            return pd.DataFrame()
            
        n = len(dates)
        # Generate random walk prices around 1000
        closes = 1000 + np.cumsum(np.random.randn(n) * 10)
        opens = closes + np.random.randn(n) * 2
        highs = np.maximum(opens, closes) + np.random.rand(n) * 5
        lows = np.minimum(opens, closes) - np.random.rand(n) * 5
        volumes = np.random.randint(100000, 1000000, size=n)
        
        df = pd.DataFrame({
            "time": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "symbol": [symbol] * n,
            "exchange": [exchange] * n,
            "interval": [interval] * n,
            "source": ["mock"] * n
        })
        
        return df

    def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        return Quote(symbol=symbol, price=1000.0, exchange=exchange)
