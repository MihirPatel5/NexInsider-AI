"""
backtesting/strategies/ml_strategy.py — ML-based trading strategy.

Integrates RegimeAwareEnsemble for predictions with proper feature engineering.
Uses confidence-based position sizing and dynamic risk management.
"""
import backtrader as bt
import numpy as np
import pandas as pd
from loguru import logger
from typing import Optional, Dict

from ml.regime_ensemble import RegimeAwareEnsemble
from ml.preprocessing import Preprocessor
from data.features.regime import detect_regime
from data.features.technical import FeatureEngineer


class MLStrategy(bt.Strategy):
    """
    ML-based strategy using RegimeAwareEnsemble for predictions.
    
    Features:
    - Regime-aware model selection
    - Confidence-based position sizing
    - Dynamic stop-loss and take-profit
    - Risk management integration
    """
    
    params = (
        ("ml_confidence_threshold", 0.65),  # Minimum confidence to trade
        ("stop_loss_pct", 0.05),            # Initial stop loss (5%)
        ("take_profit_pct", 0.10),          # Take profit target (10%)
        ("trailing_stop_pct", 0.03),        # Trailing stop (3%)
        ("max_position_pct", 0.10),         # Max 10% of portfolio per position
        ("risk_manager", None),             # RiskManager instance
        ("feature_cols", None),             # List of feature column names
        ("nifty_data", None),               # Nifty 50 data for regime detection
        ("vix_value", 20.0),                # Current VIX value
        ("sentiment_score", 0.0),           # Sentiment score (-1 to 1)
    )
    
    def log(self, txt, dt=None):
        """Logging helper."""
        dt = dt or self.datas[0].datetime.date(0)
        logger.info(f"[MLStrategy] {dt.isoformat()} | {txt}")
    
    def __init__(self):
        """Initialize strategy components."""
        # ML Components
        self.ensemble = RegimeAwareEnsemble()
        self.preprocessor = Preprocessor(scaling_type="standard")
        self.feature_engineer = FeatureEngineer()
        
        # State tracking
        self.order = None
        self.stop_price = None
        self.take_profit_price = None
        self.entry_price = None
        self.risk = self.p.risk_manager
        
        # Feature storage for current bar
        self.current_features = None
        
        # Model predictions cache (to avoid recalculation)
        self.prediction_cache = {}
        
        # Historical data buffer for feature calculation
        self.data_buffer = []
        
        self.log("Initialized with regime-aware ensemble and 27 technical indicators")
    
    def prenext(self):
        """Called before minimum period is met."""
        pass
    
    def next(self):
        """Main strategy logic called for each bar."""
        if self.order:  # Pending order
            return
        
        # 1. Check Risk Circuit Breakers
        if self.risk and not self._check_risk_limits():
            if self.position:
                self.log("Risk limits breached, closing position")
                self.close()
            return
        
        # 2. Get ML prediction
        prediction = self._get_ml_prediction()
        
        if prediction is None:
            return
        
        # 3. Execute trading logic
        if not self.position:
            self._handle_entry(prediction)
        else:
            self._handle_exit(prediction)
    
    def _check_risk_limits(self) -> bool:
        """Check if risk limits allow trading."""
        if not self.risk:
            return True
        
        current_pnl = self.broker.getvalue() - self.risk.initial_balance
        return self.risk.check_circuit_breakers(current_pnl)
    
    def _get_ml_prediction(self) -> Optional[Dict]:
        """
        Get ML prediction for current bar.
        
        Returns:
            Dict with signal, confidence, probs, regime, weights_used
            or None if prediction cannot be made
        """
        try:
            # Get current bar data
            current_bar = {
                "open": self.data.open[0],
                "high": self.data.high[0],
                "low": self.data.low[0],
                "close": self.data.close[0],
                "volume": self.data.volume[0],
            }
            
            # Extract features (this would normally come from feature engineering)
            # For now, we'll use a simplified approach
            features = self._extract_features()
            
            if features is None:
                return None
            
            # Get model probabilities (placeholder - would load actual models)
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
            logger.error(f"[MLStrategy] Error getting prediction: {e}")
            return None
    
    def _extract_features(self) -> Optional[np.ndarray]:
        """
        Extract features from current bar using FeatureEngineer.
        
        Uses 27 technical indicators for comprehensive market analysis.
        """
        try:
            # Need at least 200 bars for indicators
            if len(self.data) < 200:
                return None
            
            # Build DataFrame from recent bars (need 200+ for all indicators)
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
            current_features = features_df.iloc[-1].values
            
            # Reshape for model input
            return current_features.reshape(1, -1)
        
        except Exception as e:
            logger.error(f"[MLStrategy] Error extracting features: {e}")
            return None
    
    def _get_model_probabilities(self, features: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Get probability predictions from all models.
        
        In production, this would load actual trained models.
        For now, we'll use improved placeholder probabilities based on 27 features.
        """
        # Placeholder: Generate mock probabilities using multiple features
        # In production, this would be:
        # - Load models from MLflow
        # - Run inference on features
        # - Return actual probabilities
        
        # Use multiple features for better signal generation
        # Feature indices (based on FeatureEngineer output):
        # 0: returns_1d, 1: returns_5d, 2: returns_20d
        # 7: ema_12, 8: ema_26
        # 9: price_to_sma20, 10: price_to_sma50
        # 11: rsi_14, 14: macd_hist
        
        try:
            # Extract key signals from features
            returns_1d = features[0, 0] if features.shape[1] > 0 else 0
            price_to_sma20 = features[0, 9] if features.shape[1] > 9 else 0
            rsi = features[0, 11] if features.shape[1] > 11 else 50
            macd_hist = features[0, 14] if features.shape[1] > 14 else 0
            
            # Generate balanced signals based on multiple indicators
            bullish_score = 0
            bearish_score = 0
            
            # RSI signals
            if rsi < 30:  # Oversold
                bullish_score += 0.3
            elif rsi > 70:  # Overbought
                bearish_score += 0.3
            
            # Price vs SMA signals
            if price_to_sma20 > 0.02:  # Price above SMA
                bullish_score += 0.2
            elif price_to_sma20 < -0.02:  # Price below SMA
                bearish_score += 0.2
            
            # MACD signals
            if macd_hist > 0:
                bullish_score += 0.2
            elif macd_hist < 0:
                bearish_score += 0.2
            
            # Recent returns
            if returns_1d > 0.01:
                bullish_score += 0.15
            elif returns_1d < -0.01:
                bearish_score += 0.15
            
            # Convert scores to probabilities (more balanced distribution)
            total_score = bullish_score + bearish_score
            
            if total_score > 0:
                # Strong signal
                if bullish_score > bearish_score:
                    base_probs = np.array([0.2, 0.3, 0.5])  # Bullish
                else:
                    base_probs = np.array([0.5, 0.3, 0.2])  # Bearish
            else:
                # Weak signal - neutral
                base_probs = np.array([0.3, 0.4, 0.3])  # Neutral
            
            # Add noise for variety across models
            model_probs = {}
            for model_name in ["xgb", "lstm", "transformer", "rl"]:
                noise = np.random.normal(0, 0.08, 3)
                probs = np.clip(base_probs + noise, 0.05, 0.95)
                probs = probs / probs.sum()
                model_probs[model_name] = probs
            
            return model_probs
        
        except Exception as e:
            logger.error(f"[MLStrategy] Error generating model probabilities: {e}")
            # Fallback to neutral probabilities
            neutral_probs = np.array([0.33, 0.34, 0.33])
            return {
                "xgb": neutral_probs,
                "lstm": neutral_probs,
                "transformer": neutral_probs,
                "rl": neutral_probs,
            }
    
    def _get_nifty_data(self) -> Optional[pd.DataFrame]:
        """
        Get Nifty 50 data for regime detection.
        
        In production, this would fetch from database.
        For now, use parameter or generate synthetic data.
        """
        if self.p.nifty_data is not None:
            return self.p.nifty_data
        
        # Generate synthetic Nifty data for testing
        # In production, this would be actual Nifty 50 OHLCV data
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
        """
        Handle entry logic based on ML prediction.
        
        Args:
            prediction: Dict with signal, confidence, probs, regime
        """
        signal = prediction["signal"]
        confidence = prediction["confidence"]
        
        # Only trade on BUY signals (can extend to SELL for shorting)
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
        stop_loss_price = price * (1 - self.p.stop_loss_pct)
        
        qty = self._calculate_position_size(price, stop_loss_price, confidence)
        
        if qty <= 0:
            self.log("Position size calculation returned 0")
            return
        
        # Place order
        self.log(
            f"BUY SIGNAL: {qty} shares @ {price:.2f} "
            f"(conf={confidence:.3f}, regime={prediction['regime']})"
        )
        
        self.order = self.buy(size=qty)
        self.entry_price = price
        self.stop_price = stop_loss_price
        self.take_profit_price = price * (1 + self.p.take_profit_pct)
    
    def _handle_exit(self, prediction: Dict):
        """
        Handle exit logic for existing position.
        
        Args:
            prediction: Dict with signal, confidence, probs, regime
        """
        current_price = self.data.close[0]
        
        # Exit conditions:
        # 1. Stop loss hit
        # 2. Take profit hit
        # 3. ML signal reverses with high confidence
        # 4. Trailing stop
        
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
        """
        Calculate position size based on risk management rules.
        
        Args:
            price: Entry price
            stop_loss_price: Stop loss price
            confidence: ML prediction confidence
        
        Returns:
            Number of shares to buy
        """
        if self.risk:
            # Use risk manager
            qty = self.risk.calculate_position_size(
                symbol=self.data._name,
                price=price,
                stop_loss_price=stop_loss_price,
                confidence=confidence,
            )
        else:
            # Simple position sizing: max_position_pct of portfolio
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
                    f"(value={order.executed.value:.2f}, "
                    f"comm={order.executed.comm:.2f})"
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
            f"TRADE CLOSED: PnL={trade.pnl:.2f}, "
            f"Net PnL={trade.pnlcomm:.2f}"
        )
    
    def stop(self):
        """Called when strategy stops."""
        self.log(
            f"Strategy finished. Final portfolio value: "
            f"₹{self.broker.getvalue():,.2f}"
        )
