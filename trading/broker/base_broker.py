"""
trading/broker/base_broker.py - Base broker interface.

Defines the interface that all broker implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """Order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"


class OrderSide(Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """Order details."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Position:
    """Position details."""
    symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    pnl_percent: float


@dataclass
class Tick:
    """Market tick data."""
    symbol: str
    last_price: float
    volume: int
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None


class BaseBroker(ABC):
    """Base broker interface that all brokers must implement."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to broker API.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from broker API.
        
        Returns:
            True if disconnection successful
        """
        pass
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
    ) -> Order:
        """
        Place an order.
        
        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Number of shares
            order_type: Order type
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for STOP_LOSS orders)
        
        Returns:
            Order object
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if cancellation successful
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """
        Get order status.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order object with current status
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Position object or None
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """
        Get account balance.
        
        Returns:
            Dict with balance details (available, used, total)
        """
        pass
    
    @abstractmethod
    async def subscribe_ticks(self, symbols: List[str]) -> bool:
        """
        Subscribe to live tick data.
        
        Args:
            symbols: List of symbols to subscribe
        
        Returns:
            True if subscription successful
        """
        pass
    
    @abstractmethod
    async def unsubscribe_ticks(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from live tick data.
        
        Args:
            symbols: List of symbols to unsubscribe
        
        Returns:
            True if unsubscription successful
        """
        pass
    
    @abstractmethod
    def on_tick(self, callback):
        """
        Register callback for tick data.
        
        Args:
            callback: Function to call on each tick
        """
        pass
    
    @abstractmethod
    def on_order_update(self, callback):
        """
        Register callback for order updates.
        
        Args:
            callback: Function to call on order update
        """
        pass
