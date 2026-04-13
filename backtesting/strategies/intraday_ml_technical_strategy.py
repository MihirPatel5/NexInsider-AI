"""
backtesting/strategies/intraday_ml_technical_strategy.py - Enhanced intraday strategy with ML + Technical signals.

This strategy combines:
1. ML predictions (XGBoost + Random Forest)
2. Volume breakouts
3. RSI extremes
4. Support/Resistance levels
5. VWAP crossovers

Goal: Increase trade frequency from 0.37/day to 2-3/day while maintaining 60-65% win rate.
"""
import backtrader as bt
import numpy as np
import pandas as pd
from loguru import logger
from typing import Optional, Dict, List, Tuple
from datetime import time
import joblib
from pathlib import Path
from collections import deque

from data.features.technical import FeatureEngineer


class IntradayMLTechnicalStrategy(bt.Strategy):
    """
    Enhanced intraday strategy combining ML + Technical signals.
    
    Signal Sources:
    1. ML Models (XGBoost + Random Forest) - 61-62% accuracy
    2. Volume Breakouts - High volume = strong moves
    3. RSI Extremes - Oversold/Overbought conditions
    4. Support/Resistance - Key price levels
    5. VWAP - Institutional price reference
    
    Trading Logic:
    - Enter when ML + at least 1 technical signal agree
    - Exit on stop loss, take profit, or signal reversal
    - Automatic square-off at 3:10 PM
    """
    
    params = (
        # ML parameters
        ("ml_confidence_threshold", 0.25),
        ("ml_weight", 0.6),  # 60% weight to ML, 40% to technical
        
        # Risk management
        ("stop_loss_pct", 0.008),
        ("take_profit_pct", 0.015),
        ("trailing_stop_pct", 0.005),
        ("max_position_pct", 0.40),
        ("max_daily_loss_pct", 0.03),
        ("max_trades_per_day", 15),
        
        # Time-based rules
        ("market_open", time(9, 15)),
        ("skip_until", time(9, 30)),
        ("lunch_start", time(12, 30)),
        ("lunch_end", time(13, 30)),
        ("square_off_time", time(15, 10)),
        ("market_close", time(15, 15)),
        
        # Technical signal parameters
        ("use_volume_breakout", True),
        ("volume_threshold", 1.5),  # 1.5x average volume
        ("volume_lookback", 20),
        
        ("use_rsi_signals", True),
        ("rsi_oversold", 35),
        ("rsi_overbought", 65),
        
        ("use_support_resistance", True),
        ("sr_lookback", 50),
        ("sr_tolerance", 0.002),  # 0.2% tolerance
        
        ("use_vwap", True),
        
        # Model paths
        ("model_dir", "models/trained"),
        ("use_xgboost", True),
        ("use_random_forest", True),
    )
    
    def log(self, txt, dt=None):
        """Logging helper."""
        dt = dt or self.datas[0].datetime.datetime(0)
        logger.info(f"[MLTech] {dt.strftime('%Y-%m-%d %H:%M:%S')} | {txt}")
    
    def __init__(self):
        """Initialize strategy components."""
        # Load ML models
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
        self.entry_signals = []  # Track which signals triggered entry
        
        # Daily tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.current_date = None
        self.initial_daily_value = None
        
        # Technical indicators tracking
        self.volume_history = deque(maxlen=self.p.volume_lookback)
        self.price_history = deque(maxlen=self.p.sr_lookback)
        self.support_levels = []
        self.resistance_levels = []
        
        self.log("Initialized ML + Technical Strategy")
        self.log(f"Signal sources: ML + Volume + RSI + S/R + VWAP")
        self.log(f"Trading hours: {self.p.skip_until} - {self.p.square_off_time}")
    
    def _load_models(self):
        """Load trained intraday models."""
        try:
            model_dir = Path(self.p.model_dir)
            
            if self.p.use_xgboost:
                xgb_path = model_dir / "xgboost_intraday.joblib"
                if xgb_path.exists():
                    self.xgb_model = joblib.load(xgb_path)
                    logger.info(f"✅ Loaded XGBoost model")
            
            if self.p.use_random_forest:
                rf_path = model_dir / "random_forest_intraday.joblib"
                if rf_path.exists():
                    self.rf_model = joblib.load(rf_path)
                    logger.info(f"✅ Loaded Random Forest model")
            
            features_path = model_dir / "feature_names_intraday.joblib"
            if features_path.exists():
                self.feature_names = joblib.load(features_path)
                logger.info(f"✅ Loaded {len(self.feature_names)} features")
        
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def next(self):
        """Main strategy logic."""
        current_dt = self.datas[0].datetime.datetime(0)
        current_time = current_dt.time()
        current_date = current_dt.date()
        
        # Reset daily counters
        if self.current_date != current_date:
            self._reset_daily_counters(current_date)
        
        # Update technical indicators
        self._update_technical_indicators()
        
        # Check pending order
        if self.order:
            return
        
        # Check trading time
        if not self._is_trading_time(current_time):
            return
        
        # Square off near close
        if current_time >= self.p.square_off_time:
            if self.position:
                self.log(f"SQUARE OFF - Closing position")
                self.order = self.close()
            return
        
        # Check daily limits
        if not self._check_daily_limits():
            if self.position:
                self.log("Daily limits breached, closing")
                self.order = self.close()
            return
        
        # Get combined signals
        signals = self._get_combined_signals()
        
        if signals is None:
            return
        
        # Execute trading logic
        if not self.position:
            self._handle_entry(signals, current_time)
        else:
            self._handle_exit(signals, current_time)
    
    def _update_technical_indicators(self):
        """Update technical indicator history."""
        if len(self.data) < 2:
            return
        
        # Update volume history
        self.volume_history.append(self.data.volume[0])
        
        # Update price history for S/R
        self.price_history.append({
            'high': self.data.high[0],
            'low': self.data.low[0],
            'close': self.data.close[0]
        })
        
        # Update S/R levels every 10 bars
        if len(self.data) % 10 == 0:
            self._update_support_resistance()
    
    def _update_support_resistance(self):
        """Identify support and resistance levels."""
        if len(self.price_history) < 20:
            return
        
        highs = [p['high'] for p in self.price_history]
        lows = [p['low'] for p in self.price_history]
        
        # Find local maxima (resistance)
        self.resistance_levels = []
        for i in range(5, len(highs) - 5):
            if highs[i] == max(highs[i-5:i+6]):
                self.resistance_levels.append(highs[i])
        
        # Find local minima (support)
        self.support_levels = []
        for i in range(5, len(lows) - 5):
            if lows[i] == min(lows[i-5:i+6]):
                self.support_levels.append(lows[i])
        
        # Keep only recent levels
        self.resistance_levels = sorted(set(self.resistance_levels))[-5:]
        self.support_levels = sorted(set(self.support_levels))[-5:]
    
    def _get_combined_signals(self) -> Optional[Dict]:
        """
        Get combined signals from ML + Technical indicators.
        
        Returns:
            Dict with overall signal, confidence, and individual signals
        """
        try:
            signals = {
                'ml': None,
                'volume': None,
                'rsi': None,
                'sr': None,
                'vwap': None,
            }
            
            # 1. ML Signal
            ml_pred = self._get_ml_prediction()
            if ml_pred:
                signals['ml'] = {
                    'signal': ml_pred['signal'],
                    'confidence': ml_pred['confidence'],
                    'weight': self.p.ml_weight
                }
            
            # 2. Volume Breakout Signal
            if self.p.use_volume_breakout:
                signals['volume'] = self._get_volume_signal()
            
            # 3. RSI Signal
            if self.p.use_rsi_signals:
                signals['rsi'] = self._get_rsi_signal()
            
            # 4. Support/Resistance Signal
            if self.p.use_support_resistance:
                signals['sr'] = self._get_sr_signal()
            
            # 5. VWAP Signal
            if self.p.use_vwap:
                signals['vwap'] = self._get_vwap_signal()
            
            # Combine signals
            return self._combine_signals(signals)
        
        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            return None
    
    def _get_ml_prediction(self) -> Optional[Dict]:
        """Get ML prediction."""
        try:
            features = self._extract_features()
            if features is None:
                return None
            
            predictions = []
            confidences = []
            
            if self.xgb_model:
                xgb_proba = self.xgb_model.predict_proba(features)[0]
                xgb_pred = np.argmax(xgb_proba)
                predictions.append(xgb_pred)
                confidences.append(xgb_proba[xgb_pred])
            
            if self.rf_model:
                rf_proba = self.rf_model.predict_proba(features)[0]
                rf_pred = np.argmax(rf_proba)
                predictions.append(rf_pred)
                confidences.append(rf_proba[rf_pred])
            
            if not predictions:
                return None
            
            avg_pred = int(np.round(np.mean(predictions)))
            avg_conf = np.mean(confidences)
            
            signal_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
            
            return {
                "signal": signal_map.get(avg_pred, "HOLD"),
                "confidence": avg_conf,
            }
        except:
            return None
    
    def _get_volume_signal(self) -> Optional[Dict]:
        """
        Volume breakout signal.
        High volume = strong move likely.
        """
        if len(self.volume_history) < self.p.volume_lookback:
            return None
        
        current_volume = self.data.volume[0]
        avg_volume = np.mean(self.volume_history)
        
        if current_volume > avg_volume * self.p.volume_threshold:
            # High volume - check price direction
            price_change = (self.data.close[0] - self.data.close[-1]) / self.data.close[-1]
            
            if price_change > 0.001:  # 0.1% up
                return {'signal': 'BUY', 'strength': min(current_volume / avg_volume / 2, 1.0)}
            elif price_change < -0.001:  # 0.1% down
                return {'signal': 'SELL', 'strength': min(current_volume / avg_volume / 2, 1.0)}
        
        return {'signal': 'HOLD', 'strength': 0.0}
    
    def _get_rsi_signal(self) -> Optional[Dict]:
        """
        RSI extreme signal.
        RSI < 35 = oversold (BUY)
        RSI > 65 = overbought (SELL)
        """
        if len(self.data) < 14:
            return None
        
        # Calculate RSI
        closes = [self.data.close[-i] for i in range(14, -1, -1)]
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        if rsi < self.p.rsi_oversold:
            return {'signal': 'BUY', 'strength': (self.p.rsi_oversold - rsi) / self.p.rsi_oversold}
        elif rsi > self.p.rsi_overbought:
            return {'signal': 'SELL', 'strength': (rsi - self.p.rsi_overbought) / (100 - self.p.rsi_overbought)}
        
        return {'signal': 'HOLD', 'strength': 0.0}
    
    def _get_sr_signal(self) -> Optional[Dict]:
        """
        Support/Resistance signal.
        Near support = BUY
        Near resistance = SELL
        """
        if not self.support_levels and not self.resistance_levels:
            return None
        
        current_price = self.data.close[0]
        
        # Check if near support
        for support in self.support_levels:
            if abs(current_price - support) / support < self.p.sr_tolerance:
                return {'signal': 'BUY', 'strength': 0.7}
        
        # Check if near resistance
        for resistance in self.resistance_levels:
            if abs(current_price - resistance) / resistance < self.p.sr_tolerance:
                return {'signal': 'SELL', 'strength': 0.7}
        
        return {'signal': 'HOLD', 'strength': 0.0}
    
    def _get_vwap_signal(self) -> Optional[Dict]:
        """
        VWAP crossover signal.
        Price > VWAP = BUY
        Price < VWAP = SELL
        """
        if len(self.data) < 20:
            return None
        
        # Calculate VWAP
        typical_prices = []
        volumes = []
        
        for i in range(20, 0, -1):
            tp = (self.data.high[-i] + self.data.low[-i] + self.data.close[-i]) / 3
            typical_prices.append(tp)
            volumes.append(self.data.volume[-i])
        
        vwap = np.sum(np.array(typical_prices) * np.array(volumes)) / np.sum(volumes)
        current_price = self.data.close[0]
        
        diff_pct = (current_price - vwap) / vwap
        
        if diff_pct > 0.002:  # 0.2% above VWAP
            return {'signal': 'BUY', 'strength': min(abs(diff_pct) * 50, 1.0)}
        elif diff_pct < -0.002:  # 0.2% below VWAP
            return {'signal': 'SELL', 'strength': min(abs(diff_pct) * 50, 1.0)}
        
        return {'signal': 'HOLD', 'strength': 0.0}
    
    def _combine_signals(self, signals: Dict) -> Dict:
        """
        Combine all signals into final decision.
        
        Logic:
        - ML signal is primary (60% weight)
        - Technical signals provide confirmation (40% weight)
        - Need ML + at least 1 technical signal to trade
        """
        buy_score = 0.0
        sell_score = 0.0
        active_signals = []
        
        # ML signal (60% weight)
        if signals['ml']:
            ml_sig = signals['ml']['signal']
            ml_conf = signals['ml']['confidence']
            
            if ml_sig == 'BUY' and ml_conf > self.p.ml_confidence_threshold:
                buy_score += 0.6 * ml_conf
                active_signals.append('ML')
            elif ml_sig == 'SELL' and ml_conf > self.p.ml_confidence_threshold:
                sell_score += 0.6 * ml_conf
                active_signals.append('ML')
        
        # Technical signals (40% weight total, 10% each)
        tech_weight = 0.1
        
        for name, signal in signals.items():
            if name == 'ml' or signal is None:
                continue
            
            sig = signal.get('signal', 'HOLD')
            strength = signal.get('strength', 0.0)
            
            if sig == 'BUY':
                buy_score += tech_weight * strength
                active_signals.append(name.upper())
            elif sig == 'SELL':
                sell_score += tech_weight * strength
                active_signals.append(name.upper())
        
        # Determine final signal
        if buy_score > sell_score and buy_score > 0.4:  # Need at least 40% confidence
            return {
                'signal': 'BUY',
                'confidence': buy_score,
                'active_signals': active_signals
            }
        elif sell_score > buy_score and sell_score > 0.4:
            return {
                'signal': 'SELL',
                'confidence': sell_score,
                'active_signals': active_signals
            }
        
        return {
            'signal': 'HOLD',
            'confidence': 0.0,
            'active_signals': []
        }
    
    def _extract_features(self) -> Optional[np.ndarray]:
        """Extract ML features."""
        try:
            if len(self.data) < 200:
                return None
            
            lookback = min(250, len(self.data))
            
            df_data = {
                'open': [self.data.open[-i] for i in range(lookback - 1, -1, -1)],
                'high': [self.data.high[-i] for i in range(lookback - 1, -1, -1)],
                'low': [self.data.low[-i] for i in range(lookback - 1, -1, -1)],
                'close': [self.data.close[-i] for i in range(lookback - 1, -1, -1)],
                'volume': [self.data.volume[-i] for i in range(lookback - 1, -1, -1)],
            }
            
            df = pd.DataFrame(df_data)
            features_df = self.feature_engineer.extract_features(df, include_all=True)
            latest_features = features_df.iloc[-1]
            
            if self.feature_names:
                X = pd.DataFrame([latest_features[self.feature_names]], columns=self.feature_names)
            else:
                X = pd.DataFrame([latest_features])
            
            X = X.ffill().bfill().fillna(0)
            return X.values
        except:
            return None
    
    def _handle_entry(self, signals: Dict, current_time: time):
        """Handle entry logic."""
        if signals['signal'] != 'BUY':
            return
        
        # Need at least 2 signals (ML + 1 technical)
        if len(signals['active_signals']) < 2:
            return
        
        confidence = signals['confidence']
        price = self.data.close[0]
        stop_loss_price = price * (1 - self.p.stop_loss_pct)
        
        qty = self._calculate_position_size(price, stop_loss_price, confidence)
        
        if qty <= 0:
            return
        
        self.log(
            f"BUY: {qty} @ ₹{price:.2f} "
            f"(conf={confidence:.2f}, signals={','.join(signals['active_signals'])})"
        )
        
        self.order = self.buy(size=qty)
        self.entry_price = price
        self.entry_time = current_time
        self.stop_price = stop_loss_price
        self.take_profit_price = price * (1 + self.p.take_profit_pct)
        self.entry_signals = signals['active_signals']
        
        self.daily_trades += 1
    
    def _handle_exit(self, signals: Dict, current_time: time):
        """Handle exit logic."""
        current_price = self.data.close[0]
        
        # Stop loss
        if current_price <= self.stop_price:
            self.log(f"STOP LOSS @ ₹{current_price:.2f}")
            self.order = self.close()
            return
        
        # Take profit
        if current_price >= self.take_profit_price:
            self.log(f"TAKE PROFIT @ ₹{current_price:.2f}")
            self.order = self.close()
            return
        
        # Signal reversal
        if signals['signal'] == 'SELL' and signals['confidence'] > 0.6:
            self.log(f"SIGNAL REVERSAL @ ₹{current_price:.2f}")
            self.order = self.close()
            return
        
        # Trailing stop
        pnl_pct = (current_price - self.entry_price) / self.entry_price
        if pnl_pct > 0.005:
            new_stop = max(self.entry_price, current_price * (1 - self.p.trailing_stop_pct))
            if new_stop > self.stop_price:
                self.stop_price = new_stop
    
    def _calculate_position_size(self, price: float, stop_loss_price: float, confidence: float) -> int:
        """Calculate position size."""
        portfolio_value = self.broker.getvalue()
        max_position_value = portfolio_value * self.p.max_position_pct
        confidence_multiplier = min(confidence / 0.4, 1.5)
        adjusted_position_value = max_position_value * confidence_multiplier
        qty = int(adjusted_position_value / price)
        return max(0, qty)
    
    def _reset_daily_counters(self, new_date):
        """Reset daily counters."""
        if self.current_date:
            self.log(f"Day ended: {self.daily_trades} trades, PnL: ₹{self.daily_pnl:.2f}")
        
        self.current_date = new_date
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.initial_daily_value = self.broker.getvalue()
        self.log(f"New day: {new_date}")
    
    def _is_trading_time(self, current_time: time) -> bool:
        """Check if trading time."""
        if current_time < self.p.market_open or current_time >= self.p.square_off_time:
            return False
        if current_time < self.p.skip_until:
            return False
        if self.p.lunch_start <= current_time < self.p.lunch_end and not self.position:
            return False
        return True
    
    def _check_daily_limits(self) -> bool:
        """Check daily limits."""
        if self.daily_trades >= self.p.max_trades_per_day:
            return False
        
        if self.initial_daily_value:
            current_value = self.broker.getvalue()
            daily_loss_pct = (current_value - self.initial_daily_value) / self.initial_daily_value
            if daily_loss_pct < -self.p.max_daily_loss_pct:
                return False
        
        return True
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED: {order.executed.size} @ ₹{order.executed.price:.2f}")
            else:
                pnl = order.executed.pnl
                self.daily_pnl += pnl
                self.log(f"SELL EXECUTED: PnL=₹{pnl:.2f}")
        
        self.order = None
    
    def stop(self):
        """Strategy finished."""
        self.log(f"Finished. Portfolio: ₹{self.broker.getvalue():,.2f}")
        self.log(f"Total trades: {self.daily_trades}, PnL: ₹{self.daily_pnl:.2f}")
