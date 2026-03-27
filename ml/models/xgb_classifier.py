"""
ml/models/xgb_classifier.py — XGBoost classifier for BUY/SELL/HOLD signals.
Best for feature importance and non-linear patterns in technical indicators.
"""
from typing import List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report
from loguru import logger
import mlflow
import mlflow.xgboost

from ml.preprocessing import Preprocessor


class XgbClassifier:
    def __init__(self, params: Optional[dict] = None):
        self.params = params or {
            "objective":         "multi:softmax",
            "num_class":         3,
            "eval_metric":       "mlogloss",
            "max_depth":         6,
            "learning_rate":     0.05,
            "n_estimators":      500,
            "early_stopping_rounds": 20,
            "tree_method":       "hist",  # fast training
            "random_state":      42,
        }
        self.model = xgb.XGBClassifier(**self.params)
        self.preprocessor = Preprocessor(scaling_type="standard")

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        feature_cols: List[str],
        experiment_name: str = "xgb_classifier",
    ) -> dict:
        """
        Train the XGBoost model with MLflow tracking.
        """
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run() as run:
            X_train, y_train = self.preprocessor.fit_transform(train_df, feature_cols)
            X_val, y_val = self.preprocessor.transform(val_df), None
            # Need y_val to calculate accuracy
            _, y_val = self.preprocessor.fit_transform(val_df, feature_cols)

            logger.info(f"[xgb] Training on {len(X_train)} rows, validating on {len(X_val)}")

            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )

            # Metrics
            y_pred = self.model.predict(X_val)
            accuracy = accuracy_score(y_val, y_pred)

            mlflow.log_params(self.params)
            mlflow.log_metric("accuracy", accuracy)
            mlflow.xgboost.log_model(self.model, "model")

            logger.success(f"[xgb] Training complete. Val Accuracy: {accuracy:.4f}")
            return {"accuracy": accuracy, "run_id": run.info.run_id}

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict BUY(2)/SELL(0)/HOLD(1)."""
        X = self.preprocessor.transform(df)
        return self.model.predict(X)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Predict probabilities for each class."""
        X = self.preprocessor.transform(df)
        return self.model.predict_proba(X)
