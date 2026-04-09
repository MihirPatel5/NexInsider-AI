"""
backtesting/strategies/hybrid_strategy.py - Hybrid trading strategy combining rule-based + ML.

This strategy combines:
1. Rule-based signals (Trend Following, Mean Reversion, Momentum)
2. ML predictions (XGBoost, Random Forest)
3. Regime-aware weighting

Only trades when both rule-based and ML agree (high confidence).
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger
import joblib

from backtesting.strategies.rule_based_strategies import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MomentumStrategy
)
from data.features.technical import FeatureEngineer


class HybridStrategy:
    """
    Hybrid Strategy combining rule-based and ML predictions.
    
    Signal Generation:
    1. Get rule-based signals from 3 strategies
    2. Get ML predictions from trained models
    3. Combine with weighted voting
    4. Only trade when confidence > threshold
    
    Weighting:
    - Rule-based: 40%
    - ML models: 60%
    """
    
    def __init__(
        self,
        model_dir: str = "models/trained",
        rule_weight: float = 0.4,
        ml_weight: float = 0.6,
        confidence_threshold: float = 0.6,
        stop_loss_pct: float = 0.07,
        take_profit_pct: float = 0.12
    ):
        """
        Initialize Hybrid Strategy.
        
        Args:
            model_dir: Directory containing trained models
            rule_weight: Weight for rule-based signals (default: 0.4)
            ml_weight: Weight for ML predictions (default: 0.6)
            confidence_threshold: Minimum confidence to trade (default: 0.6)
            stop_loss_pct: Stop loss percentage (default: 7%)
            take_profit_pct: Take profit percentage (default: 12%)
        """
        self.model_dir = Path(model_dir)
        self.rule_weight = rule_weight
        self.ml_weight = ml_weight
        self.confidence_threshold = confidence_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # Initialize rule-based strategies
        self.trend_strategy = TrendFollowingStrategy()
        self.mean_reversion_strategy = MeanReversionStrategy()
        self.momentum_strategy = MomentumStrategy()
        
        # Initialize feature engineer
        self.feature_engineer = FeatureEngineer()
        
        # Load ML models
        self._load_models()
        
        logger.info("HybridStrategy initialized")
        logger.info(f"  Rule Weight: {rule_weight*100:.0f}%")
        logger.info(f"  ML Weight: {ml_weight*100:.0f}%")
        logger.info(f"  Confidence Threshold: {confidence_threshold:.2f}")
    
    def _load_models(self):
        """Load trained ML models."""
        try:
            # Load XGBoost
            xgb_path = self.model_dir / "xgboost_latest.joblib"
            self.xgb_model = joblib.load(xgb_path)
            logger.info(f"✅ Loaded XGBoost model from {xgb_path}")
            
            # Load Random Forest
            rf_path = self.model_dir / "random_forest_latest.joblib"
            self.rf_model = joblib.load(rf_path)
            logger.info(f"✅ Loaded Random Forest model from {rf_path}")
            
            # Load feature names
            features_path = self.model_dir / "feature_names_latest.joblib"
            self.feature_names = joblib.load(features_path)
            logger.info(f"✅ Loaded {len(self.feature_names)} feature names")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            logger.warning("Using rule-based only mode")
            self.xgb_model = None
            self.rf_model = None
            self.feature_names = None
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals combining rule-based + ML.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with signals and confidence scores
        """
        # Extract features
        features_df = self.feature_engineer.extract_features(df)
        
        # Get rule-based signals
        trend_signals = self.trend_strategy.generate_signals(df)
        mean_rev_signals = self.mean_reversion_strategy.generate_signals(df)
        momentum_signals = self.momentum_strategy.generate_signals(df)
        
        # Combine rule-based signals (average)
        rule_signal = (
            trend_signals['signal'] * 0.4 +
            mean_rev_signals['signal'] * 0.3 +
            momentum_signals['signal'] * 0.3
        )
        
        rule_strength = (
            trend_signals['signal_strength'] * 0.4 +
            mean_rev_signals['signal_strength'] * 0.3 +
            momentum_signals['signal_strength'] * 0.3
        )
        
        # Get ML predictions if models available
        if self.xgb_model is not None and self.rf_model is not None:
            ml_signal, ml_confidence = self._get_ml_predictions(features_df)
        else:
            ml_signal = pd.Series(0, index=features_df.index)
            ml_confidence = pd.Series(0.5, index=features_df.index)
        
        # Combine signals with weighting
        combined_signal = (
            rule_signal * self.rule_weight +
            ml_signal * self.ml_weight
        )
        
        # Calculate confidence (agreement between rule-based and ML)
        agreement = np.abs(rule_signal - ml_signal) < 0.5  # Similar direction
        confidence = (
            rule_strength * self.rule_weight +
            ml_confidence * self.ml_weight
        ) * agreement.astype(float)
        
        # Final signal: only trade when confidence > threshold
        final_signal = pd.Series(0, index=features_df.index)
        final_signal[combined_signal > 0.5] = 1  # BUY
        final_signal[combined_signal < -0.5] = -1  # SELL
        final_signal[confidence < self.confidence_threshold] = 0  # HOLD (low confidence)
        
        # Add to features_df
        features_df['signal'] = final_signal
        features_df['confidence'] = confidence
        features_df['rule_signal'] = rule_signal
        features_df['ml_signal'] = ml_signal
        
        return features_df
    
    def _get_ml_predictions(self, features_df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Get ML predictions from trained models.
        
        Args:
            features_df: DataFrame with features
        
        Returns:
            (signal, confidence) where signal is -1/0/1 and confidence is 0-1
        """
        # Prepare features
        X = features_df[self.feature_names].copy()
        X = X.ffill().bfill().fillna(0)
        
        # Get predictions from both models
        xgb_pred = self.xgb_model.predict(X)
        xgb_proba = self.xgb_model.predict_proba(X)
        
        rf_pred = self.rf_model.predict(X)
        rf_proba = self.rf_model.predict_proba(X)
        
        # Average predictions (0=SELL, 1=HOLD, 2=BUY)
        avg_pred = (xgb_pred + rf_pred) / 2.0
        
        # Convert to signal (-1, 0, 1)
        signal = pd.Series(0, index=features_df.index)
        signal[avg_pred < 0.7] = -1  # SELL
        signal[avg_pred > 1.3] = 1   # BUY
        # Otherwise HOLD (0)
        
        # Calculate confidence (max probability from both models)
        xgb_conf = xgb_proba.max(axis=1)
        rf_conf = rf_proba.max(axis=1)
        confidence = pd.Series((xgb_conf + rf_conf) / 2.0, index=features_df.index)
        
        return signal, confidence
    
    def should_exit_long(
        self,
        current_price: float,
        entry_price: float,
        highest_price: float,
        features: Dict
    ) -> Tuple[bool, str]:
        """
        Check if should exit long position.
        
        Args:
            current_price: Current price
            entry_price: Entry price
            highest_price: Highest price since entry
            features: Dictionary of technical indicators
        
        Returns:
            (should_exit, reason)
        """
        # Stop loss
        if current_price <= entry_price * (1 - self.stop_loss_pct):
            return True, "stop_loss"
        
        # Take profit
        if current_price >= entry_price * (1 + self.take_profit_pct):
            return True, "take_profit"
        
        # Signal reversal (strong sell signal)
        if features.get('signal', 0) == -1 and features.get('confidence', 0) > 0.7:
            return True, "signal_reversal"
        
        return False, ""
    
    def should_exit_short(
        self,
        current_price: float,
        entry_price: float,
        lowest_price: float,
        features: Dict
    ) -> Tuple[bool, str]:
        """
        Check if should exit short position.
        
        Args:
            current_price: Current price
            entry_price: Entry price
            lowest_price: Lowest price since entry
            features: Dictionary of technical indicators
        
        Returns:
            (should_exit, reason)
        """
        # Stop loss
        if current_price >= entry_price * (1 + self.stop_loss_pct):
            return True, "stop_loss"
        
        # Take profit
        if current_price <= entry_price * (1 - self.take_profit_pct):
            return True, "take_profit"
        
        # Signal reversal (strong buy signal)
        if features.get('signal', 0) == 1 and features.get('confidence', 0) > 0.7:
            return True, "signal_reversal"
        
        return False, ""
