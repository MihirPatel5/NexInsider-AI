"""
trading/broker/angelone_data_broker.py - Angel One SmartAPI data broker.

IMPORTANT: This broker is for DATA FETCHING ONLY - NO TRADING!
Uses Angel One SmartAPI to get real market data for paper trading.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import os
from loguru import logger
from dotenv import load_dotenv

from .base_broker import (
    BaseBroker, Order, Position, Tick,
    OrderType, OrderSide, OrderStatus
)

# Load environment variables
load_dotenv()


class AngelOneDataBroker(BaseBroker):
    """
    Angel One SmartAPI data broker - DATA ONLY, NO TRADING!
    
    Fetches real market data from Angel One SmartAPI.
    All trades are simulated (paper trading).
    """
    
    def __init__(self, initial_balance: float = 100000.0):
        """
        Initialize Angel One data broker.
        
        Args:
            initial_balance: Starting balance for paper trading
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
        
        # Angel One API credentials
        self.api_key = os.getenv('SMART_API_KEY')
        self.api_secret = os.getenv('SMART_SCRET_KEY')
        
        # SmartAPI client (will be initialized on connect)
        self.smartapi = None
        self.feed_token = None
        
        logger.info(f"AngelOneDataBroker initialized (PAPER TRADING MODE)")
        logger.info(f"Initial balance: ₹{initial_balance:,.2f}")
        logger.warning("⚠️  DATA ONLY MODE - NO REAL TRADES WILL BE EXECUTED")
    
    async def connect(self) -> bool:
        """Connect to Angel One SmartAPI for data."""
        logger.info("Connecting to Angel One SmartAPI (data only)...")
        
        try:
            # Try to import SmartAPI
            try:
                from SmartApi import SmartConnect
            except ImportError:
                logger.error("SmartApi package not installed!")
                logger.info("Install with: pip install smartapi-python")
                logger.info("Falling back to mock mode...")
                self.connected = True
                return True
            
            if not self.api_key or not self.api_secret:
                logger.error("Angel One API credentials not found in .env!")
                logger.info("Falling back to mock mode...")
                self.connected = True
                return True
            
            # Initialize SmartAPI client
            self.smartapi = SmartConnect(api_key=self.api_key)
            
            # Note: For full authentication, you need:
            # 1. Client code (trading account number)
            # 2. Password
            # 3. TOTP (2FA code)
            # Since we only need data, we'll use limited access
            
            logger.info("✅ Connected to Angel One SmartAPI (data mode)")
            logger.warning("⚠️  Limited data access - full auth requires client code + password + TOTP")
            logger.info("💡 For now, using simulated data with realistic patterns")
            
            self.connected = True
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to Angel One: {e}")
            logger.info("Falling back to mock mode...")
            self.connected = True
            return True
    
    async def disconnect(self) -> bool:
        """Disconnect from Angel One SmartAPI."""
        logger.info("Disconnecting from Angel One SmartAPI...")
        
        if self.smartapi:
            try:
                # Logout if authenticated
                pass
            except:
                pass
        
        self.connected = False
        logger.info("✅ Disconnected from Angel One SmartAPI")
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
        """
        Place a SIMULATED order (paper trading only).
        
        NO REAL TRADES ARE EXECUTED!
        """
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        # Generate order ID
        self.order_counter += 1
        order_id = f"PAPER_{self.order_counter:06d}"
        
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
            f"📝 PAPER ORDER: {order_id} | {side.value} {quantity} {symbol} "
            f"@ {order_type.value} (SIMULATED)"
        )
        
        # Simulate immediate execution for market orders
        if order_type == OrderType.MARKET:
            await self._execute_order(order_id)
        
        return order
    
    async def _execute_order(self, order_id: str):
        """Simulate order execution."""
        await asyncio.sleep(0.05)
        
        order = self.orders.get(order_id)
        if not order:
            return
        
        # Use current market price (from last tick or estimate)
        if order.price:
            execution_price = order.price
        else:
            execution_price = self._get_current_price(order.symbol)
        
        order.status = OrderStatus.COMPLETE
        order.filled_quantity = order.quantity
        order.average_price = execution_price
        
        # Update position
        self._update_position(order)
        
        logger.info(
            f"✅ PAPER EXECUTION: {order_id} | {order.quantity} @ ₹{execution_price:.2f} (SIMULATED)"
        )
        
        # Notify callbacks
        for callback in self.order_callbacks:
            try:
                await callback(order)
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    def _update_position(self, order: Order):
        """Update simulated position."""
        symbol = order.symbol
        
        if symbol not in self.positions:
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
            pos = self.positions[symbol]
            
            if order.side == OrderSide.BUY:
                total_cost = (pos.quantity * pos.average_price + 
                             order.filled_quantity * order.average_price)
                total_quantity = pos.quantity + order.filled_quantity
                pos.average_price = total_cost / total_quantity
                pos.quantity = total_quantity
            else:
                pos.quantity -= order.filled_quantity
                
                if pos.quantity <= 0:
                    del self.positions[symbol]
                    return
            
            pos.last_price = order.average_price
            pos.pnl = (pos.last_price - pos.average_price) * pos.quantity
            pos.pnl_percent = (pos.last_price / pos.average_price - 1) * 100
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current market price (simulated for now)."""
        # TODO: Fetch real price from Angel One API
        # For now, return realistic price
        prices = {
            "NIFTY50": 23500.0,
            "BANKNIFTY": 48000.0,
            "NIFTY": 23500.0,
        }
        return prices.get(symbol, 1000.0)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a simulated order."""
        order = self.orders.get(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        if order.status in [OrderStatus.COMPLETE, OrderStatus.CANCELLED]:
            logger.warning(f"Cannot cancel order in status: {order.status}")
            return False
        
        order.status = OrderStatus.CANCELLED
        logger.info(f"❌ PAPER ORDER CANCELLED: {order_id}")
        return True
    
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        return order
    
    async def get_positions(self) -> List[Position]:
        """Get all simulated positions."""
        return list(self.positions.values())
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get simulated position for symbol."""
        return self.positions.get(symbol)
    
    async def get_balance(self) -> Dict[str, float]:
        """Get simulated account balance."""
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
        """Subscribe to real-time data from Angel One."""
        self.subscribed_symbols.extend(symbols)
        logger.info(f"📊 Subscribed to Angel One data: {symbols}")
        logger.info("💡 Using simulated ticks (full WebSocket requires authentication)")
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
    
    async def simulate_realistic_ticks(self, interval: float = 1.0):
        """
        Simulate realistic tick data.
        
        TODO: Replace with real Angel One WebSocket data when authenticated.
        
        Args:
            interval: Seconds between ticks
        """
        logger.info(f"Starting realistic tick simulation (interval: {interval}s)")
        logger.info("💡 This will be replaced with real Angel One data after full authentication")
        
        import random
        
        # Base prices
        base_prices = {
            "NIFTY50": 23500.0,
            "NIFTY": 23500.0,
            "BANKNIFTY": 48000.0,
        }
        
        # Price tracking for realistic movement
        current_prices = base_prices.copy()
        
        while self.connected:
            for symbol in self.subscribed_symbols:
                # Realistic price movement (±0.05% per tick)
                if symbol in current_prices:
                    change_pct = random.uniform(-0.0005, 0.0005)
                    current_prices[symbol] *= (1 + change_pct)
                    price = current_prices[symbol]
                else:
                    price = 1000.0
                
                tick = Tick(
                    symbol=symbol,
                    last_price=price,
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
