"""
symbol_master/sync.py — Daily NSE/BSE instrument master synchronization.
Downloads NSE instrument CSV and upserts into symbol_master table.
"""
import csv
import io
from datetime import date

import httpx
from loguru import logger
from sqlalchemy import text

from data.db import get_session

NSE_CSV_URL = "https://nseindia.com/api/allcontracts.json"
NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_FO_URL = "https://www.nseindia.com/api/master-quote?type=EQ"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


async def sync_nse_equity_symbols() -> int:
    """
    Download NSE equity CSV and upsert into symbol_master.
    Returns count of upserted rows.
    CSV columns: SYMBOL,NAME OF COMPANY,SERIES,DATE OF LISTING,PAID UP VALUE,
                 MARKET LOT,ISIN NUMBER,FACE VALUE
    """
    logger.info("[symbol_master] Starting NSE equity symbol sync...")
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        resp = await client.get(NSE_EQUITY_URL)
        resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        logger.error("[symbol_master] NSE CSV returned 0 rows — aborting sync")
        return 0

    upsert_sql = text("""
        INSERT INTO symbol_master (symbol, isin, name, exchange, segment, instrument_type, lot_size, is_active, updated_at)
        VALUES (:symbol, :isin, :name, 'NSE', 'EQ', 'EQ', :lot_size, TRUE, NOW())
        ON CONFLICT (symbol, exchange)
        DO UPDATE SET
            name       = EXCLUDED.name,
            isin       = EXCLUDED.isin,
            lot_size   = EXCLUDED.lot_size,
            is_active  = TRUE,
            updated_at = NOW()
    """)

    count = 0
    async with get_session() as session:
        for row in rows:
            symbol = row.get("SYMBOL", "").strip()
            if not symbol:
                continue
            await session.execute(upsert_sql, {
                "symbol":   symbol,
                "isin":     row.get("ISIN NUMBER", "").strip() or None,
                "name":     row.get("NAME OF COMPANY", "").strip(),
                "lot_size": int(row.get("MARKET LOT", 1) or 1),
            })
            count += 1

    logger.success(f"[symbol_master] Upserted {count} NSE equity symbols")
    return count


async def mark_delisted_symbols(current_symbols: list[str], exchange: str = "NSE") -> int:
    """Mark symbols no longer in the instruments list as inactive."""
    if not current_symbols:
        return 0
    async with get_session() as session:
        result = await session.execute(
            text("""
                UPDATE symbol_master
                SET is_active = FALSE, updated_at = NOW()
                WHERE exchange = :exchange
                  AND symbol NOT IN :symbols
                  AND is_active = TRUE
            """),
            {"exchange": exchange, "symbols": tuple(current_symbols)},
        )
        count = result.rowcount
    if count:
        logger.info(f"[symbol_master] Marked {count} symbols as delisted on {exchange}")
    return count
