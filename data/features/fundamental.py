"""
features/fundamental.py — Fundamental feature engineering.
Retrieves stored fundamental data from DB and returns a flat
feature dict suitable for the feature store.
"""
from sqlalchemy import text

from data.db import get_session


async def get_fundamental_features(symbol: str, exchange: str) -> dict:
    """
    Return the most recent fundamental features for a symbol as a flat dict.
    Returns {} if no fundamentals are stored yet.
    """
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    pe_ratio, forward_pe, pb_ratio, ev_ebitda,
                    eps, eps_growth_yoy, roe, roce, pat_margin,
                    debt_to_equity, current_ratio, free_cash_flow,
                    promoter_holding, fii_holding, dii_holding,
                    revenue, net_profit, market_cap
                FROM fundamentals
                WHERE symbol = :symbol AND exchange = :exchange
                ORDER BY reported_date DESC
                LIMIT 1
            """),
            {"symbol": symbol, "exchange": exchange},
        )
        row = result.fetchone()

    if not row:
        return {}

    keys = [
        "pe_ratio", "forward_pe", "pb_ratio", "ev_ebitda",
        "eps", "eps_growth_yoy", "roe", "roce", "pat_margin",
        "debt_to_equity", "current_ratio", "free_cash_flow",
        "promoter_holding", "fii_holding", "dii_holding",
        "revenue", "net_profit", "market_cap",
    ]
    return {k: (float(v) if v is not None else None) for k, v in zip(keys, row)}


async def get_fii_dii_latest(exchange: str = "NSE") -> dict:
    """Return the latest FII/DII net activity values."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT category, net_value
                FROM fii_dii_activity
                WHERE exchange = :exchange
                ORDER BY date DESC
                LIMIT 2
            """),
            {"exchange": exchange},
        )
        rows = result.fetchall()

    out = {"fii_net": None, "dii_net": None}
    for row in rows:
        if row[0] == "FII":
            out["fii_net"] = float(row[1]) if row[1] else None
        elif row[0] == "DII":
            out["dii_net"] = float(row[1]) if row[1] else None
    return out
