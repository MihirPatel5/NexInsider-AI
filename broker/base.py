"""
broker/base.py — Abstract Base Class for Broker Connectors.
Enforces a standard interface for all brokers (Zerodha, Upstox, etc.)
to allow seamless failover and routing.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseBroker(ABC):
    @abstractmethod
    def login(self) -> bool:
        """Authenticate with the broker API."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> dict:
        """Get live LTP (Last Traded Price)."""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        order_type: str,
        price: Optional[float] = None,
        tag: str = "algo",
    ) -> str:
        """Place an order and return the order_id."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        pass

    @abstractmethod
    def get_positions(self) -> List[dict]:
        """Fetch current open positions from the broker."""
        pass

    @abstractmethod
    def get_orders(self) -> List[dict]:
        """Fetch order history for the current session."""
        pass
