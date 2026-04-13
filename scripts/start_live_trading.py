"""
scripts/start_live_trading.py - Start live trading system.

Usage:
    python3 scripts/start_live_trading.py
    python3 scripts/start_live_trading.py --config config/live_trading_config.yaml
    python3 scripts/start_live_trading.py --paper  # Paper trading mode
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import argparse
import yaml
from loguru import logger

from trading.broker import MockBroker, AngelOneDataBroker
from trading.strategies.live_intraday_strategy import LiveIntradayStrategy
from trading.monitoring import Dashboard


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


async def main():
    """Main entry point for live trading."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Start live trading system")
    parser.add_argument(
        "--config",
        default="config/live_trading_config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Enable paper trading mode"
    )
    args = parser.parse_args()
    
    # Load configuration
    logger.info("="*80)
    logger.info("LIVE TRADING SYSTEM")
    logger.info("="*80)
    logger.info(f"Loading configuration from: {args.config}")
    
    config = load_config(args.config)
    
    # Override with paper trading if specified
    if args.paper:
        logger.info("📄 PAPER TRADING MODE ENABLED")
        config['paper_trading']['enabled'] = True
        config['broker']['type'] = 'mock'
    
    # Initialize broker
    broker_type = config['broker']['type']
    logger.info(f"Initializing broker: {broker_type}")
    
    if broker_type == 'mock' or config['paper_trading']['enabled']:
        initial_balance = config['broker']['mock']['initial_balance']
        broker = MockBroker(initial_balance=initial_balance)
        logger.info(f"✅ MockBroker initialized with ₹{initial_balance:,.2f}")
    
    elif broker_type == 'angelone_data':
        initial_balance = config['broker']['angelone_data']['initial_balance']
        broker = AngelOneDataBroker(initial_balance=initial_balance)
        logger.info(f"✅ AngelOneDataBroker initialized (PAPER TRADING)")
        logger.warning("⚠️  DATA ONLY MODE - NO REAL TRADES")
    
    elif broker_type == 'zerodha':
        logger.error("❌ Zerodha broker not yet implemented!")
        logger.info("Please add your API credentials and implement ZerodhaBroker")
        logger.info("For now, use MockBroker or AngelOneDataBroker:")
        logger.info("  python3 scripts/start_live_trading.py --paper")
        return 1
    
    else:
        logger.error(f"Unknown broker type: {broker_type}")
        return 1
    
    # Initialize dashboard
    dashboard = None
    if config['monitoring']['enable_dashboard']:
        dashboard_port = config['monitoring']['dashboard_port']
        dashboard = Dashboard(port=dashboard_port)
        dashboard.start()
        logger.info(f"✅ Dashboard available at: http://localhost:{dashboard_port}")
    
    # Initialize strategy
    strategy_config = config['strategy']
    logger.info(f"Initializing strategy for {strategy_config['symbol']}")
    
    strategy = LiveIntradayStrategy(
        broker=broker,
        symbol=strategy_config['symbol'],
        ml_confidence_threshold=strategy_config['ml_confidence_threshold'],
        stop_loss_pct=strategy_config['stop_loss_pct'],
        take_profit_pct=strategy_config['take_profit_pct'],
        max_position_pct=strategy_config['max_position_pct'],
        max_daily_loss_pct=strategy_config['max_daily_loss_pct'],
        max_trades_per_day=strategy_config['max_trades_per_day'],
        model_dir=strategy_config['model_dir'],
        dashboard=dashboard,
    )
    
    logger.info("✅ Strategy initialized")
    
    # Display configuration
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Symbol: {strategy_config['symbol']}")
    logger.info(f"  Confidence Threshold: {strategy_config['ml_confidence_threshold']}")
    logger.info(f"  Stop Loss: {strategy_config['stop_loss_pct']*100:.1f}%")
    logger.info(f"  Take Profit: {strategy_config['take_profit_pct']*100:.1f}%")
    logger.info(f"  Max Position: {strategy_config['max_position_pct']*100:.0f}%")
    logger.info(f"  Max Daily Loss: {strategy_config['max_daily_loss_pct']*100:.0f}%")
    logger.info(f"  Max Trades/Day: {strategy_config['max_trades_per_day']}")
    logger.info("")
    
    # Start strategy
    try:
        logger.info("🚀 Starting live trading...")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        # Start strategy in background
        strategy_task = asyncio.create_task(strategy.start())
        
        # Start tick simulation for mock broker or Angel One
        if isinstance(broker, MockBroker):
            logger.info("Starting tick simulation...")
            tick_task = asyncio.create_task(broker.simulate_ticks(interval=1.0))
            
            # Wait for both tasks
            await asyncio.gather(strategy_task, tick_task)
        elif isinstance(broker, AngelOneDataBroker):
            logger.info("Starting realistic tick simulation (Angel One data mode)...")
            tick_task = asyncio.create_task(broker.simulate_realistic_ticks(interval=1.0))
            
            # Wait for both tasks
            await asyncio.gather(strategy_task, tick_task)
        else:
            await strategy_task
    
    except KeyboardInterrupt:
        logger.info("")
        logger.info("⚠️  Keyboard interrupt received")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        logger.info("")
        logger.info("Stopping strategy...")
        await strategy.stop()
        logger.info("✅ Strategy stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
