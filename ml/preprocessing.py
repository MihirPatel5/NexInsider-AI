"""
ml/preprocessing.py — Shared preprocessing for ML models.
Handles scaling, missing value imputation, and feature selection.
"""
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from loguru import logger


class Preprocessor:
    def __init__(self, scaling_type: str = "standard"):
        self.scaler = StandardScaler() if scaling_type == "standard" else MinMaxScaler()
        self.feature_cols: List[str] = []

    def fit_transform(
        self, df: pd.DataFrame, feature_cols: List[str]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fit scaler on features and transform. Returns scaled features and labels.
        Expects 'label' column for classification or 'fwd_return_5d' for regression.
        """
        self.feature_cols = feature_cols
        X = df[feature_cols].copy()

        # Handle NaNs (common in technical indicators)
        X = X.fillna(method="ffill").fillna(0)

        X_scaled = self.scaler.fit_transform(X)

        y = None
        if "label" in df.columns:
            # Simple encoding for classification: SELL=0, HOLD=1, BUY=2
            y = df["label"].map({"SELL": 0, "HOLD": 1, "BUY": 2}).values
        elif "fwd_return_5d" in df.columns:
            y = df["fwd_return_5d"].values

        return X_scaled, y

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform new data using fitted scaler."""
        X = df[self.feature_cols].copy()
        X = X.fillna(method="ffill").fillna(0)
        return self.scaler.transform(X)


def prepare_sequences(
    X: np.ndarray, y: np.ndarray, window_size: int = 60
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare data for sequence models (LSTM/GRU).
    Returns X as [samples, window_size, features].
    """
    X_seq, y_seq = [], []
    for i in range(len(X) - window_size):
        X_seq.append(X[i : i + window_size])
        y_seq.append(y[i + window_size])

    return np.array(X_seq), np.array(y_seq)
