"""
trading/strategies/live_intraday_strategy.py - Live intraday trading strategy.

Adapts the backtested IntradayMLStrategy for live trading.
"""
import asyncio
from typing import Optional, Dict
from datetime import datetime, time
from loguru import logger
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from trading.broker import BaseBroker, OrderSide, OrderType
from trading.data import CandleBuilder
from trading.data.data_saver import DataSaver
from trading.monitoring import Dashboard
from data.features.technical import FeatureEngineer


class LiveIntradayStrategy:
    """
    Live intraday ML trading strategy.
    
    Executes the same logic as backtested strategy but with live data.
    """
    
    def __init__(
        self,
        broker: BaseBroker,
        symbol: str = "NIFTY50",
        ml_confidence_threshold: float = 0.35,
        stop_loss_pct: float = 0.008,
        take_profit_pct: float = 0.015,
        max_position_pct: float = 0.30,
        max_daily_loss_pct: float = 0.03,
        max_trades_per_day: int = 15,
        model_dir: str = "models/trained",
        dashboard: Optional[Dashboard] = None,
    ):
        """
        Initialize live strategy.
        
        Args:
            broker: Broker instance
            symbol: Trading symbol
            ml_confidence_threshold: ML confidence threshold
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            max_position_pct: Max position size as % of capital
            max_daily_loss_pct: Max daily loss percentage
            max_trades_per_day: Max trades per day
            model_dir: Directory with trained models
            dashboard: Optional dashboard for monitoring
        """
        self.broker = broker
        self.symbol = symbol
        self.ml_confidence_threshold = ml_confidence_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_trades_per_day = max_trades_per_day
        self.dashboard = dashboard
        
        # Load models
        self.xgb_model = None
        self.rf_model = None
        self.feature_names = None
        self._load_models(model_dir)
        
        # Feature engineering
        self.feature_engineer = FeatureEngineer()
        
        # Data saver for storing candles to database
        self.data_saver = DataSaver(
            db_host="localhost",
            db_port=5432,
            db_name="algotrading",
            db_user="postgres",
            db_password="postgres",
            batch_size=50  # Save every 50 candles or 60 seconds
        )
        
        # Candle builder for tick aggregation
        self.candle_builder = CandleBuilder(
            interval_minutes=5,
            on_candle_callback=self._on_candle_async_wrapper
        )
        
        # State tracking
        self.position = None
        self.entry_price = None
        self.stop_price = None
        self.take_profit_price = None
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.current_date = None
        self.initial_daily_balance = None
        
        # Data buffer for feature calculation
        self.candle_buffer = []
        self.max_buffer_size = 250  # Keep last 250 candles
        
        # Trading hours (IST)
        self.market_open = time(9, 15)
        self.skip_until = time(9, 30)
        self.lunch_start = time(12, 30)
        self.lunch_end = time(13, 30)
        self.square_off_time = time(15, 10)
        self.market_close = time(15, 15)
        
        self.running = False
        
        logger.info(f"LiveIntradayStrategy initialized for {symbol}")
        logger.info(f"Confidence threshold: {ml_confidence_threshold}")
        logger.info(f"Risk: {stop_loss_pct*100:.1f}% SL, {take_profit_pct*100:.1f}% TP")
    
    def _load_models(self, model_dir: str):
        """Load trained ML models."""
        try:
            model_path = Path(model_dir)
            
            xgb_path = model_path / "xgboost_intraday.joblib"
            if xgb_path.exists():
                self.xgb_model = joblib.load(xgb_path)
                logger.info(f"✅ Loaded XGBoost model")
            
            rf_path = model_path / "random_forest_intraday.joblib"
            if rf_path.exists():
                self.rf_model = joblib.load(rf_path)
                logger.info(f"✅ Loaded Random Forest model")
            
            features_path = model_path / "feature_names_intraday.joblib"
            if features_path.exists():
                self.feature_names = joblib.load(features_path)
                logger.info(f"✅ Loaded {len(self.feature_names)} feature names")
        
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise
    
    async def start(self):
        """Start the live trading strategy."""
        logger.info("="*60)
        logger.info("STARTING LIVE INTRADAY STRATEGY")
        logger.info("="*60)
        
        self.running = True
        
        # Update dashboard
        if self.dashboard:
            self.dashboard.update_status("RUNNING")
        
        # Connect to database for data saving
        await self.data_saver.connect()
        await self.data_saver.start_auto_flush(interval=60.0)  # Flush every 60 seconds
        logger.info("✅ Data saver connected - will save candles to database")
        
        # Connect to broker
        await self.broker.connect()
        
        # Subscribe to tick data
        await self.broker.subscribe_ticks([self.symbol])
        
        # Register callbacks
        self.broker.on_tick(self._on_tick)
        self.broker.on_order_update(self._on_order_update)
        
        logger.info(f"✅ Strategy started for {self.symbol}")
        logger.info(f"Trading hours: {self.skip_until} - {self.square_off_time}")
        
        # Main loop
        while self.running:
            # Update dashboard with current state
            if self.dashboard:
                balance = await self.broker.get_balance()
                self.dashboard.update_balance(balance)
                
                position = await self.broker.get_position(self.symbol)
                if position:
                    self.dashboard.update_position({
                        'symbol': position.symbol,
                        'quantity': position.quantity,
                        'average_price': position.average_price,
                        'last_price': position.last_price,
                        'pnl': position.pnl,
                        'pnl_percent': position.pnl_percent,
                    })
                else:
                    self.dashboard.update_position(None)
                
                self.dashboard.update_daily_stats(self.daily_pnl, self.daily_trades)
            
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the live trading strategy."""
        logger.info("Stopping live strategy...")
        self.running = False
        
        # Update dashboard
        if self.dashboard:
            self.dashboard.update_status("STOPPED")
        
        # Close any open positions
        if self.position:
            logger.info("Closing open position...")
            await self._close_position()
        
        # Stop data saver and disconnect
        await self.data_saver.stop_auto_flush()
        await self.data_saver.disconnect()
        logger.info("✅ Data saver stopped - all candles saved")
        
        # Unsubscribe and disconnect
        await self.broker.unsubscribe_ticks([self.symbol])
        await self.broker.disconnect()
        
        logger.info("✅ Strategy stopped")
    
    async def _on_tick(self, tick):
        """Handle incoming tick data."""
        # Add tick to candle builder
        self.candle_builder.add_tick(
            symbol=tick.symbol,
            price=tick.last_price,
            volume=tick.volume,
            timestamp=tick.timestamp
        )
    
    def _on_candle_async_wrapper(self, candle: Dict):
        """Wrapper to handle candle callback in async context."""
        # Schedule the async handler
        asyncio.create_task(self._on_candle(candle))
    
    async def _on_candle(self, candle: Dict):
        """
        Handle new candle data.
        
        Args:
            candle: Dict with OHLCV data
        """
        # Save candle to database
        await self.data_saver.save_candle(
            symbol=candle['symbol'],
            timestamp=candle['time'],
            open_price=candle['open'],
            high_price=candle['high'],
            low_price=candle['low'],
            close_price=candle['close'],
            volume=candle['volume'],
            exchange="NSE",
            interval="5m"
        )
        
        # Add to buffer
        self.candle_buffer.append(candle)
        if len(self.candle_buffer) > self.max_buffer_size:
            self.candle_buffer.pop(0)
        
        # Check if we have enough data
        if len(self.candle_buffer) < 200:
            return
        
        # Get current time
        current_time = datetime.now().time()
        current_date = datetime.now().date()
        
        # Reset daily counters if new day
        if self.current_date != current_date:
            await self._reset_daily_counters(current_date)
        
        # Check trading hours
        if not self._is_trading_time(current_time):
            return
        
        # Square off near market close
        if current_time >= self.square_off_time:
            if self.position:
                logger.info("SQUARE OFF TIME - Closing position")
                await self._close_position()
            return
        
        # Check daily limits
        if not await self._check_daily_limits():
            if self.position:
                logger.info("Daily limits breached, closing position")
                await self._close_position()
            return
        
        # Get ML prediction
        prediction = self._get_ml_prediction()
        
        if prediction is None:
            return
        
        # Execute trading logic
        if not self.position:
            await self._handle_entry(prediction, candle)
        else:
            await self._handle_exit(prediction, candle)
    
    async def _reset_daily_counters(self, new_date):
        """Reset daily tracking counters."""
        if self.current_date is not None:
            logger.info(f"Day ended: {self.daily_trades} trades, PnL: ₹{self.daily_pnl:.2f}")
        
        self.current_date = new_date
        self.daily_trades = 0
        self.daily_pnl = 0.0
        
        balance = await self.broker.get_balance()
        self.initial_daily_balance = balance['total']
        
        logger.info(f"New trading day: {new_date}")
    
    def _is_trading_time(self, current_time: time) -> bool:
        """Check if current time is within trading hours."""
        if current_time < self.market_open or current_time >= self.square_off_time:
            return False
        
        if current_time < self.skip_until:
            return False
        
        if self.lunch_start <= current_time < self.lunch_end:
            if not self.position:
                return False
        
        return True
    
    async def _check_daily_limits(self) -> bool:
        """Check if daily limits allow trading."""
        if self.daily_trades >= self.max_trades_per_day:
            return False
        
        if self.initial_daily_balance is not None:
            balance = await self.broker.get_balance()
            daily_loss_pct = (balance['total'] - self.initial_daily_balance) / self.initial_daily_balance
            
            if daily_loss_pct < -self.max_daily_loss_pct:
                logger.warning(f"Daily loss limit breached: {daily_loss_pct*100:.2f}%")
                return False
        
        return True
    
    def _get_ml_prediction(self) -> Optional[Dict]:
        """Get ML prediction from current data."""
        try:
            # Extract features from buffer
            df = pd.DataFrame(self.candle_buffer)
            features_df = self.feature_engineer.extract_features(df, include_all=True)
            
            # Get latest features
            latest_features = features_df.iloc[-1]
            
            if self.feature_names is not None:
                X = pd.DataFrame([latest_features[self.feature_names]], columns=self.feature_names)
            else:
                X = pd.DataFrame([latest_features])
            
            X = X.ffill().bfill().fillna(0)
            
            # Get predictions
            predictions = []
            confidences = []
            
            if self.xgb_model is not None:
                xgb_proba = self.xgb_model.predict_proba(X.values)[0]
                xgb_pred = np.argmax(xgb_proba)
                predictions.append(xgb_pred)
                confidences.append(xgb_proba[xgb_pred])
            
            if self.rf_model is not None:
                rf_proba = self.rf_model.predict_proba(X.values)[0]
                rf_pred = np.argmax(rf_proba)
                predictions.append(rf_pred)
                confidences.append(rf_proba[rf_pred])
            
            if not predictions:
                return None
            
            # Ensemble
            avg_pred = int(np.round(np.mean(predictions)))
            avg_conf = np.mean(confidences)
            
            signal_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
            signal = signal_map.get(avg_pred, "HOLD")
            
            return {
                "signal": signal,
                "confidence": avg_conf,
                "prediction": avg_pred,
            }
        
        except Exception as e:
            logger.error(f"Error getting prediction: {e}")
            return None
    
    async def _handle_entry(self, prediction: Dict, candle: Dict):
        """Handle entry logic."""
        signal = prediction["signal"]
        confidence = prediction["confidence"]
        
        if signal != "BUY":
            return
        
        if confidence < self.ml_confidence_threshold:
            return
        
        # Calculate position size
        balance = await self.broker.get_balance()
        max_position_value = balance['available'] * self.max_position_pct
        
        price = candle['close']
        quantity = int(max_position_value / price)
        
        if quantity <= 0:
            return
        
        # Place order
        logger.info(f"🔵 BUY SIGNAL: {quantity} @ ₹{price:.2f} (conf={confidence:.3f})")
        
        try:
            order = await self.broker.place_order(
                symbol=self.symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                order_type=OrderType.MARKET
            )
            
            self.entry_price = price
            self.stop_price = price * (1 - self.stop_loss_pct)
            self.take_profit_price = price * (1 + self.take_profit_pct)
            self.daily_trades += 1
            
            logger.info(f"✅ Order placed: {order.order_id}")
        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
    
    async def _handle_exit(self, prediction: Dict, candle: Dict):
        """Handle exit logic."""
        price = candle['close']
        
        # Check stop loss
        if price <= self.stop_price:
            logger.info(f"🔴 STOP LOSS HIT @ ₹{price:.2f}")
            await self._close_position()
            return
        
        # Check take profit
        if price >= self.take_profit_price:
            logger.info(f"🟢 TAKE PROFIT HIT @ ₹{price:.2f}")
            await self._close_position()
            return
        
        # Check signal reversal
        if prediction["signal"] == "SELL" and prediction["confidence"] > 0.65:
            logger.info(f"🔴 SIGNAL REVERSAL @ ₹{price:.2f}")
            await self._close_position()
            return
    
    async def _close_position(self):
        """Close current position."""
        try:
            position = await self.broker.get_position(self.symbol)
            if not position or position.quantity == 0:
                return
            
            order = await self.broker.place_order(
                symbol=self.symbol,
                side=OrderSide.SELL,
                quantity=position.quantity,
                order_type=OrderType.MARKET
            )
            
            self.position = None
            self.entry_price = None
            self.stop_price = None
            self.take_profit_price = None
            
            logger.info(f"✅ Position closed: {order.order_id}")
        
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def _on_order_update(self, order):
        """Handle order updates."""
        logger.info(f"📝 Order update: {order.order_id} | {order.status.value}")
        
        if order.status.value == "COMPLETE":
            if order.side == OrderSide.BUY:
                self.position = order
                logger.info(f"✅ Position opened: {order.quantity} @ ₹{order.average_price:.2f}")
            else:
                pnl = (order.average_price - self.entry_price) * order.quantity if self.entry_price else 0
                self.daily_pnl += pnl
                logger.info(f"✅ Position closed: PnL = ₹{pnl:.2f}")
