"""
ml/rl_env.py — Custom Gymnasium environment for RL trading.
Maximises Sharpe ratio via PPO policy.
"""
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd


class TradingEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        initial_balance: float = 100_000,
        commission: float = 0.0003,  # 0.03%
    ):
        super(TradingEnv, self).__init__()
        self.df = df.reset_index(drop=True)
        self.feature_cols = feature_cols
        self.initial_balance = initial_balance
        self.commission = commission

        # Action space: 0=SELL, 1=HOLD, 2=BUY
        self.action_space = spaces.Discrete(3)

        # Observation space: features + current position state
        # (X features, balance, position_qty, entry_price)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(len(feature_cols) + 3,),
            dtype=np.float32
        )

        self.reset()

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.qty = 0
        self.entry_price = 0
        self.pnl = 0

        obs = self._get_obs()
        return obs, {}

    def _get_obs(self):
        row = self.df.loc[self.current_step, self.feature_cols].values
        # Add position state (normalised)
        state = np.array([
            self.balance / self.initial_balance,
            self.qty,
            self.entry_price / max(self.df["close"].iloc[0], 1)
        ], dtype=np.float32)
        return np.concatenate([row, state]).astype(np.float32)

    def step(self, action: int):
        price = self.df.loc[self.current_step, "close"]

        # Action logic
        if action == 2:  # BUY
            if self.qty == 0:
                self.qty = self.balance / price
                self.balance -= self.qty * price * (1 + self.commission)
                self.entry_price = price
        elif action == 0:  # SELL
            if self.qty > 0:
                self.balance += self.qty * price * (1 - self.commission)
                self.qty = 0
                self.entry_price = 0

        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        truncated = False

        # Reward = % change in portfolio value
        current_val = self.balance + (self.qty * price)
        reward = (current_val - self.initial_balance) / self.initial_balance

        obs = self._get_obs() if not done else np.zeros(self.observation_space.shape)
        return obs, reward, done, truncated, {"portfolio_val": current_val}
