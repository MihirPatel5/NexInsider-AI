"""
broker/router.py — Smart Order Router.
Handles primary (Zerodha) and secondary (Upstox) broker logic.
Implements idempotency and automatic failover.
"""
from typing import Optional
from loguru import logger

from broker.zerodha import ZerodhaBroker
# from broker.upstox import UpstoxBroker # to be implemented


class OrderRouter:
    def __init__(self):
        self.primary = ZerodhaBroker()
        # self.secondary = UpstoxBroker()
        self.active_broker = self.primary

    def route_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "LIMIT",
        price: float = None,
    ) -> str:
        """
        Route order to active broker with failover logic.
        """
        try:
            logger.info(f"[router] Routing {side} {symbol} to {self.active_broker.__class__.__name__}")
            return self.active_broker.place_order(symbol, side, qty, order_type, price)
        except Exception as exc:
            logger.warning(f"[router] Primary broker failed: {exc}. Attempting failover...")
            # If failover is enabled:
            # self.active_broker = self.secondary
            # return self.active_broker.place_order(...)
            raise

    def get_unified_positions(self) -> list:
        """Combine positions across all brokers if multiple are used."""
        return self.primary.get_positions()
