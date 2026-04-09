"""
data/ingestion/alpha_vantage_connector.py — Backup OHLCV feed via AlphaVantage API.
"""
import pandas as pd
import requests
from datetime import date
from loguru import logger
from data.config import settings
from data.ingestion.base import BaseConnector, Quote

class AlphaVantageConnector(BaseConnector):
    def __init__(self):
        self.api_key = settings.alpha_vantage_api_key
        self.base_url = "https://www.alphavantage.co/query"

    def fetch_ohlcv(
        self, 
        symbol: str, 
        exchange: str, 
        interval: str, 
        start: date, 
        end: date
    ) -> pd.DataFrame:
        """
        Fetch OHLCV from Alpha Vantage for India stocks.
        Alpha Vantage symbol format for NSE: NSE:SYMBOL
        """
        try:
            # Alpha Vantage uses TICKER for US, and EXCHANGE:TICKER for others
            av_symbol = f"{exchange}:{symbol}"
            
            # Map intervals: 1d -> TIME_SERIES_DAILY
            if interval != "1d":
                logger.warning(f"[alphavantage] Intraday interval {interval} not yet implemented in this connector")
                return pd.DataFrame()
                
            logger.info(f"[alphavantage] Fetching {av_symbol}")
            
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": av_symbol,
                "apikey": self.api_key,
                "outputsize": "full"
            }
            
            resp = requests.get(self.base_url, params=params)
            data = resp.json()
            
            key = "Time Series (Daily)"
            if key not in data:
                logger.warning(f"[alphavantage] No data for {av_symbol}: {data.get('Note', 'Rate limited or invalid symbol')}")
                return pd.DataFrame()
                
            df = pd.DataFrame.from_dict(data[key], orient="index")
            df.index = pd.to_datetime(df.index)
            df = df.reset_index().rename(columns={"index": "time"})
            
            # Column mapping: "1. open", "2. high", etc.
            df = df.rename(columns={
                "1. open": "open",
                "2. high": "high",
                "3. low": "low",
                "4. close": "close",
                "5. volume": "volume"
            })
            
            # Filter by date range
            df = df[(df["time"].dt.date >= start) & (df["time"].dt.date <= end)]
            
            # Ensure numeric
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col])
                
            return df.sort_values("time").reset_index(drop=True)
        except Exception as e:
            logger.error(f"[alphavantage] Failed for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        return Quote(symbol=symbol, price=0.0, exchange=exchange)
