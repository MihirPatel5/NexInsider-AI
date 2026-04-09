"""
ml/models/rl_agent.py — PPO RL Agent implementation.
Uses stable-baselines3 to train the policy in our TradingEnv.
"""
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import pandas as pd
import numpy as np
from loguru import logger
import mlflow

from ml.rl_env import TradingEnv


class RlAgent:
    def __init__(self, feature_cols, params=None):
        self.feature_cols = feature_cols
        self.params = params or {
            "policy":        "MlpPolicy",
            "learning_rate": 0.0003,
            "n_steps":       2048,
            "batch_size":    64,
            "n_epochs":      10,
            "gamma":         0.99,
        }
        self.model = None

    def train(self, df: pd.DataFrame, total_timesteps: int = 50_000):
        mlflow.set_experiment("rl_agent_ppo")

        env = DummyVecEnv([lambda: TradingEnv(df, self.feature_cols)])

        with mlflow.start_run() as run:
            self.model = PPO(
                self.params["policy"],
                env,
                verbose=0,
                learning_rate=self.params["learning_rate"],
                n_steps=self.params["n_steps"],
                batch_size=self.params["batch_size"],
                n_epochs=self.params["n_epochs"],
                gamma=self.params["gamma"],
            )

            logger.info(f"[rl] Training PPO for {total_timesteps} steps...")
            self.model.learn(total_timesteps=total_timesteps)

            mlflow.log_params(self.params)
            mlflow.log_metric("total_steps", total_timesteps)
            # SB3 models use a different saving method, but we can log path
            self.model.save("ppo_trading_model")
            mlflow.log_artifact("ppo_trading_model.zip")

            logger.success("[rl] Training complete.")
            return {"run_id": run.info.run_id}

    def predict_probs(self, df: pd.DataFrame) -> np.ndarray:
        """
        Approximate probabilities for [SELL, HOLD, BUY] from policy.
        PPO doesn't expose raw probabilities easily for Discrete,
        so we sample the policy action distribution.
        """
        # (Mock implementation for probabilities)
        # In actual use, we'd query policy.get_distribution(obs)
        return np.array([0.1, 0.8, 0.1])
