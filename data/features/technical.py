"""
data/features/technical.py - Technical indicator calculations.

Provides comprehensive technical indicators for ML feature engineering.
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from loguru import logger


class TechnicalIndicators:
    """Calculate technical indicators for trading signals."""
    
    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            prices: Array of closing prices
            period: RSI period (default 14)
        
        Returns:
            Array of RSI values (0-100)
        """
        if len(prices) < period + 1:
            return np.full(len(prices), 50.0)
        
        # Calculate price changes
        deltas = np.diff(prices)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gains and losses
        avg_gains = np.zeros(len(prices))
        avg_losses = np.zeros(len(prices))
        
        # Initial averages
        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])
        
        # Smoothed averages
        for i in range(period + 1, len(prices)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period
        
        # Calculate RS and RSI (suppress warnings for division by zero)
        with np.errstate(divide='ignore', invalid='ignore'):
            rs = np.where(avg_losses != 0, avg_gains / avg_losses, 0)
            rsi = 100 - (100 / (1 + rs))
        
        # Fill initial values with 50 (neutral)
        rsi[:period] = 50.0
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: np.ndarray,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: Array of closing prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
        
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        if len(prices) < slow_period:
            zeros = np.zeros(len(prices))
            return zeros, zeros, zeros
        
        # Calculate EMAs
        fast_ema = TechnicalIndicators._calculate_ema(prices, fast_period)
        slow_ema = TechnicalIndicators._calculate_ema(prices, slow_period)
        
        # MACD line
        macd_line = fast_ema - slow_ema
        
        # Signal line
        signal_line = TechnicalIndicators._calculate_ema(macd_line, signal_period)
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: np.ndarray,
        period: int = 20,
        num_std: float = 2.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: Array of closing prices
            period: Moving average period
            num_std: Number of standard deviations
        
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        if len(prices) < period:
            middle = np.full(len(prices), np.mean(prices))
            return middle, middle, middle
        
        # Calculate SMA (middle band)
        middle_band = TechnicalIndicators._calculate_sma(prices, period)
        
        # Calculate standard deviation
        std = np.zeros(len(prices))
        for i in range(period - 1, len(prices)):
            std[i] = np.std(prices[i - period + 1:i + 1])
        
        # Fill initial values
        std[:period - 1] = std[period - 1]
        
        # Calculate bands
        upper_band = middle_band + (num_std * std)
        lower_band = middle_band - (num_std * std)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_atr(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14,
    ) -> np.ndarray:
        """
        Calculate Average True Range (ATR).
        
        Args:
            high: Array of high prices
            low: Array of low prices
            close: Array of closing prices
            period: ATR period
        
        Returns:
            Array of ATR values
        """
        if len(close) < 2:
            return np.zeros(len(close))
        
        # Calculate True Range
        tr = np.zeros(len(close))
        
        for i in range(1, len(close)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr[i] = max(hl, hc, lc)
        
        # First TR is just high - low
        tr[0] = high[0] - low[0]
        
        # Calculate ATR (smoothed TR)
        atr = np.zeros(len(close))
        atr[period - 1] = np.mean(tr[:period])
        
        for i in range(period, len(close)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        # Fill initial values
        atr[:period - 1] = atr[period - 1] if period - 1 < len(atr) else 0
        
        return atr
    
    @staticmethod
    def calculate_stochastic(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        k_period: int = 14,
        d_period: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate Stochastic Oscillator.
        
        Args:
            high: Array of high prices
            low: Array of low prices
            close: Array of closing prices
            k_period: %K period
            d_period: %D period (smoothing)
        
        Returns:
            Tuple of (%K, %D)
        """
        if len(close) < k_period:
            zeros = np.zeros(len(close))
            return zeros, zeros
        
        # Calculate %K
        k = np.zeros(len(close))
        
        for i in range(k_period - 1, len(close)):
            period_high = np.max(high[i - k_period + 1:i + 1])
            period_low = np.min(low[i - k_period + 1:i + 1])
            
            if period_high != period_low:
                k[i] = 100 * (close[i] - period_low) / (period_high - period_low)
            else:
                k[i] = 50.0
        
        # Fill initial values
        k[:k_period - 1] = 50.0
        
        # Calculate %D (SMA of %K)
        d = TechnicalIndicators._calculate_sma(k, d_period)
        
        return k, d
    
    @staticmethod
    def calculate_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Calculate On-Balance Volume (OBV).
        
        Args:
            close: Array of closing prices
            volume: Array of volumes
        
        Returns:
            Array of OBV values
        """
        if len(close) < 2:
            return np.zeros(len(close))
        
        obv = np.zeros(len(close))
        obv[0] = volume[0]
        
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif close[i] < close[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
        
        return obv
    
    @staticmethod
    def calculate_adx(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14,
    ) -> np.ndarray:
        """
        Calculate Average Directional Index (ADX).
        
        Args:
            high: Array of high prices
            low: Array of low prices
            close: Array of closing prices
            period: ADX period
        
        Returns:
            Array of ADX values
        """
        if len(close) < period + 1:
            return np.full(len(close), 25.0)
        
        # Calculate +DM and -DM
        plus_dm = np.zeros(len(close))
        minus_dm = np.zeros(len(close))
        
        for i in range(1, len(close)):
            high_diff = high[i] - high[i-1]
            low_diff = low[i-1] - low[i]
            
            if high_diff > low_diff and high_diff > 0:
                plus_dm[i] = high_diff
            if low_diff > high_diff and low_diff > 0:
                minus_dm[i] = low_diff
        
        # Calculate ATR
        atr = TechnicalIndicators.calculate_atr(high, low, close, period)
        
        # Calculate smoothed +DM and -DM
        plus_di = np.zeros(len(close))
        minus_di = np.zeros(len(close))
        
        # Initial sums
        plus_dm_sum = np.sum(plus_dm[1:period + 1])
        minus_dm_sum = np.sum(minus_dm[1:period + 1])
        
        for i in range(period, len(close)):
            if i == period:
                plus_di[i] = 100 * plus_dm_sum / atr[i] if atr[i] != 0 else 0
                minus_di[i] = 100 * minus_dm_sum / atr[i] if atr[i] != 0 else 0
            else:
                plus_dm_sum = plus_dm_sum - plus_dm_sum / period + plus_dm[i]
                minus_dm_sum = minus_dm_sum - minus_dm_sum / period + minus_dm[i]
                plus_di[i] = 100 * plus_dm_sum / atr[i] if atr[i] != 0 else 0
                minus_di[i] = 100 * minus_dm_sum / atr[i] if atr[i] != 0 else 0
        
        # Calculate DX
        dx = np.zeros(len(close))
        for i in range(period, len(close)):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum != 0:
                dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / di_sum
        
        # Calculate ADX (smoothed DX)
        adx = np.zeros(len(close))
        adx[period * 2 - 1] = np.mean(dx[period:period * 2])
        
        for i in range(period * 2, len(close)):
            adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
        
        # Fill initial values
        adx[:period * 2 - 1] = 25.0
        
        return adx
    
    @staticmethod
    def calculate_roc(prices: np.ndarray, period: int = 12) -> np.ndarray:
        """
        Calculate Rate of Change (ROC).
        
        Args:
            prices: Array of closing prices
            period: ROC period
        
        Returns:
            Array of ROC values (percentage)
        """
        if len(prices) < period + 1:
            return np.zeros(len(prices))
        
        roc = np.zeros(len(prices))
        
        for i in range(period, len(prices)):
            if prices[i - period] != 0:
                roc[i] = 100 * (prices[i] - prices[i - period]) / prices[i - period]
        
        return roc
    
    @staticmethod
    def _calculate_sma(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return np.full(len(prices), np.mean(prices))
        
        sma = np.zeros(len(prices))
        
        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1:i + 1])
        
        # Fill initial values
        sma[:period - 1] = sma[period - 1] if period - 1 < len(sma) else np.mean(prices)
        
        return sma
    
    @staticmethod
    def _calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return np.full(len(prices), np.mean(prices))
        
        ema = np.zeros(len(prices))
        multiplier = 2 / (period + 1)
        
        # Start with SMA
        ema[period - 1] = np.mean(prices[:period])
        
        # Calculate EMA
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
        
        # Fill initial values
        ema[:period - 1] = ema[period - 1]
        
        return ema


class FeatureEngineer:
    """Engineer features from OHLCV data for ML models."""
    
    def __init__(self):
        """Initialize feature engineer."""
        self.indicators = TechnicalIndicators()
    
    def extract_features(
        self,
        df: pd.DataFrame,
        include_all: bool = True,
    ) -> pd.DataFrame:
        """
        Extract comprehensive technical features from OHLCV data.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
            include_all: Include all indicators (True) or basic only (False)
        
        Returns:
            DataFrame with engineered features
        """
        features = pd.DataFrame(index=df.index)
        
        # Price-based features
        features['returns_1d'] = df['close'].pct_change()
        features['returns_5d'] = df['close'].pct_change(5)
        features['returns_20d'] = df['close'].pct_change(20)
        
        # Moving averages
        features['sma_20'] = self.indicators._calculate_sma(df['close'].values, 20)
        features['sma_50'] = self.indicators._calculate_sma(df['close'].values, 50)
        features['sma_200'] = self.indicators._calculate_sma(df['close'].values, 200)
        
        features['ema_12'] = self.indicators._calculate_ema(df['close'].values, 12)
        features['ema_26'] = self.indicators._calculate_ema(df['close'].values, 26)
        
        # Price relative to moving averages
        features['price_to_sma20'] = df['close'] / features['sma_20'] - 1
        features['price_to_sma50'] = df['close'] / features['sma_50'] - 1
        
        if include_all:
            # Momentum indicators
            features['rsi_14'] = self.indicators.calculate_rsi(df['close'].values, 14)
            
            macd, signal, hist = self.indicators.calculate_macd(df['close'].values)
            features['macd'] = macd
            features['macd_signal'] = signal
            features['macd_hist'] = hist
            
            features['roc_12'] = self.indicators.calculate_roc(df['close'].values, 12)
            
            # Volatility indicators
            features['atr_14'] = self.indicators.calculate_atr(
                df['high'].values,
                df['low'].values,
                df['close'].values,
                14
            )
            
            bb_upper, bb_middle, bb_lower = self.indicators.calculate_bollinger_bands(
                df['close'].values, 20, 2.0
            )
            features['bb_upper'] = bb_upper
            features['bb_middle'] = bb_middle
            features['bb_lower'] = bb_lower
            features['bb_width'] = (bb_upper - bb_lower) / bb_middle
            features['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # Volume indicators
            features['obv'] = self.indicators.calculate_obv(
                df['close'].values,
                df['volume'].values
            )
            features['volume_sma_20'] = self.indicators._calculate_sma(df['volume'].values, 20)
            features['volume_ratio'] = df['volume'] / features['volume_sma_20']
            
            # Trend indicators
            features['adx_14'] = self.indicators.calculate_adx(
                df['high'].values,
                df['low'].values,
                df['close'].values,
                14
            )
            
            stoch_k, stoch_d = self.indicators.calculate_stochastic(
                df['high'].values,
                df['low'].values,
                df['close'].values,
                14, 3
            )
            features['stoch_k'] = stoch_k
            features['stoch_d'] = stoch_d
        
        # Fill NaN values
        features = features.bfill().ffill().fillna(0)
        
        return features
    
    def get_feature_names(self, include_all: bool = True) -> list:
        """Get list of feature names."""
        basic_features = [
            'returns_1d', 'returns_5d', 'returns_20d',
            'sma_20', 'sma_50', 'sma_200',
            'ema_12', 'ema_26',
            'price_to_sma20', 'price_to_sma50',
        ]
        
        if include_all:
            all_features = basic_features + [
                'rsi_14', 'macd', 'macd_signal', 'macd_hist', 'roc_12',
                'atr_14', 'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
                'obv', 'volume_sma_20', 'volume_ratio',
                'adx_14', 'stoch_k', 'stoch_d',
            ]
            return all_features
        
        return basic_features
