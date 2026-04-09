"""
corporate_actions/nse_fetcher.py — Fetch corporate action data from NSE.

Fetches splits, bonuses, rights issues, and dividends from NSE and stores them
in the corporate_actions table for backward price adjustment.
"""
import asyncio
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

import httpx
import pandas as pd
from loguru import logger

from data.corporate_actions.pipeline import store_corporate_action, ActionType


class NSECorporateActionFetcher:
    """
    Fetches corporate action data from NSE.
    
    NSE provides corporate action data through their website and APIs.
    We'll use multiple sources with fallback for reliability.
    """
    
    BASE_URL = "https://www.nseindia.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }
    
    def __init__(self):
        self.session: httpx.AsyncClient | None = None
    
    async def __aenter__(self):
        """Create async HTTP session with cookies."""
        self.session = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=30.0,
            follow_redirects=True
        )
        # Get cookies by visiting homepage first
        await self.session.get(self.BASE_URL)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close async HTTP session."""
        if self.session:
            await self.session.aclose()
    
    async def fetch_corporate_actions(
        self,
        symbol: str,
        from_date: date | None = None,
        to_date: date | None = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch corporate actions for a symbol from NSE.
        
        Args:
            symbol: NSE symbol (e.g., "RELIANCE", "TCS")
            from_date: Start date (default: 5 years ago)
            to_date: End date (default: today)
        
        Returns:
            List of corporate action dictionaries
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")
        
        if from_date is None:
            from_date = date.today() - timedelta(days=365 * 5)  # 5 years
        if to_date is None:
            to_date = date.today()
        
        logger.info(f"[nse_fetcher] Fetching corporate actions for {symbol} from {from_date} to {to_date}")
        
        # Try multiple endpoints with fallback
        actions = []
        
        # Method 1: NSE Corporate Actions API
        try:
            actions = await self._fetch_from_api(symbol, from_date, to_date)
            if actions:
                logger.info(f"[nse_fetcher] Fetched {len(actions)} actions from NSE API")
                return actions
        except Exception as e:
            logger.warning(f"[nse_fetcher] NSE API failed: {e}")
        
        # Method 2: Parse from NSE website (fallback)
        try:
            actions = await self._fetch_from_website(symbol, from_date, to_date)
            if actions:
                logger.info(f"[nse_fetcher] Fetched {len(actions)} actions from NSE website")
                return actions
        except Exception as e:
            logger.warning(f"[nse_fetcher] NSE website parsing failed: {e}")
        
        logger.warning(f"[nse_fetcher] No corporate actions found for {symbol}")
        return []
    
    async def _fetch_from_api(
        self,
        symbol: str,
        from_date: date,
        to_date: date
    ) -> List[Dict[str, Any]]:
        """
        Fetch from NSE corporate actions API.
        
        Endpoint: /api/corporates-corporateActions
        """
        url = f"{self.BASE_URL}/api/corporates-corporateActions"
        params = {
            "symbol": symbol,
            "from_date": from_date.strftime("%d-%m-%Y"),
            "to_date": to_date.strftime("%d-%m-%Y"),
        }
        
        response = await self.session.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response and normalize
        actions = []
        for item in data.get("data", []):
            action = self._parse_action_item(item)
            if action:
                actions.append(action)
        
        return actions
    
    async def _fetch_from_website(
        self,
        symbol: str,
        from_date: date,
        to_date: date
    ) -> List[Dict[str, Any]]:
        """
        Fallback: Parse corporate actions from NSE website HTML.
        
        This is a backup method if the API fails.
        """
        # NSE website corporate actions page
        url = f"{self.BASE_URL}/get-quotes/equity?symbol={symbol}"
        
        response = await self.session.get(url)
        response.raise_for_status()
        
        # Parse HTML and extract corporate actions
        # This would require BeautifulSoup or similar
        # For now, return empty list as placeholder
        logger.warning("[nse_fetcher] Website parsing not fully implemented yet")
        return []
    
    def _parse_action_item(self, item: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        Parse a corporate action item from NSE API response.
        
        Expected fields:
        - subject: "Bonus 1:1" or "Stock Split From Rs 10/- to Rs 5/-"
        - exDate: "01-Jan-2023"
        - recordDate: "31-Dec-2022"
        - purpose: "BONUS" or "SPLIT" or "DIVIDEND"
        """
        try:
            subject = item.get("subject", "")
            ex_date_str = item.get("exDate", "")
            record_date_str = item.get("recordDate", "")
            purpose = item.get("purpose", "").upper()
            
            if not ex_date_str:
                return None
            
            # Parse dates
            ex_date = datetime.strptime(ex_date_str, "%d-%b-%Y").date()
            record_date = None
            if record_date_str:
                try:
                    record_date = datetime.strptime(record_date_str, "%d-%b-%Y").date()
                except:
                    pass
            
            # Determine action type and parse ratios
            action_type, ratio_from, ratio_to, dividend_amount = self._parse_subject(subject, purpose)
            
            if not action_type:
                return None
            
            return {
                "action_type": action_type,
                "ex_date": ex_date,
                "record_date": record_date,
                "ratio_from": ratio_from,
                "ratio_to": ratio_to,
                "dividend_amount": dividend_amount,
                "subject": subject,
            }
        
        except Exception as e:
            logger.warning(f"[nse_fetcher] Failed to parse action item: {e}")
            return None
    
    def _parse_subject(
        self,
        subject: str,
        purpose: str
    ) -> tuple[ActionType | None, float | None, float | None, float | None]:
        """
        Parse subject line to extract action type and ratios.
        
        Examples:
        - "Bonus 1:1" → BONUS, 1, 1, None
        - "Stock Split From Rs 10/- to Rs 5/-" → SPLIT, 10, 5, None
        - "Dividend Rs 5 Per Share" → DIVIDEND, None, None, 5.0
        """
        subject_lower = subject.lower()
        
        # Bonus
        if "bonus" in subject_lower or purpose == "BONUS":
            # Extract ratio like "1:1" or "1:2"
            import re
            match = re.search(r"(\d+)\s*:\s*(\d+)", subject)
            if match:
                ratio_from = float(match.group(1))
                ratio_to = float(match.group(2))
                return "BONUS", ratio_from, ratio_to, None
            return "BONUS", None, None, None
        
        # Split
        if "split" in subject_lower or purpose == "SPLIT":
            # Extract "from Rs X to Rs Y"
            import re
            match = re.search(r"from\s+rs\.?\s*(\d+).*to\s+rs\.?\s*(\d+)", subject_lower)
            if match:
                ratio_from = float(match.group(1))
                ratio_to = float(match.group(2))
                return "SPLIT", ratio_from, ratio_to, None
            return "SPLIT", None, None, None
        
        # Dividend
        if "dividend" in subject_lower or purpose == "DIVIDEND":
            # Extract "Rs X per share"
            import re
            match = re.search(r"rs\.?\s*(\d+\.?\d*)", subject_lower)
            if match:
                dividend_amount = float(match.group(1))
                return "DIVIDEND", None, None, dividend_amount
            return "DIVIDEND", None, None, None
        
        # Rights
        if "rights" in subject_lower or purpose == "RIGHTS":
            return "RIGHTS", None, None, None
        
        return None, None, None, None


async def fetch_and_store_corporate_actions(
    symbol: str,
    exchange: str = "NSE",
    from_date: date | None = None,
    to_date: date | None = None
) -> int:
    """
    Fetch corporate actions from NSE and store in database.
    
    Args:
        symbol: Stock symbol
        exchange: Exchange (default: NSE)
        from_date: Start date (default: 5 years ago)
        to_date: End date (default: today)
    
    Returns:
        Number of actions stored
    """
    async with NSECorporateActionFetcher() as fetcher:
        actions = await fetcher.fetch_corporate_actions(symbol, from_date, to_date)
        
        stored_count = 0
        for action in actions:
            try:
                await store_corporate_action(
                    symbol=symbol,
                    exchange=exchange,
                    action_type=action["action_type"],
                    ex_date=action["ex_date"],
                    record_date=action.get("record_date"),
                    ratio_from=action.get("ratio_from"),
                    ratio_to=action.get("ratio_to"),
                    dividend_amount=action.get("dividend_amount"),
                    source="nse_api",
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"[nse_fetcher] Failed to store action: {e}")
        
        logger.info(f"[nse_fetcher] Stored {stored_count}/{len(actions)} corporate actions for {symbol}")
        return stored_count


async def sync_all_symbols_corporate_actions(
    symbols: List[str],
    exchange: str = "NSE",
    from_date: date | None = None
) -> Dict[str, int]:
    """
    Sync corporate actions for multiple symbols.
    
    Args:
        symbols: List of stock symbols
        exchange: Exchange (default: NSE)
        from_date: Start date (default: 1 year ago)
    
    Returns:
        Dictionary mapping symbol to number of actions stored
    """
    if from_date is None:
        from_date = date.today() - timedelta(days=365)
    
    results = {}
    
    for symbol in symbols:
        try:
            count = await fetch_and_store_corporate_actions(symbol, exchange, from_date)
            results[symbol] = count
            # Rate limiting - be nice to NSE servers
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"[nse_fetcher] Failed to sync {symbol}: {e}")
            results[symbol] = 0
    
    total = sum(results.values())
    logger.info(f"[nse_fetcher] Synced {total} corporate actions across {len(symbols)} symbols")
    return results


if __name__ == "__main__":
    # Test the fetcher
    async def test():
        # Test with RELIANCE
        count = await fetch_and_store_corporate_actions("RELIANCE", from_date=date(2020, 1, 1))
        print(f"Fetched {count} corporate actions for RELIANCE")
    
    asyncio.run(test())
