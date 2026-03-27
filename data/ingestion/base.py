"""
ingestion/base.py — Abstract base class for all data feed connectors.
Each connector must implement fetch_ohlcv and fetch_quote.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd


@dataclass
class Quote:
    symbol: str
    exchange: str
    ltp: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    oi: Optional[int] = None


class BaseConnector(ABC):
    source_name: str = "base"

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """
        Return a DataFrame with columns:
        [time, symbol, exchange, interval, open, high, low, close, volume]
        'time' must be timezone-aware (IST).
        """

    @abstractmethod
    def fetch_quote(self, symbol: str, exchange: str) -> Quote:
        """Return the current best bid/ask/LTP for a symbol."""

    def validate_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assert required columns exist and coerce types."""
        required = ["time", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"[{self.source_name}] Missing OHLCV columns: {missing}")
        df["symbol"] = df.get("symbol", "")
        df["exchange"] = df.get("exchange", "NSE")
        df["interval"] = df.get("interval", "1d")
        df["source"] = self.source_name
        return df
