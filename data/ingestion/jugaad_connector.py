"""
ingestion/jugaad_connector.py — Primary NSE/BSE data connector via jugaad-data.
Most reliable source for Indian market historical + live data.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
from jugaad_data.nse import NSELive, stock_df
from loguru import logger

from data.ingestion.base import BaseConnector, Quote

IST = ZoneInfo("Asia/Kolkata")

INTERVAL_MAP = {
    "1d": "1",
    "1w": "1",
}


class JugaadConnector(BaseConnector):
    source_name = "jugaad"

    def __init__(self):
        self._live = NSELive()

    def fetch_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV from jugaad-data.
        Currently supports daily ('1d') data — best option for NSE.
        For intraday, fall back to yfinance connector.
        """
        if interval not in ("1d", "1w"):
            raise ValueError(
                f"JugaadConnector supports intervals: 1d, 1w. Got: {interval}. "
                "Use YfinanceConnector for intraday."
            )

        logger.info(f"[jugaad] Fetching {symbol} ({exchange}) {interval} {start}→{end}")
        try:
            df = stock_df(symbol=symbol, from_date=start, to_date=end, series="EQ")
        except Exception as exc:
            logger.error(f"[jugaad] Failed for {symbol}: {exc}")
            raise

        if df.empty:
            logger.warning(f"[jugaad] No data returned for {symbol}")
            return pd.DataFrame()

        df = df.rename(
            columns={
                "DATE": "time",
                "OPEN": "open",
                "HIGH": "high",
                "LOW": "low",
                "close": "close",
                "CLOSE": "close",
                "VOLUME": "volume",
            }
        )
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(IST)
        df["symbol"] = symbol
        df["exchange"] = exchange
        df["interval"] = interval
        df = df[["time", "symbol", "exchange", "interval", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("time").reset_index(drop=True)
        return self.validate_ohlcv(df)

    def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        """Fetch live quote using NSELive."""
        try:
            data = self._live.equities(symbol)
            return Quote(
                symbol=symbol,
                exchange=exchange,
                ltp=float(data.get("lastPrice", 0)),
                volume=int(data.get("totalTradedVolume", 0)),
                bid=float(data.get("buyPrice1", 0) or 0),
                ask=float(data.get("sellPrice1", 0) or 0),
            )
        except Exception as exc:
            logger.error(f"[jugaad] Quote fetch failed for {symbol}: {exc}")
            raise
