"""
backtesting/strategies/intraday_ml_strategy.py - Intraday ML trading strategy for Nifty 50.

This strategy is specifically designed for intraday trading with:
- 5-minute candles
- Trading hours: 9:15 AM - 3:15 PM IST
- Tighter risk management (0.5-1% stops)
- Smaller profit targets (1-2%)
- Automatic square-off at 3:15 PM
- No overnight positions
"""
import backtrader as bt
import numpy as np
import pandas as pd
from loguru import logger
from typing import Optional, Dict
from datetime import time
import joblib
from pathlib import Path

from data.features.technical import FeatureEngineer


class IntradayMLStrategy(bt.Strategy):
    """
    Intraday ML-based strategy using trained XGBoost and Random Forest models.
    
    Features:
    - Intraday-specific trained models (61-62% accuracy)
    - Time-based trading rules (9:15 AM - 3:15 PM IST)
    - Automatic square-off at 3:15 PM
    - Tighter risk management for intraday
    - No overnight positions
    - Skip volatile opening (9:15-9:30 AM)
    - Reduced activity during lunch (12:30-1:30 PM)
    """
    
    params = (
        ("ml_confidence_threshold", 0.25),  # Lowered for more trades (was 0.30)
        ("stop_loss_pct", 0.008),           # 0.8% stop loss (tighter for intraday)
        ("take_profit_pct", 0.015),         # 1.5% take profit (smaller target)
        ("trailing_stop_pct", 0.005),       # 0.5% trailing stop
        ("max_position_pct", 0.40),         # 40% of portfolio per position (increased from 30%)
        ("max_daily_loss_pct", 0.03),       # 3% max daily loss (circuit breaker)
        ("max_trades_per_day", 15),         # Max 15 trades per day
        
        # Time-based rules (IST)
        ("market_open", time(9, 15)),       # Market opens at 9:15 AM
        ("skip_until", time(9, 30)),        # Skip first 15 minutes
        ("lunch_start", time(12, 30)),      # Lunch time starts
        ("lunch_end", time(13, 30)),        # Lunch time ends
        ("square_off_time", time(15, 10)),  # Start squaring off at 3:10 PM
        ("market_close", time(15, 15)),     # Market closes at 3:15 PM
        
        # Technical indicator signals (NEW - for more trades)
        ("use_technical_signals", True),    # Enable technical indicator signals
        ("rsi_oversold", 35),               # RSI oversold level
        ("rsi_overbought", 65),             # RSI overbought level
        
        # Model paths
        ("model_dir", "models/trained"),
        ("use_xgboost", True),
        ("use_random_forest", True),
    )
    
    def log(self, txt, dt=None):
        """Logging helper."""
        dt = dt or self.datas[0].datetime.datetime(0)
        logger.info(f"[IntradayML] {dt.strftime('%Y-%m-%d %H:%M:%S')} | {txt}")
    
    def __init__(self):
        """Initialize strategy components."""
        # Load trained intraday models
        self.xgb_model = None
        self.rf_model = None
        self.feature_names = None
        
        self._load_models()
        
        # Feature engineering
        self.feature_engineer = FeatureEngineer()
        
        # State tracking
        self.order = None
        self.stop_price = None
        self.take_profit_price = None
        self.entry_price = None
        self.entry_time = None
        
        # Daily tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.current_date = None
        self.initial_daily_value = None
        
        self.log("Initialized with intraday ML models (XGBoost 61.6%, RF 62.5%)")
        self.log(f"Trading hours: {self.p.skip_until} - {self.p.square_off_time}")
        self.log(f"Risk: {self.p.stop_loss_pct*100:.1f}% SL, {self.p.take_profit_pct*100:.1f}% TP")
    
    def _load_models(self):
        """Load trained intraday models."""
        try:
            model_dir = Path(self.p.model_dir)
            
            if self.p.use_xgboost:
                xgb_path = model_dir / "xgboost_intraday.joblib"
                if xgb_path.exists():
                    self.xgb_model = joblib.load(xgb_path)
                    logger.info(f"✅ Loaded XGBoost model from {xgb_path}")
                else:
                    logger.warning(f"XGBoost model not found: {xgb_path}")
            
            if self.p.use_random_forest:
                rf_path = model_dir / "random_forest_intraday.joblib"
                if rf_path.exists():
                    self.rf_model = joblib.load(rf_path)
                    logger.info(f"✅ Loaded Random Forest model from {rf_path}")
                else:
                    logger.warning(f"Random Forest model not found: {rf_path}")
            
            # Load feature names
            features_path = model_dir / "feature_names_intraday.joblib"
            if features_path.exists():
                self.feature_names = joblib.load(features_path)
                logger.info(f"✅ Loaded {len(self.feature_names)} feature names")
            else:
                logger.warning(f"Feature names not found: {features_path}")
        
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def prenext(self):
        """Called before minimum period is met."""
        pass
    
    def next(self):
        """Main strategy logic called for each bar."""
        # Get current time
        current_dt = self.datas[0].datetime.datetime(0)
        current_time = current_dt.time()
        current_date = current_dt.date()
        
        # Reset daily counters if new day
        if self.current_date != current_date:
            self._reset_daily_counters(current_date)
        
        # Check if we have a pending order
        if self.order:
            return
        
        # 1. Check time-based rules
        if not self._is_trading_time(current_time):
            return
        
        # 2. Check if we need to square off (near market close)
        if current_time >= self.p.square_off_time:
            if self.position:
                self.log(f"SQUARE OFF TIME - Closing position")
                self.order = self.close()
            return
        
        # 3. Check daily limits
        if not self._check_daily_limits():
            if self.position:
                self.log("Daily limits breached, closing position")
                self.order = self.close()
            return
        
        # 4. Get ML prediction
        prediction = self._get_ml_prediction()
        
        if prediction is None:
            return
        
        # 5. Execute trading logic
        if not self.position:
            self._handle_entry(prediction, current_time)
        else:
            self._handle_exit(prediction, current_time)
    
    def _reset_daily_counters(self, new_date):
        """Reset daily tracking counters."""
        if self.current_date is not None:
            self.log(f"Day ended: {self.daily_trades} trades, PnL: ₹{self.daily_pnl:.2f}")
        
        self.current_date = new_date
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.initial_daily_value = self.broker.getvalue()
        
        self.log(f"New trading day: {new_date}")
    
    def _is_trading_time(self, current_time: time) -> bool:
        """
        Check if current time is within trading hours.
        
        Rules:
        - Skip first 15 minutes (9:15-9:30 AM) - high volatility
        - Reduce activity during lunch (12:30-1:30 PM)
        - Stop new trades at 3:10 PM (square off time)
        """
        # Before market opens or after square-off time
        if current_time < self.p.market_open or current_time >= self.p.square_off_time:
            return False
        
        # Skip first 15 minutes
        if current_time < self.p.skip_until:
            return False
        
        # During lunch time - only allow exits, no new entries
        if self.p.lunch_start <= current_time < self.p.lunch_end:
            if not self.position:  # Don't enter during lunch
                return False
        
        return True
    
    def _check_daily_limits(self) -> bool:
        """
        Check if daily limits allow trading.
        
        Returns:
            True if trading is allowed, False otherwise
        """
        # Check max trades per day
        if self.daily_trades >= self.p.max_trades_per_day:
            return False
        
        # Check max daily loss (circuit breaker)
        if self.initial_daily_value is not None:
            current_value = self.broker.getvalue()
            daily_loss_pct = (current_value - self.initial_daily_value) / self.initial_daily_value
            
            if daily_loss_pct < -self.p.max_daily_loss_pct:
                self.log(f"Daily loss limit breached: {daily_loss_pct*100:.2f}%")
                return False
        
        return True
    
    def _get_ml_prediction(self) -> Optional[Dict]:
        """
        Get ML prediction using trained intraday models.
        
        Returns:
            Dict with signal, confidence, probs
            or None if prediction cannot be made
        """
        try:
            # Extract features
            features = self._extract_features()
            
            if features is None:
                return None
            
            # Get predictions from models
            predictions = []
            confidences = []
            
            if self.xgb_model is not None:
                xgb_proba = self.xgb_model.predict_proba(features)[0]
                xgb_pred = np.argmax(xgb_proba)
                xgb_conf = xgb_proba[xgb_pred]
                predictions.append(xgb_pred)
                confidences.append(xgb_conf)
            
            if self.rf_model is not None:
                rf_proba = self.rf_model.predict_proba(features)[0]
                rf_pred = np.argmax(rf_proba)
                rf_conf = rf_proba[rf_pred]
                predictions.append(rf_pred)
                confidences.append(rf_conf)
            
            if not predictions:
                return None
            
            # Ensemble: Average predictions
            avg_pred = int(np.round(np.mean(predictions)))
            avg_conf = np.mean(confidences)
            
            # Map prediction to signal
            # 0 = SELL, 1 = HOLD, 2 = BUY
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
    
    def _extract_features(self) -> Optional[np.ndarray]:
        """
        Extract features from current bar using FeatureEngineer.
        
        Uses same 27 technical indicators as training.
        """
        try:
            # Need at least 200 bars for indicators
            if len(self.data) < 200:
                return None
            
            # Build DataFrame from recent bars
            lookback = min(250, len(self.data))
            
            df_data = {
                'open': [self.data.open[-i] for i in range(lookback - 1, -1, -1)],
                'high': [self.data.high[-i] for i in range(lookback - 1, -1, -1)],
                'low': [self.data.low[-i] for i in range(lookback - 1, -1, -1)],
                'close': [self.data.close[-i] for i in range(lookback - 1, -1, -1)],
                'volume': [self.data.volume[-i] for i in range(lookback - 1, -1, -1)],
            }
            
            df = pd.DataFrame(df_data)
            
            # Extract all 27 features
            features_df = self.feature_engineer.extract_features(df, include_all=True)
            
            # Get the most recent row (current bar features)
            latest_features = features_df.iloc[-1]
            
            # Select only the features used in training
            if self.feature_names is not None:
                X = pd.DataFrame([latest_features[self.feature_names]], columns=self.feature_names)
            else:
                X = pd.DataFrame([latest_features])
            
            # Handle NaN values
            X = X.ffill().bfill().fillna(0)
            
            return X.values
        
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def _handle_entry(self, prediction: Dict, current_time: time):
        """
        Handle entry logic based on ML prediction.
        
        Args:
            prediction: Dict with signal, confidence
            current_time: Current time
        """
        signal = prediction["signal"]
        confidence = prediction["confidence"]
        
        # Only trade on BUY signals (can extend to SELL for shorting)
        if signal != "BUY":
            return
        
        # Check confidence threshold
        if confidence < self.p.ml_confidence_threshold:
            return
        
        # Calculate position size
        price = self.data.close[0]
        stop_loss_price = price * (1 - self.p.stop_loss_pct)
        
        qty = self._calculate_position_size(price, stop_loss_price, confidence)
        
        if qty <= 0:
            return
        
        # Place order
        self.log(
            f"BUY SIGNAL: {qty} shares @ ₹{price:.2f} "
            f"(conf={confidence:.3f})"
        )
        
        self.order = self.buy(size=qty)
        self.entry_price = price
        self.entry_time = current_time
        self.stop_price = stop_loss_price
        self.take_profit_price = price * (1 + self.p.take_profit_pct)
        
        self.daily_trades += 1
    
    def _handle_exit(self, prediction: Dict, current_time: time):
        """
        Handle exit logic for existing position.
        
        Args:
            prediction: Dict with signal, confidence
            current_time: Current time
        """
        current_price = self.data.close[0]
        
        # Exit conditions:
        # 1. Stop loss hit
        # 2. Take profit hit
        # 3. ML signal reverses with high confidence
        # 4. Trailing stop
        # 5. Time-based exit (held too long)
        
        # Check stop loss
        if current_price <= self.stop_price:
            self.log(f"STOP LOSS HIT @ ₹{current_price:.2f}")
            self.order = self.close()
            return
        
        # Check take profit
        if current_price >= self.take_profit_price:
            self.log(f"TAKE PROFIT HIT @ ₹{current_price:.2f}")
            self.order = self.close()
            return
        
        # Check ML signal reversal
        if prediction["signal"] == "SELL" and prediction["confidence"] > 0.65:
            self.log(
                f"ML SIGNAL REVERSAL @ ₹{current_price:.2f} "
                f"(conf={prediction['confidence']:.3f})"
            )
            self.order = self.close()
            return
        
        # Update trailing stop (move to breakeven after 0.5% profit)
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        
        if pnl_pct > 0.005:  # 0.5% profit
            # Move stop to breakeven or better
            new_stop = max(self.entry_price, current_price * (1 - self.p.trailing_stop_pct))
            
            if new_stop > self.stop_price:
                self.stop_price = new_stop
                self.log(f"Trailing stop updated to ₹{self.stop_price:.2f}")
    
    def _calculate_position_size(
        self,
        price: float,
        stop_loss_price: float,
        confidence: float,
    ) -> int:
        """
        Calculate position size based on risk management rules.
        
        For intraday, we use a larger position size (30% of portfolio)
        since we're taking smaller risks per trade.
        
        Args:
            price: Entry price
            stop_loss_price: Stop loss price
            confidence: ML prediction confidence
        
        Returns:
            Number of shares to buy
        """
        # Simple position sizing: max_position_pct of portfolio
        portfolio_value = self.broker.getvalue()
        max_position_value = portfolio_value * self.p.max_position_pct
        
        # Scale by confidence (higher confidence = larger position)
        confidence_multiplier = min(confidence / self.p.ml_confidence_threshold, 1.5)
        adjusted_position_value = max_position_value * confidence_multiplier
        
        qty = int(adjusted_position_value / price)
        
        return max(0, qty)
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED: {order.executed.size} @ ₹{order.executed.price:.2f} "
                    f"(value=₹{order.executed.value:.2f}, comm=₹{order.executed.comm:.2f})"
                )
            else:
                pnl = order.executed.pnl
                self.daily_pnl += pnl
                
                self.log(
                    f"SELL EXECUTED: {order.executed.size} @ ₹{order.executed.price:.2f} "
                    f"(PnL=₹{pnl:.2f}, comm=₹{order.executed.comm:.2f})"
                )
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.status}")
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications."""
        if not trade.isclosed:
            return
        
        self.log(
            f"TRADE CLOSED: PnL=₹{trade.pnl:.2f}, Net PnL=₹{trade.pnlcomm:.2f}"
        )
    
    def stop(self):
        """Called when strategy stops."""
        self.log(
            f"Strategy finished. Final portfolio value: ₹{self.broker.getvalue():,.2f}"
        )
        self.log(f"Total trades: {self.daily_trades}, Final daily PnL: ₹{self.daily_pnl:.2f}")
