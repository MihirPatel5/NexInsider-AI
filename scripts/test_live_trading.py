"""
scripts/test_live_trading.py - Test live trading system components.

Tests the mock broker, candle builder, and strategy integration.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime, timedelta
from loguru import logger

from trading.broker import MockBroker, OrderSide, OrderType
from trading.data import CandleBuilder


async def test_mock_broker():
    """Test MockBroker functionality."""
    logger.info("="*60)
    logger.info("TEST 1: MockBroker")
    logger.info("="*60)
    
    broker = MockBroker(initial_balance=100000.0)
    
    # Test connection
    await broker.connect()
    assert broker.connected, "Broker should be connected"
    logger.info("✅ Connection test passed")
    
    # Test balance
    balance = await broker.get_balance()
    assert balance['total'] == 100000.0, "Initial balance should be 100000"
    logger.info(f"✅ Balance test passed: ₹{balance['total']:,.2f}")
    
    # Test order placement
    order = await broker.place_order(
        symbol="NIFTY50",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.MARKET
    )
    assert order.order_id is not None, "Order should have ID"
    logger.info(f"✅ Order placement test passed: {order.order_id}")
    
    # Wait for execution
    await asyncio.sleep(0.2)
    
    # Test position
    position = await broker.get_position("NIFTY50")
    assert position is not None, "Position should exist"
    assert position.quantity == 10, "Position quantity should be 10"
    logger.info(f"✅ Position test passed: {position.quantity} @ ₹{position.average_price:.2f}")
    
    # Test order cancellation
    order2 = await broker.place_order(
        symbol="NIFTY50",
        side=OrderSide.SELL,
        quantity=5,
        order_type=OrderType.LIMIT,
        price=24000.0
    )
    cancelled = await broker.cancel_order(order2.order_id)
    assert cancelled, "Order should be cancelled"
    logger.info("✅ Order cancellation test passed")
    
    # Disconnect
    await broker.disconnect()
    assert not broker.connected, "Broker should be disconnected"
    logger.info("✅ Disconnection test passed")
    
    logger.info("")
    logger.info("✅ ALL MOCK BROKER TESTS PASSED")
    logger.info("")


async def test_candle_builder():
    """Test CandleBuilder functionality."""
    logger.info("="*60)
    logger.info("TEST 2: CandleBuilder")
    logger.info("="*60)
    
    candles_received = []
    
    def on_candle(candle):
        candles_received.append(candle)
        logger.info(
            f"Candle: {candle['time']} | "
            f"O:{candle['open']:.2f} H:{candle['high']:.2f} "
            f"L:{candle['low']:.2f} C:{candle['close']:.2f}"
        )
    
    builder = CandleBuilder(interval_minutes=5, on_candle_callback=on_candle)
    
    # Simulate ticks over 10 minutes (2 candles)
    base_time = datetime(2026, 4, 10, 9, 30, 0)
    
    # First candle (9:30-9:35)
    for i in range(30):
        tick_time = base_time + timedelta(seconds=i*10)
        price = 23500 + (i * 0.5)  # Gradually increasing
        builder.add_tick("NIFTY50", price, 1000, tick_time)
    
    # Second candle (9:35-9:40)
    for i in range(30):
        tick_time = base_time + timedelta(minutes=5, seconds=i*10)
        price = 23515 - (i * 0.3)  # Gradually decreasing
        builder.add_tick("NIFTY50", price, 1000, tick_time)
    
    # Force close last candle
    builder.force_close_candle("NIFTY50")
    
    assert len(candles_received) == 2, f"Should have 2 candles, got {len(candles_received)}"
    logger.info(f"✅ Candle count test passed: {len(candles_received)} candles")
    
    # Verify first candle
    candle1 = candles_received[0]
    assert candle1['open'] == 23500.0, "First candle open should be 23500"
    assert candle1['high'] > candle1['open'], "High should be > open"
    assert candle1['low'] == candle1['open'], "Low should equal open (increasing prices)"
    logger.info("✅ First candle OHLC test passed")
    
    # Verify second candle
    candle2 = candles_received[1]
    assert candle2['open'] == 23515.0, "Second candle open should be 23515"
    assert candle2['low'] < candle2['open'], "Low should be < open (decreasing prices)"
    logger.info("✅ Second candle OHLC test passed")
    
    logger.info("")
    logger.info("✅ ALL CANDLE BUILDER TESTS PASSED")
    logger.info("")


async def test_integration():
    """Test integration of broker + candle builder."""
    logger.info("="*60)
    logger.info("TEST 3: Integration")
    logger.info("="*60)
    
    broker = MockBroker(initial_balance=100000.0)
    await broker.connect()
    
    candles_received = []
    
    def on_candle(candle):
        candles_received.append(candle)
    
    builder = CandleBuilder(interval_minutes=5, on_candle_callback=on_candle)
    
    # Register tick callback
    async def on_tick(tick):
        builder.add_tick(tick.symbol, tick.last_price, tick.volume, tick.timestamp)
    
    broker.on_tick(on_tick)
    
    # Subscribe and simulate
    await broker.subscribe_ticks(["NIFTY50"])
    
    # Run tick simulation for 3 seconds
    logger.info("Running tick simulation for 3 seconds...")
    tick_task = asyncio.create_task(broker.simulate_ticks(interval=0.5))
    
    await asyncio.sleep(3)
    
    # Stop simulation
    await broker.disconnect()
    tick_task.cancel()
    
    try:
        await tick_task
    except asyncio.CancelledError:
        pass
    
    logger.info(f"Received {len(candles_received)} candles during simulation")
    logger.info("✅ Integration test passed")
    
    logger.info("")
    logger.info("✅ ALL INTEGRATION TESTS PASSED")
    logger.info("")


async def main():
    """Run all tests."""
    logger.info("")
    logger.info("="*60)
    logger.info("LIVE TRADING SYSTEM TESTS")
    logger.info("="*60)
    logger.info("")
    
    try:
        await test_mock_broker()
        await test_candle_builder()
        await test_integration()
        
        logger.info("="*60)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("="*60)
        logger.info("")
        logger.info("Your live trading system is ready to use!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run: python3 scripts/start_live_trading.py --paper")
        logger.info("2. Add Zerodha API credentials when ready")
        logger.info("3. Implement monitoring dashboard")
        logger.info("")
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
