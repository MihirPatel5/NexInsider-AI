"""
backend/api/signals.py — Signal endpoints.
Exposes current ML signals and historical signal performance.
"""
from fastapi import APIRouter
from sqlalchemy import text
from data.db import get_session

router = APIRouter()


@router.get("/latest")
async def get_latest_signals(limit: int = 50):
    """Get the most recent signals generated across all models."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT s.time, s.symbol, s.signal, s.confidence, s.strategy_id, sm.accuracy
                FROM signals s
                LEFT JOIN strategy_metrics sm ON s.strategy_id = sm.strategy_id
                ORDER BY s.time DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        return [dict(r._mapping) for r in result.fetchall()]


@router.get("/symbol/{symbol}")
async def get_symbol_signals(symbol: str):
    """Get signal history for a specific symbol."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT time, signal, confidence, strategy_id
                FROM signals
                WHERE symbol = :symbol
                ORDER BY time DESC
                LIMIT 100
            """),
            {"symbol": symbol}
        )
        return [dict(r._mapping) for r in result.fetchall()]
