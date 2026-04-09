"""
ingestion/jugaad_connector.py — Primary NSE/BSE data connector via jugaad-data.
Hardened with session-based cookie warming and TLS 1.2+ forced.
"""
import requests
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo
from io import StringIO
from loguru import logger
from jugaad_data.nse import NSELive, stock_df
from data.ingestion.base import BaseConnector, Quote
import ssl
from urllib3.poolmanager import PoolManager
from urllib3.util.ssl_ import create_urllib3_context
from requests.adapters import HTTPAdapter

IST = ZoneInfo("Asia/Kolkata")

class TlsAdapter(HTTPAdapter):
    """
    Forces TLS 1.2+ for NSE/Yahoo. Uses ssl_context (urllib3 v2.x compatible).
    """
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
        )

class JugaadConnector(BaseConnector):
    source_name = "jugaad"

    def __init__(self):
        self._live = NSELive()
        self.session = requests.Session()
        self.session.mount("https://", TlsAdapter())
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        self._warm_up()

    def _warm_up(self):
        """Warm up by visiting home page to set cookies."""
        try:
            # First visit home to get main cookies
            self.session.get("https://www.nseindia.com", timeout=15)
            # Then visit market data page to get more specific session state
            self.session.get("https://www.nseindia.com/market-data/live-equity-market", timeout=15)
            logger.info("[jugaad] NSE Session warmed up successfully")
        except Exception as e:
            logger.warning(f"[jugaad] Session warm-up failed: {e}")

    def fetch_ohlcv(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start: date,
        end: date,
    ) -> pd.DataFrame:
        if interval not in ("1d", "1w"):
            raise ValueError(f"JugaadConnector supports 1d, 1w. Got: {interval}")

        logger.info(f"[jugaad] Fetching {symbol} {start}→{end}")
        
        try:
            # Try jugaad-data's stock_df first (uses standard requests)
            df = stock_df(symbol=symbol, from_date=start, to_date=end, series="EQ")
            if not df.empty:
                return self._process_df(df, symbol, exchange, interval)
        except Exception as e:
            logger.warning(f"[jugaad] jugaad-data failed for {symbol}: {e}. Trying direct API...")
        
        # PRO-GRADE FALLBACK: Direct API request with our warmed session
        return self._fetch_direct(symbol, exchange, interval, start, end)

    def _fetch_direct(self, symbol, exchange, interval, start, end) -> pd.DataFrame:
        try:
            s_str = start.strftime("%d-%m-%Y")
            e_str = end.strftime("%d-%m-%Y")
            url = f"https://www.nseindia.com/api/historical/cm/equity?symbol={symbol}&series=[%22EQ%22]&from={s_str}&to={e_str}&csv=true"
            
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 200:
                df = pd.read_csv(StringIO(resp.text))
                df.columns = [c.strip().upper() for c in df.columns]
                return self._process_df(df, symbol, exchange, interval)
            
            logger.error(f"[jugaad] Direct API failed with status {resp.status_code}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"[jugaad] Direct API failed for {symbol}: {e}")
            return pd.DataFrame()

    def _process_df(self, df: pd.DataFrame, symbol: str, exchange: str, interval: str) -> pd.DataFrame:
        # Standardize columns (handle both jugaad-data and direct API naming)
        rename_map = {
            "DATE": "time", "Date": "time",
            "OPEN": "open", "Open": "open",
            "HIGH": "high", "High": "high",
            "LOW": "low", "Low": "low",
            "CLOSE": "close", "Close": "close",
            "VOLUME": "volume", "Volume": "volume"
        }
        df = df.rename(columns=rename_map)
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(IST)
        df["symbol"] = symbol
        df["exchange"] = exchange
        df["interval"] = interval
        keep = ["time", "symbol", "exchange", "interval", "open", "high", "low", "close", "volume"]
        df = df[[c for c in keep if c in df.columns]]
        return self.validate_ohlcv(df.sort_values("time").reset_index(drop=True))

    def fetch_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        try:
            # Try direct API first as it's more robust with our session
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            resp = self.session.get(url, timeout=10)
            data = resp.json()
            p = data.get("priceInfo", {})
            m = data.get("marketDeptOrderBook", {}).get("tradeInfo", {})
            return Quote(
                symbol=symbol,
                exchange=exchange,
                ltp=float(p.get("lastPrice", 0)),
                volume=int(m.get("totalTradedVolume", 0))
            )
        except Exception:
            # Fallback to jugaad-data NSELive
            data = self._live.equities(symbol)
            return Quote(
                symbol=symbol,
                exchange=exchange,
                ltp=float(data.get("lastPrice", 0)),
                volume=int(data.get("totalTradedVolume", 0))
            )
