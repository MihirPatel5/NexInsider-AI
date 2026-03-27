"""
ingestion/yfinance_connector.py — yfinance connector for intraday + historical OHLCV.
Used as secondary source and for intraday intervals (5min, 15min, 1h).
"""
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from loguru import logger

from data.ingestion.base import BaseConnector, Quote

IST = ZoneInfo("Asia/Kolkata")

# yfinance interval mapping
YF_INTERVAL_MAP = {
    "1min":  "1m",
    "2min":  "2m",
    "5min":  "5m",
    "15min": "15m",
    "30min": "30m",
    "1h":    "60m",
    "1d":    "1d",
    "1w":    "1wk",
    "1mo":   "1mo",
}

# yfinance ticker suffix for NSE/BSE
EXCHANGE_SUFFIX = {
    "NSE": ".NS",
    "BSE": ".BO",
}


class YfinanceConnector(BaseConnector):
    source_name = "yfinance"

    def _ticker(self, symbol: str, exchange: str) -> str:
        suffix = EXCHANGE_SUFFIX.get(exchange.upper(), ".NS")
        return f"{symbol}{suffix}"

    def fetch_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        yf_interval = YF_INTERVAL_MAP.get(interval)
        if not yf_interval:
            raise ValueError(f"yfinance: unsupported interval '{interval}'")

        ticker = self._ticker(symbol, exchange)
        logger.info(f"[yfinance] Fetching {ticker} {interval} {start}→{end}")

        # yfinance intraday is limited to last 60 days for 1m, 730 days for 1h
        df = yf.download(
            ticker,
            start=start,
            end=end + timedelta(days=1),
            interval=yf_interval,
            progress=False,
            auto_adjust=True,   # handles splits/dividends automatically
        )

        if df.empty:
            logger.warning(f"[yfinance] No data for {ticker}")
            return pd.DataFrame()

        df = df.reset_index()
        # Handle multi-level columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]

        time_col = "datetime" if "datetime" in df.columns else "date"
        df = df.rename(columns={time_col: "time"})
        df["time"] = pd.to_datetime(df["time"])
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize(IST)
        else:
            df["time"] = df["time"].dt.tz_convert(IST)

        df["symbol"] = symbol
        df["exchange"] = exchange
        df["interval"] = interval
        df = df.rename(columns={"vol": "volume"})

        keep = ["time", "symbol", "exchange", "interval", "open", "high", "low", "close", "volume"]
        df = df[[c for c in keep if c in df.columns]]
        return self.validate_ohlcv(df.sort_values("time").reset_index(drop=True))

    def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        ticker = self._ticker(symbol, exchange)
        info = yf.Ticker(ticker).fast_info
        return Quote(
            symbol=symbol,
            exchange=exchange,
            ltp=float(info.last_price),
            volume=int(info.three_month_average_volume or 0),
        )
