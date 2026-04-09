"""
ml/regime_ensemble.py — Regime-aware ensemble for adaptive model selection.

Uses different model weights based on the current market regime (BULL, BEAR, SIDEWAYS, HIGH_VOL).
This allows the system to adapt to different market conditions by emphasizing models
that perform better in each regime.
"""
from typing import Dict, Optional, Literal

import numpy as np
import pandas as pd
from loguru import logger

from data.features.regime import detect_regime, Regime


# Default weights per regime (optimized based on 6-year backtest analysis)
# Analysis showed: SIDEWAYS 61.1%, BULL 21.8%, BEAR 17.1%, HIGH_VOL 0%
DEFAULT_REGIME_WEIGHTS = {
    "BULL": {
        "xgb": 0.25,
        "lstm": 0.35,  # LSTM often good at capturing trends
        "transformer": 0.25,
        "rl": 0.15,
    },
    "BEAR": {
        "xgb": 0.35,  # XGBoost good at detecting reversals
        "lstm": 0.25,
        "transformer": 0.25,
        "rl": 0.15,
    },
    "SIDEWAYS": {
        "xgb": 0.28,  # More balanced weights for most common regime (61%)
        "lstm": 0.28,
        "transformer": 0.26,
        "rl": 0.18,
    },
    "HIGH_VOL": {
        "xgb": 0.45,  # XGBoost more conservative in high volatility (rare: 0%)
        "lstm": 0.20,
        "transformer": 0.20,
        "rl": 0.15,
    },
}


class RegimeAwareEnsemble:
    """
    Ensemble that adapts model weights based on market regime.
    
    Uses regime detection to determine current market state and applies
    regime-specific model weights for better performance.
    """
    
    def __init__(
        self,
        regime_weights: Optional[Dict[str, Dict[str, float]]] = None,
        default_weights: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize regime-aware ensemble.
        
        Args:
            regime_weights: Dict mapping regime to model weights
                           e.g., {"BULL": {"xgb": 0.3, "lstm": 0.4, ...}, ...}
            default_weights: Fallback weights if regime detection fails
        """
        self.regime_weights = regime_weights or DEFAULT_REGIME_WEIGHTS
        self.default_weights = default_weights or {
            "xgb": 0.3,
            "lstm": 0.3,
            "transformer": 0.2,
            "rl": 0.2,
        }
        
        # Validate weights
        self._validate_weights()
        
        logger.info("[RegimeAwareEnsemble] Initialized with regime-specific weights")
    
    def _validate_weights(self):
        """Validate that all regime weights sum to 1.0."""
        for regime, weights in self.regime_weights.items():
            total = sum(weights.values())
            if not (0.99 <= total <= 1.01):  # Allow small floating point errors
                logger.warning(
                    f"[RegimeAwareEnsemble] Weights for {regime} sum to {total:.4f}, "
                    f"normalizing to 1.0"
                )
                # Normalize
                for model in weights:
                    weights[model] /= total
    
    def get_regime_weights(
        self,
        nifty_df: pd.DataFrame,
        vix: float,
    ) -> tuple[Regime, Dict[str, float]]:
        """
        Detect current regime and return appropriate model weights.
        
        Args:
            nifty_df: Nifty 50 OHLCV data (at least 200 bars)
            vix: Current India VIX value
        
        Returns:
            Tuple of (regime, weights_dict)
        """
        try:
            regime = detect_regime(nifty_df, vix)
            weights = self.regime_weights.get(regime, self.default_weights)
            
            logger.info(
                f"[RegimeAwareEnsemble] Detected regime: {regime}, "
                f"using weights: {weights}"
            )
            
            return regime, weights
        
        except Exception as e:
            logger.error(
                f"[RegimeAwareEnsemble] Error detecting regime: {e}, "
                f"using default weights"
            )
            return "SIDEWAYS", self.default_weights
    
    def combine(
        self,
        model_probs: Dict[str, np.ndarray],
        nifty_df: pd.DataFrame,
        vix: float,
        sentiment_score: float = 0,
        sentiment_multiplier: float = 0.15,
    ) -> Dict[str, any]:
        """
        Combine model probabilities using regime-aware weights.
        
        Args:
            model_probs: Dict of {model_name: prob_array_of_3}
                        Each prob_array is [SELL_prob, HOLD_prob, BUY_prob]
            nifty_df: Nifty 50 OHLCV data for regime detection
            vix: Current India VIX value
            sentiment_score: Compound score from -1.0 to 1.0
            sentiment_multiplier: How much sentiment affects the raw score
        
        Returns:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": float,
                "probs": [sell_prob, hold_prob, buy_prob],
                "regime": str,
                "weights_used": dict
            }
        """
        # Detect regime and get appropriate weights
        regime, weights = self.get_regime_weights(nifty_df, vix)
        
        # Combine probabilities using regime-specific weights
        final_probs = np.zeros(3)
        
        for model_name, prob in model_probs.items():
            weight = weights.get(model_name, 0)
            final_probs += weight * prob
        
        # Apply sentiment as a bias towards BUY (2) or SELL (0)
        if sentiment_score > 0:
            shift = sentiment_score * sentiment_multiplier
            final_probs[2] += shift  # Increase BUY probability
            final_probs[1] -= shift / 2
            final_probs[0] -= shift / 2
        elif sentiment_score < 0:
            shift = abs(sentiment_score) * sentiment_multiplier
            final_probs[0] += shift  # Increase SELL probability
            final_probs[1] -= shift / 2
            final_probs[2] -= shift / 2
        
        # Normalize (ensure sum=1 and min=0)
        final_probs = np.clip(final_probs, 0, 1)
        final_probs /= final_probs.sum()
        
        # Determine signal
        signal_idx = int(np.argmax(final_probs))
        confidence = float(np.max(final_probs))
        
        labels = ["SELL", "HOLD", "BUY"]
        
        result = {
            "signal": labels[signal_idx],
            "confidence": confidence,
            "probs": final_probs.tolist(),
            "regime": regime,
            "weights_used": weights,
        }
        
        logger.debug(
            f"[RegimeAwareEnsemble] Regime={regime}, Signal={result['signal']}, "
            f"Confidence={confidence:.3f}"
        )
        
        return result
    
    def update_regime_weights(
        self,
        regime: Regime,
        new_weights: Dict[str, float],
    ):
        """
        Update weights for a specific regime.
        
        Useful for tuning based on backtesting or live performance.
        
        Args:
            regime: Regime to update ("BULL", "BEAR", "SIDEWAYS", "HIGH_VOL")
            new_weights: New model weights dict
        """
        # Validate weights sum to 1.0
        total = sum(new_weights.values())
        if not (0.99 <= total <= 1.01):
            logger.warning(
                f"[RegimeAwareEnsemble] New weights sum to {total:.4f}, normalizing"
            )
            new_weights = {k: v / total for k, v in new_weights.items()}
        
        self.regime_weights[regime] = new_weights
        logger.info(
            f"[RegimeAwareEnsemble] Updated weights for {regime}: {new_weights}"
        )
    
    def get_current_weights(self, regime: Regime) -> Dict[str, float]:
        """Get current weights for a specific regime."""
        return self.regime_weights.get(regime, self.default_weights)
