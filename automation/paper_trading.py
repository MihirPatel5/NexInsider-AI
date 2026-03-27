"""
automation/paper_trading.py — Paper trading engine.
Intercepts orders and simulates execution in the DB instead of the broker.
"""
from datetime import datetime
from loguru import logger
from sqlalchemy import text
from data.db import get_session


class PaperBroker:
    """
    Virtual broker that simulates fills at current LTP.
    Maintains a virtual 'paper_positions' table.
    """
    def __init__(self, initial_cash: float = 100_000):
        self.cash = initial_cash

    async def execute_order(self, symbol: str, side: str, qty: int, price: float):
        """Simulate a trade execution."""
        total_cost = qty * price
        
        async with get_session() as session:
            # 1. Log trade
            await session.execute(
                text("""
                    INSERT INTO trade_history (symbol, exchange, side, quantity, entry_price, entry_time)
                    VALUES (:symbol, 'NSE', :side, :qty, :price, NOW())
                """),
                {"symbol": symbol, "side": side, "qty": qty, "price": price}
            )
            
            # 2. Update virtual position
            if side == "BUY":
                await session.execute(
                    text("""
                        INSERT INTO paper_positions (symbol, quantity, avg_price)
                        VALUES (:symbol, :qty, :price)
                        ON CONFLICT (symbol) DO UPDATE SET
                            avg_price = (paper_positions.avg_price * paper_positions.quantity + :price * :qty) / (paper_positions.quantity + :qty),
                            quantity = paper_positions.quantity + :qty
                    """),
                    {"symbol": symbol, "qty": qty, "price": price}
                )
            else: # SELL
                await session.execute(
                    text("UPDATE paper_positions SET quantity = quantity - :qty WHERE symbol = :symbol"),
                    {"symbol": symbol, "qty": qty}
                )
        
        logger.info(f"[paper] EXPLICIT {side} {qty} {symbol} @ {price}")
        return True
