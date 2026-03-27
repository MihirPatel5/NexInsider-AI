"""
ml/models/lstm_model.py — LSTM sequence model using PyTorch.
Predicts next-candle return direction or magnitude.
"""
from typing import List, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import pandas as pd
from loguru import logger
import mlflow
import mlflow.pytorch

from ml.preprocessing import Preprocessor, prepare_sequences


class LSTMNet(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2, output_dim=3):
        super(LSTMNet, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
        c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])  # take last time step
        return out


class LstmModel:
    def __init__(self, input_dim, params=None):
        self.params = params or {
            "hidden_dim": 64,
            "num_layers": 2,
            "lr":          0.001,
            "epochs":      50,
            "batch_size":  32,
            "window_size": 60,
        }
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = LSTMNet(
            input_dim=input_dim,
            hidden_dim=self.params["hidden_dim"],
            num_layers=self.params["num_layers"],
            output_dim=3  # BUY/SELL/HOLD
        ).to(self.device)
        self.preprocessor = Preprocessor(scaling_type="minmax")

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        feature_cols: List[str],
        experiment_name: str = "lstm_classifier",
    ) -> dict:
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run() as run:
            # 1. Preprocess
            X_train, y_train = self.preprocessor.fit_transform(train_df, feature_cols)
            X_val, y_val = self.preprocessor.transform(val_df), None
            _, y_val = self.preprocessor.fit_transform(val_df, feature_cols)

            # 2. Sequence datasets
            win = self.params["window_size"]
            X_train_seq, y_train_seq = prepare_sequences(X_train, y_train, win)
            X_val_seq, y_val_seq = prepare_sequences(X_val, y_val, win)

            train_loader = DataLoader(
                TensorDataset(torch.FloatTensor(X_train_seq), torch.LongTensor(y_train_seq)),
                batch_size=self.params["batch_size"], shuffle=True
            )
            val_loader = DataLoader(
                TensorDataset(torch.FloatTensor(X_val_seq), torch.LongTensor(y_val_seq)),
                batch_size=self.params["batch_size"]
            )

            # 3. Train
            criterion = nn.CrossEntropyLoss()
            optimizer = optim.Adam(self.model.parameters(), lr=self.params["lr"])

            best_acc = 0
            for epoch in range(self.params["epochs"]):
                self.model.train()
                for batch_X, batch_y in train_loader:
                    batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                    optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()

                # Valuation
                self.model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for batch_X, batch_y in val_loader:
                        batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                        outputs = self.model(batch_X)
                        _, predicted = torch.max(outputs.data, 1)
                        total += batch_y.size(0)
                        correct += (predicted == batch_y).sum().item()

                acc = correct / total
                mlflow.log_metric("accuracy", acc, step=epoch)

                if acc > best_acc:
                    best_acc = acc
                    mlflow.pytorch.log_model(self.model, "model")

            logger.success(f"[lstm] Training complete. Best Accuracy: {best_acc:.4f}")
            return {"accuracy": best_acc, "run_id": run.info.run_id}
