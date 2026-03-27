"""
ingestion/router.py — Smart data router with primary/fallback logic.
Tries jugaad first for daily data, falls back to yfinance on error.
For intraday intervals, uses yfinance directly.
"""
from datetime import date
from typing import Literal

import pandas as pd
from loguru import logger

from data.ingestion.base import BaseConnector, Quote
from data.ingestion.jugaad_connector import JugaadConnector
from data.ingestion.yfinance_connector import YfinanceConnector

INTRADAY_INTERVALS = {"1min", "2min", "5min", "15min", "30min", "1h"}


class DataRouter:
    """
    Routes data requests to the most appropriate connector.
    - Daily/weekly: jugaad-data (primary) → yfinance (fallback)
    - Intraday: yfinance (only current option)
    """

    def __init__(self):
        self._jugaad = JugaadConnector()
        self._yfinance = YfinanceConnector()

    def fetch_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        if interval in INTRADAY_INTERVALS:
            logger.debug(f"[router] Intraday → yfinance for {symbol} {interval}")
            return self._yfinance.fetch_ohlcv(symbol, exchange, interval, start, end)

        # Daily / weekly — try jugaad first
        try:
            df = self._jugaad.fetch_ohlcv(symbol, exchange, interval, start, end)
            if not df.empty:
                return df
            logger.warning(f"[router] jugaad returned empty for {symbol}, trying yfinance")
        except Exception as exc:
            logger.warning(f"[router] jugaad failed for {symbol}: {exc}. Falling back to yfinance")

        return self._yfinance.fetch_ohlcv(symbol, exchange, interval, start, end)

    def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        try:
            return self._jugaad.fetch_quote(symbol, exchange)
        except Exception as exc:
            logger.warning(f"[router] jugaad quote failed for {symbol}: {exc}. Trying yfinance")
            return self._yfinance.fetch_quote(symbol, exchange)


# Singleton router instance
router = DataRouter()
