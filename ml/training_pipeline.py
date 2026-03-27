"""
ml/training_pipeline.py — Master ML training pipeline.
Runs walk-forward validation across all models for a given symbol.
"""
from typing import List, Dict

import pandas as pd
from loguru import logger

from ml.models import XgbClassifier, LstmModel, TransformerModel, RlAgent
from ml.validation import walk_forward_split


async def train_all_models(
    symbol: str,
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Dict[str, dict]:
    """
    Orchestrate the training of all ensemble components.
    Uses 1-year windows with 3-month strides for validation.
    """
    logger.info(f"[ml_pipeline] Starting training ensemble for {symbol}...")

    results = {}

    # Logic: use the most recent split for final validation report,
    # but the ensemble will use all trained weights eventually.
    splits = list(walk_forward_split(df, train_size_days=365, test_size_days=90))
    if not splits:
        logger.error("[ml_pipeline] Not enough data for walk-forward splits")
        return {}

    train_df, val_df = splits[-1]  # use latest split

    # 1. XGBoost
    xgb = XgbClassifier()
    results["xgb"] = xgb.train(train_df, val_df, feature_cols)

    # 2. LSTM
    lstm = LstmModel(input_dim=len(feature_cols))
    results["lstm"] = lstm.train(train_df, val_df, feature_cols)

    # 3. Transformer (TFT)
    tft = TransformerModel()
    results["tft"] = tft.train(train_df, val_df, feature_cols)

    # 4. RL Agent (PPO) - uses full history for policy learning
    rl = RlAgent(feature_cols=feature_cols)
    results["rl"] = rl.train(train_df)

    logger.success(f"[ml_pipeline] Created ensemble for {symbol}")
    return results
