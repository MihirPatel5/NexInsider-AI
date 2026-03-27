"""
backend/api/data.py — Data endpoints.
Exposes symbol master, OHLCV, and fundamental data.
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text

from data.db import get_session
from data.ingestion.ohlcv_store import get_ohlcv

router = APIRouter()


@router.get("/symbols")
async def get_symbols(q: str = Query(..., min_length=2)):
    """Search for symbols in the instrument master."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT symbol, name, exchange, instrument_type
                FROM instrument_master
                WHERE symbol ILIKE :q OR name ILIKE :q
                LIMIT 20
            """),
            {"q": f"%{q}%"}
        )
        return [{"symbol": r[0], "name": r[1], "exchange": r[2], "type": r[3]} for r in result.fetchall()]


@router.get("/ohlcv/{symbol}")
async def get_ohlcv_data(
    symbol: str,
    exchange: str = "NSE",
    interval: str = "1d",
    start: date = date.today() - timedelta(days=30),
    end: date = date.today(),
):
    """Retrieve OHLCV bars for a symbol."""
    df = await get_ohlcv(symbol, exchange, interval, start, end)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data found")
    return df.to_dict(orient="records")


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(symbol: str, exchange: str = "NSE"):
    """Get latest fundamental snapshot."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT * FROM fundamentals
                WHERE symbol = :symbol AND exchange = :exchange
                ORDER BY reported_date DESC LIMIT 1
            """),
            {"symbol": symbol, "exchange": exchange}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No fundamentals found")
        return dict(row._mapping)
