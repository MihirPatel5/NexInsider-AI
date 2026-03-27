"""
ml/ensemble.py — Ensemble layer for unified signal generation.
Combines probabilities from multiple models (XGB, LSTM, Transformer, RL)
and applies a sentiment multiplier to output the final signal.
"""
from typing import Dict, List

import numpy as np
from loguru import logger


class SignalEnsemble:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Weights for each model. Default is equal weighting.
        Weights should sum to 1.0.
        """
        self.weights = weights or {
            "xgb":       0.3,
            "lstm":      0.3,
            "transformer": 0.2,
            "rl":        0.2,
        }

    def combine(
        self,
        model_probs: Dict[str, np.ndarray],
        sentiment_score: float = 0,
        sentiment_multiplier: float = 0.15,
    ) -> Dict[str, any]:
        """
        Combine class probabilities [SELL, HOLD, BUY].

        Args:
            model_probs: Dict of {model_name: prob_array_of_3}
            sentiment_score: Compound score from -1.0 to 1.0
            sentiment_multiplier: How much sentiment affects the raw score

        Returns:
            {signal: BUY/SELL/HOLD, confidence: float}
        """
        final_probs = np.zeros(3)

        for name, prob in model_probs.items():
            weight = self.weights.get(name, 0)
            final_probs += weight * prob

        # Apply sentiment as a bias towards BUY (2) or SELL (0)
        # Shift probability mass based on sentiment
        if sentiment_score > 0:
            shift = sentiment_score * sentiment_multiplier
            final_probs[2] += shift
            final_probs[1] -= shift / 2
            final_probs[0] -= shift / 2
        elif sentiment_score < 0:
            shift = abs(sentiment_score) * sentiment_multiplier
            final_probs[0] += shift
            final_probs[1] -= shift / 2
            final_probs[2] -= shift / 2

        # Final normalization (ensure sum=1 and min=0)
        final_probs = np.clip(final_probs, 0, 1)
        final_probs /= final_probs.sum()

        signal_idx = int(np.argmax(final_probs))
        confidence = float(np.max(final_probs))

        labels = ["SELL", "HOLD", "BUY"]
        return {
            "signal":     labels[signal_idx],
            "confidence": confidence,
            "probs":      final_probs.tolist(),
        }
