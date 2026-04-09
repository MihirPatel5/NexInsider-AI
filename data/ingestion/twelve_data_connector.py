"""
data/ingestion/twelve_data_connector.py — Backup OHLCV feed via TwelveData API.
"""
import pandas as pd
import requests
from datetime import date
from loguru import logger
from data.config import settings
from data.ingestion.base import BaseConnector, Quote

class TwelveDataConnector(BaseConnector):
    def __init__(self):
        self.api_key = settings.twelve_data_api_key
        self.base_url = "https://api.twelvedata.com"

    def fetch_ohlcv(
        self, 
        symbol: str, 
        exchange: str, 
        interval: str, 
        start: date, 
        end: date
    ) -> pd.DataFrame:
        """
        Fetch OHLCV from TwelveData for India stocks.
        TwelveData symbol format for NSE: SYMBOL:NSE
        """
        try:
            td_symbol = f"{symbol}:{exchange}"
            # Map intervals: 1d -> 1day, 1min -> 1min
            td_interval = "1day" if interval == "1d" else interval
            
            logger.info(f"[twelvedata] Fetching {td_symbol} {interval}")
            
            params = {
                "symbol": td_symbol,
                "interval": td_interval,
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "apikey": self.api_key,
                "outputsize": 5000,
                "order": "ASC"
            }
            
            resp = requests.get(f"{self.base_url}/time_series", params=params)
            data = resp.json()
            
            if "values" not in data:
                logger.warning(f"[twelvedata] No values for {td_symbol}: {data.get('message', 'Unknown error')}")
                return pd.DataFrame()
                
            df = pd.DataFrame(data["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.rename(columns={"datetime": "time"})
            
            # Ensure numeric types
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col])
                
            return df
        except Exception as e:
            logger.error(f"[twelvedata] Failed for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        # Quote implementation if needed
        return Quote(symbol=symbol, price=0.0, exchange=exchange)
