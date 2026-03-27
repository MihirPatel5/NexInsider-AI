"""
data/ingestion/nse_extra_connector.py — NSE F&O, Indices, and Market Status.
Uses nsepy and nsetools for data not covered by jugaad-data.
"""
from typing import Dict, List, Optional
import pandas as pd
from nsepy import get_history, get_index_pe_history
from nsetools import Nse
from datetime import date, timedelta
from loguru import logger

class NSEExtraConnector:
    def __init__(self):
        self.nse_tools = Nse()

    def get_option_chain(self, symbol: str, expiry: date = None) -> pd.DataFrame:
        """Fetch option chain for a given symbol and expiry."""
        try:
            # Note: nsepy's get_history for options is often used for historical, 
            # while nsetools is better for live. 
            # For this production system, we focus on structure.
            logger.info(f"[nse_extra] Fetching option chain for {symbol}")
            # Placeholder for actual option chain logic as nsepy/nsetools 
            # interfaces can be flaky.
            return pd.DataFrame() 
        except Exception as e:
            logger.error(f"[nse_extra] Failed to fetch option chain for {symbol}: {e}")
            return pd.DataFrame()

    def get_index_data(self, index_name: str, start: date, end: date) -> pd.DataFrame:
        """Fetch historical index data (e.g., NIFTY 50)."""
        try:
            logger.info(f"[nse_extra] Fetching index history for {index_name}")
            df = get_history(symbol=index_name, start=start, end=end, index=True)
            return df
        except Exception as e:
            logger.error(f"[nse_extra] Failed to fetch index data for {index_name}: {e}")
            return pd.DataFrame()

    def get_vix_data(self, start: date, end: date) -> pd.DataFrame:
        """Fetch India VIX history."""
        try:
            logger.info("[nse_extra] Fetching India VIX")
            df = get_history(symbol="INDIAVIX", start=start, end=end, index=True)
            return df
        except Exception as e:
            logger.error(f"[nse_extra] Failed to fetch VIX data: {e}")
            return pd.DataFrame()

    def get_market_status(self) -> dict:
        """Get current NSE market status (OPEN/CLOSED)."""
        try:
            return self.nse_tools.get_market_status()
        except Exception:
            return {"status": "UNKNOWN"}

    def get_top_gainers(self) -> list:
        """Get live top gainers."""
        try:
            return self.nse_tools.get_top_gainers()
        except Exception:
            return []
