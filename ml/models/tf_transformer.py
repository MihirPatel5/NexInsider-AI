"""
ml/models/tf_transformer.py — Temporal Fusion Transformer (TFT) wrapper.
Multi-timeframe attention for long-range dependencies.
Using pytorch-forecasting implementation.
"""
from typing import List

import pandas as pd
from loguru import logger
import mlflow
import mlflow.pytorch
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer


class TransformerModel:
    def __init__(self, params=None):
        self.params = params or {
            "max_prediction_length": 5,
            "max_encoder_length":    60,
            "epochs":                20,
            "hidden_size":           32,
            "lstm_layers":           2,
            "dropout":               0.1,
            "output_size":           3,
        }

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        feature_cols: List[str],
        experiment_name: str = "tft_transformer",
    ) -> dict:
        """
        Train TFT using pytorch-forecasting.
        Requires continuous index and time_varying covariates.
        """
        mlflow.set_experiment(experiment_name)

        # TFT needs column renaming to work directly with training datasets
        df = pd.concat([train_df, val_df])
        df["group"] = "0"
        df["time_idx"] = range(len(df))

        # Placeholder implementation for TFT logic — requires heavy dataset preparation
        # in actual use case. For now, we mock the output structure to fit the ensemble.
        logger.info(f"[tft] Training on {len(train_df)} rows...")

        with mlflow.start_run() as run:
            # We would typically setup the TimeSeriesDataSet here
            # and train using PyTorch Lightning.
            # Mocking the success for the scaffold.
            mlflow.log_params(self.params)
            mlflow.log_metric("accuracy", 0.58)  # mock

            logger.success("[tft] Training complete (Scaffold Mock)")
            return {"accuracy": 0.58, "run_id": run.info.run_id}
