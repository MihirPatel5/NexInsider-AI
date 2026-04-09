"""
backtesting/strategies/ml_strategy_optimized.py — Optimized ML-based trading strategy.

Enhanced version with optimized parameters based on backtesting results.
"""
import backtrader as bt
import numpy as np
import pandas as pd
from loguru import logger
from typing import Optional, Dict

from ml.regime_ensemble import RegimeAwareEnsemble
from ml.preprocessing import Preprocessor
from data.features.regime import detect_regime


class MLStrategyOptimized(bt.Strategy):
    """
    Optimized ML-based strategy with improved parameters.
    
    Key improvements over base MLStrategy:
    - Lower confidence threshold (0.55 vs 0.65)
    - Wider stop-loss (7% vs 5%)
    - Higher take-profit (12% vs 10%)
    - Larger position sizing (15% vs 10%)
    - Better trailing stop (4% vs 3%)
    """
    
    params = (
        # OPTIMIZED PARAMETERS (based on backtesting)
        ("ml_confidence_threshold", 0.55),  # Lower threshold = more trades
        ("stop_loss_pct", 0.07),            # Wider stop = less premature exits
        ("take_profit_pct", 0.12),          # Higher target = capture bigger moves
        ("trailing_stop_pct", 0.04),        # Better profit protection
        ("max_position_pct", 0.15),         # Larger positions = better returns
        
        # Risk management
        ("risk_manager", None),
        ("feature_cols", None),
        ("nifty_data", None),
        ("vix_value", 20.0),
        ("sentiment_score", 0.0),
        
        # Additional optimizations
        ("min_bars_required", 200),         # Minimum bars for indicators
        ("use_dynamic_stops", True),        # Enable dynamic stop-loss
        ("volatility_adjustment", True),    # Adjust stops based on volatility
    )
    
    def log(self, txt, dt=None):
        """Logging helper."""
        dt = dt or self.datas[0].datetime.date(0)
        logger.info(f"[MLStrategyOpt] {dt.isoformat()} | {txt}")
    
    def __init__(self):
        """Initialize strategy components."""
        # ML Components
        self.ensemble = RegimeAwareEnsemble()
        self.preprocessor = Preprocessor(scaling_type="standard")
        
        # State tracking
        self.order = None
        self.stop_price = None
        self.take_profit_price = None
        self.entry_price = None
        self.risk = self.p.risk_manager
        
        # Feature storage
        self.current_features = None
        self.prediction_cache = {}
        
        # Volatility tracking for dynamic stops
        self.recent_volatility = []
        
        self.log(
            f"Initialized with optimized parameters: "
            f"conf={self.p.ml_confidence_threshold}, "
            f"stop={self.p.stop_loss_pct:.1%}, "
            f"target={self.p.take_profit_pct:.1%}"
        )
    
    def prenext(self):
        """Called before minimum period is met."""
        pass
    
    def next(self):
        """Main strategy logic called for each bar."""
        if self.order:  # Pending order
            return
        
        # Update volatility tracking
        self._update_volatility()
        
        # Check Risk Circuit Breakers
        if self.risk and not self._check_risk_limits():
            if self.position:
                self.log("Risk limits breached, closing position")
                self.close()
            return
        
        # Get ML prediction
        prediction = self._get_ml_prediction()
        
        if prediction is None:
            return
        
        # Execute trading logic
        if not self.position:
            self._handle_entry(prediction)
        else:
            self._handle_exit(prediction)
    
    def _update_volatility(self):
        """Update recent volatility for dynamic stops."""
        if len(self.data) < 20:
            return
        
        # Calculate 20-day volatility
        returns = [
            (self.data.close[-i] - self.data.close[-i-1]) / self.data.close[-i-1]
            for i in range(20)
        ]
        volatility = np.std(returns)
        
        self.recent_volatility.append(volatility)
        
        # Keep only last 60 days
        if len(self.recent_volatility) > 60:
            self.recent_volatility.pop(0)
    
    def _get_volatility_multiplier(self) -> float:
        """
        Get volatility multiplier for dynamic stops.
        
        Returns:
            Multiplier (1.0 = normal, >1.0 = wider stops, <1.0 = tighter stops)
        """
        if not self.recent_volatility or not self.p.volatility_adjustment:
            return 1.0
        
        current_vol = self.recent_volatility[-1]
        avg_vol = np.mean(self.recent_volatility)
        
        if avg_vol == 0:
            return 1.0
        
        # Scale stops based on current vs average volatility
        multiplier = current_vol / avg_vol
        
        # Limit multiplier to reasonable range (0.7 to 1.5)
        multiplier = max(0.7, min(1.5, multiplier))
        
        return multiplier
    
    def _check_risk_limits(self) -> bool:
        """Check if risk limits allow trading."""
        if not self.risk:
            return True
        
        current_pnl = self.broker.getvalue() - self.risk.initial_balance
        return self.risk.check_circuit_breakers(current_pnl)
    
    def _get_ml_prediction(self) -> Optional[Dict]:
        """Get ML prediction for current bar."""
        try:
            # Extract features
            features = self._extract_features()
            
            if features is None:
                return None
            
            # Get model probabilities
            model_probs = self._get_model_probabilities(features)
            
            # Get Nifty data for regime detection
            nifty_df = self._get_nifty_data()
            
            if nifty_df is None or len(nifty_df) < 200:
                self.log("Insufficient Nifty data for regime detection")
                return None
            
            # Combine predictions using regime-aware ensemble
            prediction = self.ensemble.combine(
                model_probs=model_probs,
                nifty_df=nifty_df,
                vix=self.p.vix_value,
                sentiment_score=self.p.sentiment_score,
            )
            
            self.log(
                f"Prediction: {prediction['signal']} "
                f"(conf={prediction['confidence']:.3f}, "
                f"regime={prediction['regime']})"
            )
            
            return prediction
        
        except Exception as e:
            logger.error(f"[MLStrategyOpt] Error getting prediction: {e}")
            return None
    
    def _extract_features(self) -> Optional[np.ndarray]:
        """Extract features from current bar."""
        try:
            if len(self.data) < self.p.min_bars_required:
                return None
            
            features = []
            
            # Price-based features
            close_prices = [self.data.close[-i] for i in range(20)]
            sma_20 = np.mean(close_prices)
            features.append((self.data.close[0] - sma_20) / sma_20)
            
            # Volume features
            volumes = [self.data.volume[-i] for i in range(20)]
            vol_avg = np.mean(volumes)
            features.append(self.data.volume[0] / vol_avg if vol_avg > 0 else 1.0)
            
            # Momentum features
            returns_5d = (self.data.close[0] - self.data.close[-5]) / self.data.close[-5]
            features.append(returns_5d)
            
            # Volatility features
            returns = [
                (self.data.close[-i] - self.data.close[-i-1]) / self.data.close[-i-1]
                for i in range(20)
            ]
            volatility = np.std(returns)
            features.append(volatility)
            
            return np.array(features).reshape(1, -1)
        
        except Exception as e:
            logger.error(f"[MLStrategyOpt] Error extracting features: {e}")
            return None
    
    def _get_model_probabilities(self, features: np.ndarray) -> Dict[str, np.ndarray]:
        """Get probability predictions from all models."""
        # Placeholder: Use feature-based heuristics
        feature_signal = features[0, 0]  # Distance from SMA
        
        if feature_signal > 0.02:  # Price above SMA
            base_probs = np.array([0.1, 0.3, 0.6])  # Bullish
        elif feature_signal < -0.02:  # Price below SMA
            base_probs = np.array([0.6, 0.3, 0.1])  # Bearish
        else:
            base_probs = np.array([0.2, 0.6, 0.2])  # Neutral
        
        # Add some noise
        noise = np.random.normal(0, 0.05, 3)
        probs = np.clip(base_probs + noise, 0, 1)
        probs = probs / probs.sum()
        
        return {
            "xgb": probs,
            "lstm": probs,
            "transformer": probs,
            "rl": probs,
        }
    
    def _get_nifty_data(self) -> Optional[pd.DataFrame]:
        """Get Nifty 50 data for regime detection."""
        if self.p.nifty_data is not None:
            return self.p.nifty_data
        
        # Generate synthetic Nifty data for testing
        dates = pd.date_range(end=pd.Timestamp.now(), periods=250, freq='D')
        nifty_df = pd.DataFrame({
            'time': dates,
            'open': np.random.randn(250).cumsum() + 18000,
            'high': np.random.randn(250).cumsum() + 18100,
            'low': np.random.randn(250).cumsum() + 17900,
            'close': np.random.randn(250).cumsum() + 18000,
            'volume': np.random.randint(1000000, 10000000, 250),
        })
        
        return nifty_df
    
    def _handle_entry(self, prediction: Dict):
        """Handle entry logic based on ML prediction."""
        signal = prediction["signal"]
        confidence = prediction["confidence"]
        
        # Only trade on BUY signals
        if signal != "BUY":
            return
        
        # Check confidence threshold
        if confidence < self.p.ml_confidence_threshold:
            self.log(
                f"Confidence {confidence:.3f} below threshold "
                f"{self.p.ml_confidence_threshold}"
            )
            return
        
        # Calculate position size
        price = self.data.close[0]
        
        # Apply volatility adjustment to stop-loss
        vol_multiplier = self._get_volatility_multiplier()
        adjusted_stop_pct = self.p.stop_loss_pct * vol_multiplier
        
        stop_loss_price = price * (1 - adjusted_stop_pct)
        
        qty = self._calculate_position_size(price, stop_loss_price, confidence)
        
        if qty <= 0:
            self.log("Position size calculation returned 0")
            return
        
        # Place order
        self.log(
            f"BUY SIGNAL: {qty} shares @ {price:.2f} "
            f"(conf={confidence:.3f}, regime={prediction['regime']}, "
            f"stop={adjusted_stop_pct:.1%})"
        )
        
        self.order = self.buy(size=qty)
        self.entry_price = price
        self.stop_price = stop_loss_price
        self.take_profit_price = price * (1 + self.p.take_profit_pct)
    
    def _handle_exit(self, prediction: Dict):
        """Handle exit logic for existing position."""
        current_price = self.data.close[0]
        
        # Check stop loss
        if current_price <= self.stop_price:
            self.log(f"STOP LOSS HIT @ {current_price:.2f}")
            self.order = self.close()
            return
        
        # Check take profit
        if current_price >= self.take_profit_price:
            self.log(f"TAKE PROFIT HIT @ {current_price:.2f}")
            self.order = self.close()
            return
        
        # Check ML signal reversal
        if prediction["signal"] == "SELL" and prediction["confidence"] > 0.7:
            self.log(
                f"ML SIGNAL REVERSAL @ {current_price:.2f} "
                f"(conf={prediction['confidence']:.3f})"
            )
            self.order = self.close()
            return
        
        # Update trailing stop
        new_stop = current_price * (1 - self.p.trailing_stop_pct)
        if new_stop > self.stop_price:
            self.stop_price = new_stop
            self.log(f"Trailing stop updated to {self.stop_price:.2f}")
    
    def _calculate_position_size(
        self,
        price: float,
        stop_loss_price: float,
        confidence: float,
    ) -> int:
        """Calculate position size based on risk management rules."""
        if self.risk:
            qty = self.risk.calculate_position_size(
                symbol=self.data._name,
                price=price,
                stop_loss_price=stop_loss_price,
                confidence=confidence,
            )
        else:
            # Simple position sizing
            portfolio_value = self.broker.getvalue()
            max_position_value = portfolio_value * self.p.max_position_pct
            qty = int(max_position_value / price)
        
        return max(0, qty)
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED: {order.executed.size} @ {order.executed.price:.2f} "
                    f"(value={order.executed.value:.2f}, comm={order.executed.comm:.2f})"
                )
            else:
                pnl = order.executed.pnl
                self.log(
                    f"SELL EXECUTED: {order.executed.size} @ {order.executed.price:.2f} "
                    f"(PnL={pnl:.2f}, comm={order.executed.comm:.2f})"
                )
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.status}")
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications."""
        if not trade.isclosed:
            return
        
        self.log(
            f"TRADE CLOSED: PnL={trade.pnl:.2f}, Net PnL={trade.pnlcomm:.2f}"
        )
    
    def stop(self):
        """Called when strategy stops."""
        self.log(
            f"Strategy finished. Final portfolio value: ₹{self.broker.getvalue():,.2f}"
        )
