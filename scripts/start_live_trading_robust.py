"""
scripts/start_live_trading_robust.py - Robust live trading system with auto-restart.

This version includes:
- Better error handling
- Automatic restart on failure
- Detailed logging
- Graceful shutdown

Usage:
    python3 scripts/start_live_trading_robust.py
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import argparse
import yaml
import signal
from datetime import datetime
from loguru import logger

from trading.broker import MockBroker, AngelOneDataBroker
from trading.strategies.live_intraday_strategy import LiveIntradayStrategy
from trading.monitoring import Dashboard


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    logger.info("")
    logger.warning("⚠️  Shutdown signal received")
    shutdown_requested = True


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


async def run_trading_session(config: dict, dashboard: Dashboard = None):
    """Run a single trading session."""
    # Initialize broker
    broker_type = config['broker']['type']
    
    if broker_type == 'mock' or config['paper_trading']['enabled']:
        initial_balance = config['broker']['mock']['initial_balance']
        broker = MockBroker(initial_balance=initial_balance)
        logger.info(f"✅ MockBroker initialized with ₹{initial_balance:,.2f}")
    
    elif broker_type == 'angelone_data':
        initial_balance = config['broker']['angelone_data']['initial_balance']
        broker = AngelOneDataBroker(initial_balance=initial_balance)
        logger.info(f"✅ AngelOneDataBroker initialized (PAPER TRADING)")
    
    else:
        logger.error(f"Unknown broker type: {broker_type}")
        return False
    
    # Initialize strategy
    strategy_config = config['strategy']
    
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
    
    try:
        # Start strategy
        strategy_task = asyncio.create_task(strategy.start())
        
        # Start tick simulation
        if isinstance(broker, (MockBroker, AngelOneDataBroker)):
            if isinstance(broker, AngelOneDataBroker):
                tick_task = asyncio.create_task(broker.simulate_realistic_ticks(interval=1.0))
            else:
                tick_task = asyncio.create_task(broker.simulate_ticks(interval=1.0))
            
            # Wait for either task to complete or shutdown signal
            while not shutdown_requested:
                # Check if tasks are still running
                if strategy_task.done():
                    logger.warning("⚠️  Strategy task completed unexpectedly")
                    break
                if tick_task.done():
                    logger.warning("⚠️  Tick task completed unexpectedly")
                    break
                
                await asyncio.sleep(1)
            
            # Cancel tasks
            if not strategy_task.done():
                strategy_task.cancel()
            if not tick_task.done():
                tick_task.cancel()
        else:
            await strategy_task
        
        # Stop strategy gracefully
        await strategy.stop()
        logger.info("✅ Strategy stopped gracefully")
        return True
    
    except asyncio.CancelledError:
        logger.info("⚠️  Tasks cancelled")
        await strategy.stop()
        return True
    
    except Exception as e:
        logger.error(f"❌ Error in trading session: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await strategy.stop()
        except:
            pass
        
        return False


async def main():
    """Main entry point with auto-restart."""
    global shutdown_requested
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Start robust live trading system")
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
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Disable automatic restart on failure"
    )
    args = parser.parse_args()
    
    # Load configuration
    logger.info("="*80)
    logger.info("ROBUST LIVE TRADING SYSTEM")
    logger.info("="*80)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Config: {args.config}")
    logger.info("")
    
    config = load_config(args.config)
    
    # Override with paper trading if specified
    if args.paper:
        logger.info("📄 PAPER TRADING MODE ENABLED")
        config['paper_trading']['enabled'] = True
        config['broker']['type'] = 'mock'
    
    # Initialize dashboard (once, shared across restarts)
    dashboard = None
    if config['monitoring']['enable_dashboard']:
        dashboard_port = config['monitoring']['dashboard_port']
        dashboard = Dashboard(port=dashboard_port)
        dashboard.start()
        logger.info(f"✅ Dashboard: http://localhost:{dashboard_port}")
    
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Symbol: {config['strategy']['symbol']}")
    logger.info(f"  Broker: {config['broker']['type']}")
    logger.info(f"  Auto-restart: {not args.no_restart}")
    logger.info("")
    
    # Main loop with auto-restart
    restart_count = 0
    max_restarts = 10
    
    while not shutdown_requested:
        logger.info("="*80)
        logger.info(f"STARTING TRADING SESSION (Attempt {restart_count + 1})")
        logger.info("="*80)
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        try:
            success = await run_trading_session(config, dashboard)
            
            if shutdown_requested:
                logger.info("✅ Shutdown completed successfully")
                break
            
            if success:
                logger.info("✅ Session completed successfully")
                if args.no_restart:
                    break
            else:
                logger.warning("⚠️  Session failed")
                restart_count += 1
                
                if restart_count >= max_restarts:
                    logger.error(f"❌ Max restarts ({max_restarts}) reached. Stopping.")
                    break
                
                if args.no_restart:
                    break
                
                # Wait before restart
                wait_time = min(restart_count * 5, 30)  # Max 30 seconds
                logger.info(f"⏳ Waiting {wait_time}s before restart...")
                await asyncio.sleep(wait_time)
        
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            
            if args.no_restart:
                break
            
            restart_count += 1
            if restart_count >= max_restarts:
                logger.error(f"❌ Max restarts ({max_restarts}) reached. Stopping.")
                break
            
            wait_time = min(restart_count * 5, 30)
            logger.info(f"⏳ Waiting {wait_time}s before restart...")
            await asyncio.sleep(wait_time)
    
    logger.info("")
    logger.info("="*80)
    logger.info("SYSTEM SHUTDOWN")
    logger.info("="*80)
    logger.info(f"Total restarts: {restart_count}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("")
        logger.info("✅ Shutdown complete")
        sys.exit(0)
