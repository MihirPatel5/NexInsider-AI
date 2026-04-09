"""
ml/data_split.py — Temporal data splitting with strict holdout protocol.
Ensures no data leakage and maintains temporal order for time-series data.
"""
from datetime import datetime, timedelta
from typing import Tuple, Optional
from pathlib import Path
import json

import pandas as pd
from loguru import logger


class DataSplitter:
    """
    Handles temporal splitting of data into train, validation, and holdout sets.
    
    Key principles:
    1. Temporal order preserved (no future data in training)
    2. Holdout set is strictly isolated (never touched during development)
    3. Split ratios: 60% train, 20% validation, 20% holdout
    4. Access controls enforced via metadata tracking
    """
    
    def __init__(
        self,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        holdout_ratio: float = 0.2,
        metadata_path: str = ".ml_metadata/data_splits.json"
    ):
        """
        Initialize data splitter with split ratios.
        
        Args:
            train_ratio: Proportion of data for training (default 0.6)
            val_ratio: Proportion of data for validation (default 0.2)
            holdout_ratio: Proportion of data for holdout (default 0.2)
            metadata_path: Path to store split metadata
        """
        if not abs(train_ratio + val_ratio + holdout_ratio - 1.0) < 1e-6:
            raise ValueError("Split ratios must sum to 1.0")
        
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.holdout_ratio = holdout_ratio
        self.metadata_path = Path(metadata_path)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._holdout_accessed = False
        self._load_metadata()
    
    def _load_metadata(self):
        """Load split metadata if exists."""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "splits": [],
                "holdout_access_log": []
            }
    
    def _save_metadata(self):
        """Save split metadata."""
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def split(
        self,
        df: pd.DataFrame,
        time_column: str = "time",
        split_name: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data temporally into train, validation, and holdout sets.
        
        Args:
            df: DataFrame with time column
            time_column: Name of the time column
            split_name: Optional name for this split (for tracking)
        
        Returns:
            Tuple of (train_df, val_df, holdout_df)
        """
        if time_column not in df.columns:
            raise ValueError(f"Time column '{time_column}' not found in DataFrame")
        
        # Sort by time
        df = df.sort_values(time_column).reset_index(drop=True)
        
        # Calculate split points
        n = len(df)
        train_end = int(n * self.train_ratio)
        val_end = int(n * (self.train_ratio + self.val_ratio))
        
        # Split data
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        holdout_df = df.iloc[val_end:].copy()
        
        # Log split metadata
        split_info = {
            "split_name": split_name or f"split_{len(self.metadata['splits'])}",
            "timestamp": datetime.now().isoformat(),
            "total_samples": n,
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "holdout_samples": len(holdout_df),
            "train_date_range": [
                train_df[time_column].min().isoformat(),
                train_df[time_column].max().isoformat()
            ],
            "val_date_range": [
                val_df[time_column].min().isoformat(),
                val_df[time_column].max().isoformat()
            ],
            "holdout_date_range": [
                holdout_df[time_column].min().isoformat(),
                holdout_df[time_column].max().isoformat()
            ]
        }
        
        self.metadata["splits"].append(split_info)
        self._save_metadata()
        
        logger.info(f"Data split complete: {split_info['split_name']}")
        logger.info(f"  Train: {len(train_df)} samples ({train_df[time_column].min()} to {train_df[time_column].max()})")
        logger.info(f"  Val: {len(val_df)} samples ({val_df[time_column].min()} to {val_df[time_column].max()})")
        logger.info(f"  Holdout: {len(holdout_df)} samples ({holdout_df[time_column].min()} to {holdout_df[time_column].max()})")
        
        return train_df, val_df, holdout_df
    
    def get_holdout(
        self,
        df: pd.DataFrame,
        time_column: str = "time",
        reason: str = "final_validation"
    ) -> pd.DataFrame:
        """
        Get holdout set with access logging.
        
        CRITICAL: This should only be called for final validation!
        
        Args:
            df: Full DataFrame
            time_column: Name of the time column
            reason: Reason for accessing holdout (logged for audit)
        
        Returns:
            Holdout DataFrame
        """
        # Log access
        access_log = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "samples": len(df)
        }
        self.metadata["holdout_access_log"].append(access_log)
        self._save_metadata()
        self._holdout_accessed = True
        
        logger.warning(f"🚨 HOLDOUT SET ACCESSED: {reason}")
        logger.warning(f"   Access count: {len(self.metadata['holdout_access_log'])}")
        
        # Sort and get holdout portion
        df = df.sort_values(time_column).reset_index(drop=True)
        n = len(df)
        val_end = int(n * (self.train_ratio + self.val_ratio))
        
        return df.iloc[val_end:].copy()
    
    def check_holdout_access(self) -> dict:
        """
        Check if holdout set has been accessed.
        
        Returns:
            Dict with access information
        """
        return {
            "accessed": len(self.metadata["holdout_access_log"]) > 0,
            "access_count": len(self.metadata["holdout_access_log"]),
            "access_log": self.metadata["holdout_access_log"]
        }
    
    def get_split_info(self) -> dict:
        """Get information about all splits."""
        return self.metadata


def create_temporal_split(
    df: pd.DataFrame,
    time_column: str = "time",
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    holdout_ratio: float = 0.2
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Convenience function for temporal splitting.
    
    Args:
        df: DataFrame with time column
        time_column: Name of the time column
        train_ratio: Proportion for training
        val_ratio: Proportion for validation
        holdout_ratio: Proportion for holdout
    
    Returns:
        Tuple of (train_df, val_df, holdout_df)
    """
    splitter = DataSplitter(train_ratio, val_ratio, holdout_ratio)
    return splitter.split(df, time_column)
