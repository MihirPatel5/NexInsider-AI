"""
ingestion/router.py — Smart data router with primary/fallback logic.
Tries jugaad first for daily data, falls back to yfinance on error.
For intraday intervals, uses yfinance directly.
"""
from datetime import date
from typing import Literal

import asyncio
import pandas as pd
from loguru import logger

from data.ingestion.base import BaseConnector, Quote
from data.ingestion.jugaad_connector import JugaadConnector
from data.ingestion.yfinance_connector import YfinanceConnector
from data.ingestion.twelve_data_connector import TwelveDataConnector
from data.ingestion.alpha_vantage_connector import AlphaVantageConnector
from data.ingestion.nse_extra_connector import NSEExtraConnector
from data.ingestion.mock_connector import MockConnector

INTRADAY_INTERVALS = {"1min", "2min", "5min", "15min", "30min", "1h"}


class DataRouter:
    """
    Routes data requests to the most appropriate connector.
    Fallbacks: jugaad → yfinance → TwelveData → AlphaVantage → Mock (Final resort)
    """

    def __init__(self):
        self._jugaad = JugaadConnector()
        self._yfinance = YfinanceConnector()
        self._twelve = TwelveDataConnector()
        self._alpha = AlphaVantageConnector()
        self._extra = NSEExtraConnector()
        self._mock = MockConnector()

    async def fetch_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        # Special handling for Indices
        indices = {"NIFTY 50", "NIFTY50", "NIFTY BANK", "BANKNIFTY", "NIFTY IT", "INDIAVIX"}
        if symbol.upper() in indices:
            logger.info(f"[router] Index detected: {symbol} → Using NSEExtra (Index) fetch")
            df = await asyncio.to_thread(self._extra.get_index_data, symbol, start, end)
            if not df.empty:
                df["source"] = "nse_extra"
                return df

        if interval in INTRADAY_INTERVALS:
            logger.debug(f"[router] Intraday → yfinance for {symbol} {interval}")
            return await asyncio.to_thread(self._yfinance.fetch_ohlcv, symbol, exchange, interval, start, end)

        # Force Mock for MOCK symbols or CRYPTO exchange (for testing)
        if symbol.upper().startswith("MOCK_") or exchange.upper() == "CRYPTO":
            logger.info(f"[router] Mock detected: {symbol} → Using MockConnector")
            return await asyncio.to_thread(self._mock.fetch_ohlcv, symbol, exchange, interval, start, end)

        # TEMPORARY: Skip jugaad (too slow/unreliable), try yfinance first
        logger.debug(f"[router] Using yfinance for {symbol} (jugaad disabled)")
        df = await asyncio.to_thread(self._yfinance.fetch_ohlcv, symbol, exchange, interval, start, end)
        if not df.empty:
            return df

        # Daily / weekly — try jugaad as fallback (commented out for now)
        # try:
        #     df = await asyncio.to_thread(self._jugaad.fetch_ohlcv, symbol, exchange, interval, start, end)
        #     if not df.empty:
        #         return df
        #     logger.warning(f"[router] jugaad returned empty for {symbol}, trying yfinance")
        # except Exception as exc:
        #     logger.warning(f"[router] jugaad failed for {symbol}: {exc}. Falling back to yfinance")

        logger.debug(f"[router] Falling back to TwelveData for {symbol}")
        df = await asyncio.to_thread(self._twelve.fetch_ohlcv, symbol, exchange, interval, start, end)
        if not df.empty:
            return df

        logger.debug(f"[router] Falling back to AlphaVantage for {symbol}")
        df = await asyncio.to_thread(self._alpha.fetch_ohlcv, symbol, exchange, interval, start, end)
        if not df.empty:
            return df

        logger.warning(f"[router] All real sources failed for {symbol} - NO MOCK FALLBACK FOR BACKTESTING")
        return pd.DataFrame()  # Return empty instead of mock data

    async def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        try:
            return await asyncio.to_thread(self._jugaad.fetch_quote, symbol, exchange)
        except Exception as exc:
            logger.warning(f"[router] jugaad quote failed for {symbol}: {exc}. Trying yfinance")
            return await asyncio.to_thread(self._yfinance.fetch_quote, symbol, exchange)


# Singleton router instance
router = DataRouter()
