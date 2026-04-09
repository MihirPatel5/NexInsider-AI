"""
corporate_actions/pipeline.py — Corporate action ingestion and price adjustment.
Fetches NSE corporate action data and computes backward-adjusted price factors.

CRITICAL: All OHLCV data must be adjusted for splits/bonuses before feature
computation. Without this, momentum indicators will fire on artificial price jumps.
"""
from datetime import date
from typing import Literal

import pandas as pd
from loguru import logger
from sqlalchemy import text

from data.db import get_session

ActionType = Literal["SPLIT", "BONUS", "RIGHTS", "DIVIDEND", "MERGER"]


def compute_split_factor(ratio_from: float, ratio_to: float) -> float:
    """
    Compute the backward price adjustment factor for a stock split/bonus.

    For a 1:2 split (1 share → 2 shares), price halves:
      adj_factor = ratio_from / ratio_to = 1/2 = 0.5

    For a 2:1 bonus (2 bonus shares per 1 held → 3 total):
      adj_factor = 1 / (1 + ratio_to/ratio_from)

    Args:
        ratio_from: shares BEFORE the action
        ratio_to:   shares AFTER the action
    """
    if ratio_from <= 0 or ratio_to <= 0:
        raise ValueError(f"Invalid ratio: {ratio_from}:{ratio_to}")
    return ratio_from / ratio_to


async def store_corporate_action(
    symbol: str,
    exchange: str,
    action_type: ActionType,
    ex_date: date,
    ratio_from: float | None = None,
    ratio_to: float | None = None,
    dividend_amount: float | None = None,
    record_date: date | None = None,
    source: str = "nse",
) -> None:
    """Insert or update a corporate action record."""
    adj_factor = None
    if action_type in ("SPLIT", "BONUS") and ratio_from and ratio_to:
        adj_factor = compute_split_factor(ratio_from, ratio_to)

    async with get_session() as session:
        await session.execute(
            text("""
                INSERT INTO corporate_actions
                    (symbol, exchange, action_type, ex_date, record_date,
                     ratio_from, ratio_to, dividend_amount, adj_factor, source)
                VALUES
                    (:symbol, :exchange, :action_type, :ex_date, :record_date,
                     :ratio_from, :ratio_to, :dividend_amount, :adj_factor, :source)
                ON CONFLICT (symbol, exchange, action_type, ex_date)
                DO UPDATE SET
                    ratio_from       = EXCLUDED.ratio_from,
                    ratio_to         = EXCLUDED.ratio_to,
                    dividend_amount  = EXCLUDED.dividend_amount,
                    adj_factor       = EXCLUDED.adj_factor,
                    record_date      = EXCLUDED.record_date
            """),
            dict(
                symbol=symbol, exchange=exchange, action_type=action_type,
                ex_date=ex_date, record_date=record_date,
                ratio_from=ratio_from, ratio_to=ratio_to,
                dividend_amount=dividend_amount, adj_factor=adj_factor,
                source=source,
            ),
        )
    logger.info(f"[corp_action] Stored {action_type} for {symbol} on {ex_date}")


async def get_adjustment_factors(symbol: str, exchange: str) -> pd.DataFrame:
    """
    Return all corporate actions for a symbol sorted by ex_date.
    Used to apply backward-adjusted multipliers to historical OHLCV.
    """
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT ex_date, action_type, adj_factor
                FROM corporate_actions
                WHERE symbol = :symbol AND exchange = :exchange
                  AND action_type IN ('SPLIT', 'BONUS')
                  AND adj_factor IS NOT NULL
                ORDER BY ex_date ASC
            """),
            {"symbol": symbol, "exchange": exchange},
        )
        rows = result.fetchall()
    return pd.DataFrame(rows, columns=["ex_date", "action_type", "adj_factor"])


def apply_backward_adjustment(df: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    """
    Apply backward price adjustment to an OHLCV DataFrame.

    For each corporate action ex_date, ALL historical bars BEFORE that date
    are multiplied by the adj_factor so that historical prices are on the
    same scale as current prices.

    Args:
        df:      OHLCV DataFrame with 'time' column (tz-aware)
        actions: DataFrame from get_adjustment_factors()

    Returns:
        df with 'adj_open', 'adj_high', 'adj_low', 'adj_close', 'adj_factor' columns added.
    """
    df = df.copy().sort_values("time").reset_index(drop=True)
    
    if actions.empty:
        df["adj_factor"] = 1.0
        for col in ["open", "high", "low", "close"]:
            df[f"adj_{col}"] = df[col]
        return df

    df["adj_factor"] = 1.0

    # Apply adjustments: for each action, multiply all bars BEFORE ex_date by adj_factor
    for _, action in actions.iterrows():
        ex_date = pd.Timestamp(action["ex_date"]).tz_localize("Asia/Kolkata")
        mask = df["time"] < ex_date
        df.loc[mask, "adj_factor"] *= action["adj_factor"]

    # Apply the cumulative adjustment factor to all OHLC columns
    for col in ["open", "high", "low", "close"]:
        df[f"adj_{col}"] = df[col] * df["adj_factor"]

    logger.debug(f"[corp_action] Applied {len(actions)} adjustments to {len(df)} bars")
    return df
