"""
ml/validation.py — Walk-forward validation framework.
Ensures no look-ahead bias by strictly splitting data chronologically.
"""
from datetime import datetime, timedelta
from typing import Generator, Tuple

import pandas as pd
from loguru import logger


def walk_forward_split(
    df: pd.DataFrame,
    train_size_days: int = 365 * 2,
    test_size_days: int = 90,
    stride_days: int = 30,
) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
    """
    Generator for walk-forward validation splits.

    Logic:
    1. Start at (min_date + train_size_days)
    2. Test window = next test_size_days
    3. Slide forward by stride_days
    4. Repeat until data ends

    Args:
        df: DataFrame with 'time' column (tz-aware)
        train_size_days: Fixed size of training window
        test_size_days: Size of each out-of-sample test window
        stride_days: How many days to slide forward between folds
    """
    df = df.sort_values("time").reset_index(drop=True)
    if df.empty:
        return

    start_date = df["time"].min()
    end_date = df["time"].max()

    curr_train_end = start_date + timedelta(days=train_size_days)

    while curr_train_end + timedelta(days=test_size_days) <= end_date:
        curr_test_end = curr_train_end + timedelta(days=test_size_days)

        train_set = df[(df["time"] >= start_date) & (df["time"] < curr_train_end)]
        test_set  = df[(df["time"] >= curr_train_end) & (df["time"] < curr_test_end)]

        if not test_set.empty:
            yield train_set, test_set

        curr_train_end += timedelta(days=stride_days)


def expanding_window_split(
    df: pd.DataFrame,
    min_train_size_days: int = 365,
    test_size_days: int = 30,
    stride_days: int = 30,
) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
    """
    Expanding window variant: training set grows over time.
    Useful for models that benefit from more historical context.
    """
    df = df.sort_values("time").reset_index(drop=True)
    if df.empty:
        return

    start_date = df["time"].min()
    end_date = df["time"].max()

    curr_train_end = start_date + timedelta(days=min_train_size_days)

    while curr_train_end + timedelta(days=test_size_days) <= end_date:
        curr_test_end = curr_train_end + timedelta(days=test_size_days)

        train_set = df[(df["time"] >= start_date) & (df["time"] < curr_train_end)]
        test_set  = df[(df["time"] >= curr_train_end) & (df["time"] < curr_test_end)]

        if not test_set.empty:
            yield train_set, test_set

        curr_train_end += timedelta(days=stride_days)
