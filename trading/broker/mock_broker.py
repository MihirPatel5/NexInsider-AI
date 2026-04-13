"""
trading/broker/mock_broker.py - Mock broker for testing.

Simulates broker behavior without real API calls.
Use this for development and testing before connecting real broker.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import random
from loguru import logger

from .base_broker import (
    BaseBroker, Order, Position, Tick,
    OrderType, OrderSide, OrderStatus
)


class MockBroker(BaseBroker):
    """Mock broker implementation for testing."""
    
    def __init__(self, initial_balance: float = 100000.0):
        """
        Initialize mock broker.
        
        Args:
            initial_balance: Starting balance
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.order_counter = 0
        self.connected = False
        self.subscribed_symbols: List[str] = []
        self.tick_callbacks = []
        self.order_callbacks = []
        
        logger.info(f"MockBroker initialized with balance: ₹{initial_balance:,.2f}")
    
    async def connect(self) -> bool:
        """Connect to mock broker."""
        logger.info("Connecting to MockBroker...")
        await asyncio.sleep(0.1)  # Simulate connection delay
        self.connected = True
        logger.info("✅ Connected to MockBroker")
        return True
    
    async def disconnect(self) -> bool:
        """Disconnect from mock broker."""
        logger.info("Disconnecting from MockBroker...")
        self.connected = False
        logger.info("✅ Disconnected from MockBroker")
        return True
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
    ) -> Order:
        """Place a mock order."""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        # Generate order ID
        self.order_counter += 1
        order_id = f"MOCK_{self.order_counter:06d}"
        
        # Create order
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            status=OrderStatus.OPEN,
            timestamp=datetime.now()
        )
        
        self.orders[order_id] = order
        
        logger.info(
            f"📝 Order placed: {order_id} | {side.value} {quantity} {symbol} "
            f"@ {order_type.value}"
        )
        
        # Simulate immediate execution for market orders
        if order_type == OrderType.MARKET:
            await self._execute_order(order_id)
        
        return order
    
    async def _execute_order(self, order_id: str):
        """Simulate order execution."""
        await asyncio.sleep(0.05)  # Simulate execution delay
        
        order = self.orders.get(order_id)
        if not order:
            return
        
        # Simulate execution price (with small slippage)
        if order.price:
            execution_price = order.price * (1 + random.uniform(-0.001, 0.001))
        else:
            # Use a mock price based on symbol
            execution_price = self._get_mock_price(order.symbol)
        
        order.status = OrderStatus.COMPLETE
        order.filled_quantity = order.quantity
        order.average_price = execution_price
        
        # Update position
        self._update_position(order)
        
        logger.info(
            f"✅ Order executed: {order_id} | {order.quantity} @ ₹{execution_price:.2f}"
        )
        
        # Notify callbacks
        for callback in self.order_callbacks:
            try:
                await callback(order)
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    def _update_position(self, order: Order):
        """Update position after order execution."""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # New position
            if order.side == OrderSide.BUY:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.filled_quantity,
                    average_price=order.average_price,
                    last_price=order.average_price,
                    pnl=0.0,
                    pnl_percent=0.0
                )
        else:
            # Update existing position
            pos = self.positions[symbol]
            
            if order.side == OrderSide.BUY:
                # Add to position
                total_cost = (pos.quantity * pos.average_price + 
                             order.filled_quantity * order.average_price)
                total_quantity = pos.quantity + order.filled_quantity
                pos.average_price = total_cost / total_quantity
                pos.quantity = total_quantity
            else:
                # Reduce position
                pos.quantity -= order.filled_quantity
                
                if pos.quantity <= 0:
                    # Position closed
                    del self.positions[symbol]
                    return
            
            # Update PnL
            pos.last_price = order.average_price
            pos.pnl = (pos.last_price - pos.average_price) * pos.quantity
            pos.pnl_percent = (pos.last_price / pos.average_price - 1) * 100
    
    def _get_mock_price(self, symbol: str) -> float:
        """Get mock price for symbol."""
        # Return mock prices based on symbol
        mock_prices = {
            "NIFTY50": 23500.0,
            "BANKNIFTY": 48000.0,
            "RELIANCE": 2800.0,
            "TCS": 3500.0,
        }
        return mock_prices.get(symbol, 1000.0) * (1 + random.uniform(-0.01, 0.01))
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a mock order."""
        order = self.orders.get(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        if order.status in [OrderStatus.COMPLETE, OrderStatus.CANCELLED]:
            logger.warning(f"Cannot cancel order in status: {order.status}")
            return False
        
        order.status = OrderStatus.CANCELLED
        logger.info(f"❌ Order cancelled: {order_id}")
        return True
    
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        return order
    
    async def get_positions(self) -> List[Position]:
        """Get all positions."""
        return list(self.positions.values())
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        return self.positions.get(symbol)
    
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        # Calculate used margin from positions
        used = sum(
            pos.quantity * pos.average_price 
            for pos in self.positions.values()
        )
        
        return {
            "total": self.balance,
            "available": self.balance - used,
            "used": used,
        }
    
    async def subscribe_ticks(self, symbols: List[str]) -> bool:
        """Subscribe to tick data."""
        self.subscribed_symbols.extend(symbols)
        logger.info(f"📊 Subscribed to ticks: {symbols}")
        return True
    
    async def unsubscribe_ticks(self, symbols: List[str]) -> bool:
        """Unsubscribe from tick data."""
        for symbol in symbols:
            if symbol in self.subscribed_symbols:
                self.subscribed_symbols.remove(symbol)
        logger.info(f"📊 Unsubscribed from ticks: {symbols}")
        return True
    
    def on_tick(self, callback):
        """Register tick callback."""
        self.tick_callbacks.append(callback)
    
    def on_order_update(self, callback):
        """Register order update callback."""
        self.order_callbacks.append(callback)
    
    async def simulate_ticks(self, interval: float = 1.0):
        """
        Simulate tick data generation.
        
        Args:
            interval: Seconds between ticks
        """
        logger.info(f"Starting tick simulation (interval: {interval}s)")
        
        while self.connected:
            for symbol in self.subscribed_symbols:
                # Simulate realistic price movement
                base_price = self._get_mock_price(symbol)
                
                tick = Tick(
                    symbol=symbol,
                    last_price=base_price,
                    volume=random.randint(1000, 10000),
                    timestamp=datetime.now()
                )
                
                # Notify callbacks
                for callback in self.tick_callbacks:
                    try:
                        await callback(tick)
                    except Exception as e:
                        logger.error(f"Error in tick callback: {e}")
            
            await asyncio.sleep(interval)
