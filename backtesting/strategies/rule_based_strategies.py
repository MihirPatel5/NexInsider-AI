"""
backtesting/strategies/rule_based_strategies.py - Rule-based trading strategies.

This module implements proven rule-based strategies:
1. Trend Following - Follow the trend with SMA, MACD, ADX
2. Mean Reversion - Trade oversold/overbought with RSI, Bollinger Bands
3. Momentum - Capture strong moves with ADX, ROC

These strategies use the 27 technical indicators from FeatureEngineer.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger
from datetime import datetime

from data.features.technical import FeatureEngineer


class TrendFollowingStrategy:
    """
    Trend Following Strategy.
    
    Entry Rules:
    - BUY: Price > SMA(50) AND RSI < 70 AND MACD > 0 AND ADX > 25
    - SELL: Price < SMA(50) AND RSI > 30 AND MACD < 0 AND ADX > 25
    
    Exit Rules:
    - Exit LONG: Price < SMA(50) OR RSI > 80 OR MACD < 0
    - Exit SHORT: Price > SMA(50) OR RSI < 20 OR MACD > 0
    
    Risk Management:
    - Stop Loss: 7%
    - Take Profit: 12%
    """
    
    def __init__(
        self,
        stop_loss_pct: float = 0.07,
        take_profit_pct: float = 0.12,
        min_adx: float = 25.0,
        rsi_overbought: float = 80.0,
        rsi_oversold: float = 20.0,
        rsi_entry_max: float = 70.0,
        rsi_entry_min: float = 30.0
    ):
        """
        Initialize Trend Following Strategy.
        
        Args:
            stop_loss_pct: Stop loss percentage (default: 7%)
            take_profit_pct: Take profit percentage (default: 12%)
            min_adx: Minimum ADX for trend strength (default: 25)
            rsi_overbought: RSI overbought level (default: 80)
            rsi_oversold: RSI oversold level (default: 20)
            rsi_entry_max: Maximum RSI for long entry (default: 70)
            rsi_entry_min: Minimum RSI for short entry (default: 30)
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.min_adx = min_adx
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.rsi_entry_max = rsi_entry_max
        self.rsi_entry_min = rsi_entry_min
        
        self.feature_engineer = FeatureEngineer()
        
        logger.info("TrendFollowingStrategy initialized")
        logger.info(f"  Stop Loss: {stop_loss_pct*100:.1f}%")
        logger.info(f"  Take Profit: {take_profit_pct*100:.1f}%")
        logger.info(f"  Min ADX: {min_adx}")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with signals (1=BUY, -1=SELL, 0=HOLD)
        """
        # Extract features
        features_df = self.feature_engineer.extract_features(df)
        
        # Initialize signal column
        features_df['signal'] = 0
        features_df['signal_strength'] = 0.0
        
        # Long entry conditions
        long_condition = (
            (features_df['close'] > features_df['sma_50']) &
            (features_df['rsi_14'] < self.rsi_entry_max) &
            (features_df['macd'] > 0) &
            (features_df['adx'] > self.min_adx)
        )
        
        # Short entry conditions
        short_condition = (
            (features_df['close'] < features_df['sma_50']) &
            (features_df['rsi_14'] > self.rsi_entry_min) &
            (features_df['macd'] < 0) &
            (features_df['adx'] > self.min_adx)
        )
        
        # Set signals
        features_df.loc[long_condition, 'signal'] = 1
        features_df.loc[short_condition, 'signal'] = -1
        
        # Calculate signal strength (0-1)
        # Based on how strong the trend is
        features_df.loc[long_condition, 'signal_strength'] = (
            features_df.loc[long_condition, 'adx'] / 100.0
        ).clip(0, 1)
        
        features_df.loc[short_condition, 'signal_strength'] = (
            features_df.loc[short_condition, 'adx'] / 100.0
        ).clip(0, 1)
        
        return features_df
    
    def should_exit_long(self, current_price: float, entry_price: float, features: Dict) -> Tuple[bool, str]:
        """
        Check if should exit long position.
        
        Args:
            current_price: Current price
            entry_price: Entry price
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
        
        # Trend reversal
        if current_price < features.get('sma_50', 0):
            return True, "trend_reversal"
        
        # Overbought
        if features.get('rsi_14', 50) > self.rsi_overbought:
            return True, "overbought"
        
        # MACD bearish
        if features.get('macd', 0) < 0:
            return True, "macd_bearish"
        
        return False, ""
    
    def should_exit_short(self, current_price: float, entry_price: float, features: Dict) -> Tuple[bool, str]:
        """
        Check if should exit short position.
        
        Args:
            current_price: Current price
            entry_price: Entry price
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
        
        # Trend reversal
        if current_price > features.get('sma_50', 0):
            return True, "trend_reversal"
        
        # Oversold
        if features.get('rsi_14', 50) < self.rsi_oversold:
            return True, "oversold"
        
        # MACD bullish
        if features.get('macd', 0) > 0:
            return True, "macd_bullish"
        
        return False, ""


class MeanReversionStrategy:
    """
    Mean Reversion Strategy.
    
    Entry Rules:
    - BUY: RSI < 30 AND Price touches lower Bollinger Band
    - SELL: RSI > 70 AND Price touches upper Bollinger Band
    
    Exit Rules:
    - Exit LONG: RSI > 70 OR Price touches upper Bollinger Band
    - Exit SHORT: RSI < 30 OR Price touches lower Bollinger Band
    
    Risk Management:
    - Stop Loss: 5%
    - Take Profit: 10%
    """
    
    def __init__(
        self,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.10,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        bb_touch_threshold: float = 0.02  # 2% from band
    ):
        """
        Initialize Mean Reversion Strategy.
        
        Args:
            stop_loss_pct: Stop loss percentage (default: 5%)
            take_profit_pct: Take profit percentage (default: 10%)
            rsi_oversold: RSI oversold level (default: 30)
            rsi_overbought: RSI overbought level (default: 70)
            bb_touch_threshold: Threshold for Bollinger Band touch (default: 2%)
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_touch_threshold = bb_touch_threshold
        
        self.feature_engineer = FeatureEngineer()
        
        logger.info("MeanReversionStrategy initialized")
        logger.info(f"  Stop Loss: {stop_loss_pct*100:.1f}%")
        logger.info(f"  Take Profit: {take_profit_pct*100:.1f}%")
        logger.info(f"  RSI Oversold: {rsi_oversold}")
        logger.info(f"  RSI Overbought: {rsi_overbought}")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with signals (1=BUY, -1=SELL, 0=HOLD)
        """
        # Extract features
        features_df = self.feature_engineer.extract_features(df)
        
        # Initialize signal column
        features_df['signal'] = 0
        features_df['signal_strength'] = 0.0
        
        # Calculate distance from Bollinger Bands
        bb_lower_dist = (features_df['close'] - features_df['bb_lower']) / features_df['close']
        bb_upper_dist = (features_df['bb_upper'] - features_df['close']) / features_df['close']
        
        # Long entry conditions (oversold + near lower band)
        long_condition = (
            (features_df['rsi_14'] < self.rsi_oversold) &
            (bb_lower_dist < self.bb_touch_threshold)
        )
        
        # Short entry conditions (overbought + near upper band)
        short_condition = (
            (features_df['rsi_14'] > self.rsi_overbought) &
            (bb_upper_dist < self.bb_touch_threshold)
        )
        
        # Set signals
        features_df.loc[long_condition, 'signal'] = 1
        features_df.loc[short_condition, 'signal'] = -1
        
        # Calculate signal strength based on RSI extremity
        features_df.loc[long_condition, 'signal_strength'] = (
            (self.rsi_oversold - features_df.loc[long_condition, 'rsi_14']) / self.rsi_oversold
        ).clip(0, 1)
        
        features_df.loc[short_condition, 'signal_strength'] = (
            (features_df.loc[short_condition, 'rsi_14'] - self.rsi_overbought) / (100 - self.rsi_overbought)
        ).clip(0, 1)
        
        return features_df
    
    def should_exit_long(self, current_price: float, entry_price: float, features: Dict) -> Tuple[bool, str]:
        """Check if should exit long position."""
        # Stop loss
        if current_price <= entry_price * (1 - self.stop_loss_pct):
            return True, "stop_loss"
        
        # Take profit
        if current_price >= entry_price * (1 + self.take_profit_pct):
            return True, "take_profit"
        
        # Overbought
        if features.get('rsi_14', 50) > self.rsi_overbought:
            return True, "overbought"
        
        # Near upper Bollinger Band
        bb_upper = features.get('bb_upper', 0)
        if bb_upper > 0 and current_price >= bb_upper * (1 - self.bb_touch_threshold):
            return True, "bb_upper_touch"
        
        return False, ""
    
    def should_exit_short(self, current_price: float, entry_price: float, features: Dict) -> Tuple[bool, str]:
        """Check if should exit short position."""
        # Stop loss
        if current_price >= entry_price * (1 + self.stop_loss_pct):
            return True, "stop_loss"
        
        # Take profit
        if current_price <= entry_price * (1 - self.take_profit_pct):
            return True, "take_profit"
        
        # Oversold
        if features.get('rsi_14', 50) < self.rsi_oversold:
            return True, "oversold"
        
        # Near lower Bollinger Band
        bb_lower = features.get('bb_lower', 0)
        if bb_lower > 0 and current_price <= bb_lower * (1 + self.bb_touch_threshold):
            return True, "bb_lower_touch"
        
        return False, ""


class MomentumStrategy:
    """
    Momentum Strategy.
    
    Entry Rules:
    - BUY: ADX > 25 AND +DI > -DI AND ROC > 0
    - SELL: ADX > 25 AND -DI > +DI AND ROC < 0
    
    Exit Rules:
    - Exit LONG: ADX < 20 OR +DI < -DI OR trailing stop hit
    - Exit SHORT: ADX < 20 OR -DI < +DI OR trailing stop hit
    
    Risk Management:
    - Trailing Stop: 5%
    - Take Profit: 15%
    """
    
    def __init__(
        self,
        trailing_stop_pct: float = 0.05,
        take_profit_pct: float = 0.15,
        min_adx: float = 25.0,
        weak_adx: float = 20.0,
        min_roc: float = 0.0
    ):
        """
        Initialize Momentum Strategy.
        
        Args:
            trailing_stop_pct: Trailing stop percentage (default: 5%)
            take_profit_pct: Take profit percentage (default: 15%)
            min_adx: Minimum ADX for entry (default: 25)
            weak_adx: ADX level for exit (default: 20)
            min_roc: Minimum ROC for entry (default: 0)
        """
        self.trailing_stop_pct = trailing_stop_pct
        self.take_profit_pct = take_profit_pct
        self.min_adx = min_adx
        self.weak_adx = weak_adx
        self.min_roc = min_roc
        
        self.feature_engineer = FeatureEngineer()
        
        logger.info("MomentumStrategy initialized")
        logger.info(f"  Trailing Stop: {trailing_stop_pct*100:.1f}%")
        logger.info(f"  Take Profit: {take_profit_pct*100:.1f}%")
        logger.info(f"  Min ADX: {min_adx}")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with signals (1=BUY, -1=SELL, 0=HOLD)
        """
        # Extract features
        features_df = self.feature_engineer.extract_features(df)
        
        # Initialize signal column
        features_df['signal'] = 0
        features_df['signal_strength'] = 0.0
        
        # Long entry conditions (strong upward momentum)
        long_condition = (
            (features_df['adx'] > self.min_adx) &
            (features_df['roc_10'] > self.min_roc) &
            (features_df['macd'] > 0) &
            (features_df['close'] > features_df['sma_20'])
        )
        
        # Short entry conditions (strong downward momentum)
        short_condition = (
            (features_df['adx'] > self.min_adx) &
            (features_df['roc_10'] < -self.min_roc) &
            (features_df['macd'] < 0) &
            (features_df['close'] < features_df['sma_20'])
        )
        
        # Set signals
        features_df.loc[long_condition, 'signal'] = 1
        features_df.loc[short_condition, 'signal'] = -1
        
        # Calculate signal strength based on ADX and ROC
        features_df.loc[long_condition, 'signal_strength'] = (
            (features_df.loc[long_condition, 'adx'] / 100.0) * 0.5 +
            (features_df.loc[long_condition, 'roc_10'] / 10.0).clip(0, 0.5)
        ).clip(0, 1)
        
        features_df.loc[short_condition, 'signal_strength'] = (
            (features_df.loc[short_condition, 'adx'] / 100.0) * 0.5 +
            (-features_df.loc[short_condition, 'roc_10'] / 10.0).clip(0, 0.5)
        ).clip(0, 1)
        
        return features_df
    
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
        # Trailing stop from highest price
        if current_price <= highest_price * (1 - self.trailing_stop_pct):
            return True, "trailing_stop"
        
        # Take profit
        if current_price >= entry_price * (1 + self.take_profit_pct):
            return True, "take_profit"
        
        # Weak trend
        if features.get('adx', 100) < self.weak_adx:
            return True, "weak_trend"
        
        # Momentum reversal
        if features.get('macd', 0) < 0:
            return True, "momentum_reversal"
        
        return False, ""
    
    def should_exit_short(
        self,
        current_price: float,
        entry_price: float,
        lowest_price: float,
        features: Dict
    ) -> Tuple[bool, str]:
        """Check if should exit short position."""
        # Trailing stop from lowest price
        if current_price >= lowest_price * (1 + self.trailing_stop_pct):
            return True, "trailing_stop"
        
        # Take profit
        if current_price <= entry_price * (1 - self.take_profit_pct):
            return True, "take_profit"
        
        # Weak trend
        if features.get('adx', 100) < self.weak_adx:
            return True, "weak_trend"
        
        # Momentum reversal
        if features.get('macd', 0) > 0:
            return True, "momentum_reversal"
        
        return False, ""
