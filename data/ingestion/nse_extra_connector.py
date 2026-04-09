"""
data/ingestion/nse_extra_connector.py — NSE F&O, Indices, and Market Status.
Uses jugaad-data / NSE direct API / yfinance as layered fallbacks.
"""
from typing import Dict, List, Optional
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import ssl
import requests
import pandas as pd
import yfinance as yf
from loguru import logger
from urllib3.poolmanager import PoolManager
from urllib3.util.ssl_ import create_urllib3_context
from requests.adapters import HTTPAdapter

try:
    from nsepy import get_history
except ImportError:
    get_history = None

try:
    from nsetools import Nse as _Nse
except ImportError:
    _Nse = None

IST = ZoneInfo("Asia/Kolkata")


class TlsAdapter(HTTPAdapter):
    """TLS 1.2+ adapter — urllib3 v2.x compatible (no deprecated ssl_version)."""

    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
        )


# NSE index → yfinance ticker mapping
NSE_INDEX_YF_MAP = {
    "NIFTY 50":       "^NSEI",
    "NIFTY50":        "^NSEI",
    "NIFTY BANK":     "^NSEBANK",
    "BANKNIFTY":      "^NSEBANK",
    "NIFTY IT":       "^CNXIT",
    "NIFTY MIDCAP50": "NIFTYMIDCAP50.NS",
    "INDIAVIX":       "^INDIAVIX",
}


def _build_session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", TlsAdapter())
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.nseindia.com/",
        "X-Requested-With": "XMLHttpRequest",
    })
    return s


class NSEExtraConnector:
    """
    Fetches NSE index / F&O / market-status data.

    Index fetch order:
      1. jugaad-data index_raw   (fastest, no browser needed)
      2. NSE direct JSON API
      3. yfinance (no custom session — lets yfinance manage its own cookies)
    """

    def __init__(self):
        self._session = _build_session()
        # Warm up NSE cookies once
        try:
            self._session.get("https://www.nseindia.com", timeout=10)
        except Exception as e:
            logger.warning(f"[nse_extra] Warm-up failed: {e}")

        self._nse = _Nse() if _Nse else None

    # ─── Public API ──────────────────────────────────────────────────────────

    def get_index_data(self, index_name: str, start: date, end: date) -> pd.DataFrame:
        """
        Fetch historical OHLCV for an NSE index with multi-level fallback:
          1. jugaad-data
          2. NSE direct JSON API
          3. yfinance (no custom session)
        """
        # --- Attempt 1: jugaad-data ------------------------------------------
        df = self._fetch_jugaad(index_name, start, end)
        if not df.empty:
            return df

        # --- Attempt 2: NSE direct API ---------------------------------------
        df = self._fetch_nse_api(index_name, start, end)
        if not df.empty:
            return df

        # --- Attempt 3: yfinance (own session) --------------------------------
        df = self._fetch_yfinance(index_name, start, end)
        if not df.empty:
            return df

        logger.error(f"[nse_extra] All sources exhausted for index {index_name}")
        return pd.DataFrame()

    def get_vix_data(self, start: date, end: date) -> pd.DataFrame:
        return self.get_index_data("INDIAVIX", start, end)

    def get_option_chain(self, symbol: str, expiry: date = None) -> pd.DataFrame:
        try:
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
            resp = self._session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("records", {}).get("data", [])
                rows = []
                for item in records:
                    for opt_type in ("CE", "PE"):
                        if opt_type in item:
                            rows.append({**item[opt_type], "optionType": opt_type})
                return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"[nse_extra] Option chain failed for {symbol}: {e}")
        return pd.DataFrame()

    def get_market_status(self) -> dict:
        if self._nse:
            try:
                return self._nse.get_market_status()
            except Exception:
                pass
        return {"status": "UNKNOWN"}

    def get_top_gainers(self) -> list:
        if self._nse:
            try:
                return self._nse.get_top_gainers()
            except Exception:
                pass
        return []

    # ─── Private helpers ─────────────────────────────────────────────────────

    def _fetch_jugaad(self, index_name: str, start: date, end: date) -> pd.DataFrame:
        try:
            from jugaad_data.nse import index_raw
            raw = index_raw(symbol=index_name.upper(), from_date=start, to_date=end)
            df = pd.DataFrame(raw)
            if df.empty:
                return pd.DataFrame()
            # jugaad returns columns like 'CH_TIMESTAMP','CH_OPENING_PRICE', etc.
            col_map = {
                "CH_TIMESTAMP":    "time",
                "CH_OPENING_PRICE": "open",
                "CH_TRADE_HIGH_PRICE": "high",
                "CH_TRADE_LOW_PRICE":  "low",
                "CH_CLOSING_PRICE":    "close",
                "CH_TOT_TRADED_QTY":   "volume",
            }
            df = df.rename(columns=col_map)
            if "time" not in df.columns:
                # try alternate jugaad column names
                return pd.DataFrame()
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(IST)
            for c in ["open", "high", "low", "close", "volume"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df[[c for c in ["time", "open", "high", "low", "close", "volume"] if c in df.columns]]
            logger.info(f"[nse_extra] jugaad: {len(df)} rows for {index_name}")
            return df.sort_values("time").reset_index(drop=True)
        except Exception as e:
            logger.warning(f"[nse_extra] jugaad failed for {index_name}: {e}")
            return pd.DataFrame()

    def _fetch_nse_api(self, index_name: str, start: date, end: date) -> pd.DataFrame:
        """Use NSE's historical index CSV endpoint."""
        try:
            # NSE accepts date as DD-MM-YYYY
            s_str = start.strftime("%d-%m-%Y")
            e_str = end.strftime("%d-%m-%Y")
            index_encoded = requests.utils.quote(index_name.upper())
            url = (
                f"https://www.nseindia.com/api/historical/indices-history"
                f"?indexType={index_encoded}&from={s_str}&to={e_str}"
            )
            resp = self._session.get(url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("data", {}).get("indexCloseOnlineRecords", [])
                if rows:
                    df = pd.DataFrame(rows)
                    # Columns: EOD_TIMESTAMP, EOD_OPEN_INDEX_VAL, EOD_HIGH_INDEX_VAL,
                    #          EOD_LOW_INDEX_VAL, EOD_CLOSE_INDEX_VAL
                    df = df.rename(columns={
                        "EOD_TIMESTAMP":       "time",
                        "EOD_OPEN_INDEX_VAL":  "open",
                        "EOD_HIGH_INDEX_VAL":  "high",
                        "EOD_LOW_INDEX_VAL":   "low",
                        "EOD_CLOSE_INDEX_VAL": "close",
                    })
                    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(IST)
                    for c in ["open", "high", "low", "close"]:
                        if c in df.columns:
                            df[c] = pd.to_numeric(df[c], errors="coerce")
                    if "volume" not in df.columns:
                        df["volume"] = 0
                    df = df[[c for c in ["time", "open", "high", "low", "close", "volume"] if c in df.columns]]
                    logger.info(f"[nse_extra] NSE API: {len(df)} rows for {index_name}")
                    return df.sort_values("time").reset_index(drop=True)
            logger.warning(f"[nse_extra] NSE API returned {resp.status_code} for {index_name}")
        except Exception as e:
            logger.warning(f"[nse_extra] NSE API failed for {index_name}: {e}")
        return pd.DataFrame()

    def _fetch_yfinance(self, index_name: str, start: date, end: date) -> pd.DataFrame:
        """
        Fallback via yfinance WITHOUT a custom session.
        yfinance v0.2.x manages its own internal session/cookies — injecting
        a custom TLS session breaks its JSON response parsing.
        """
        ticker = NSE_INDEX_YF_MAP.get(index_name.upper(), None)
        if not ticker:
            # best-effort: try SYMBOL.NS
            ticker = f"{index_name.replace(' ', '')}.NS"
        try:
            logger.info(f"[nse_extra] yfinance: downloading {ticker}")
            df = yf.download(
                ticker,
                start=start,
                end=end + timedelta(days=1),
                progress=False,
                auto_adjust=True,
                # ← NO custom session: let yfinance handle its own cookies
            )
            if df.empty:
                logger.warning(f"[nse_extra] yfinance returned empty for {ticker}")
                return pd.DataFrame()
            df = df.reset_index()
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
            if "volume" not in df.columns:
                df["volume"] = 0
            df = df[[c for c in ["time", "open", "high", "low", "close", "volume"] if c in df.columns]]
            logger.info(f"[nse_extra] yfinance: {len(df)} rows for {ticker}")
            return df.sort_values("time").reset_index(drop=True)
        except Exception as e:
            logger.warning(f"[nse_extra] yfinance failed for {ticker}: {e}")
            return pd.DataFrame()
