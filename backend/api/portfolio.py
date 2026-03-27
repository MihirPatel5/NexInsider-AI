"""
backend/api/portfolio.py — Portfolio endpoints.
Exposes live holdings, P&L, and trade history.
"""
from fastapi import APIRouter
from sqlalchemy import text
from data.db import get_session

router = APIRouter()


@router.get("/holdings")
async def get_holdings():
    """Get all currently open positions."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT symbol, exchange, quantity, avg_price, current_price,
                       (current_price - avg_price) * quantity AS pnl_unrealized
                FROM positions
                WHERE quantity > 0
            """)
        )
        return [dict(r._mapping) for r in result.fetchall()]


@router.get("/history")
async def get_trade_history(limit: int = 100):
    """Get completed trade history."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT * FROM trade_history
                ORDER BY exit_time DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        return [dict(r._mapping) for r in result.fetchall()]
