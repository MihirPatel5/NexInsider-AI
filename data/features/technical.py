"""
features/technical.py — Technical indicator feature engineering.
Uses pandas-ta for all indicators. Returns a DataFrame with all features.

Indicators: RSI, MACD, Bollinger Bands, ATR, EMA/SMA, VWAP, OBV,
            Stochastic, ADX, Ichimoku, Donchian Channels.
"""
import pandas as pd
import pandas_ta as ta
from loguru import logger


def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all technical indicators on an OHLCV DataFrame.

    Args:
        df: DataFrame with columns [time, open, high, low, close, volume]
            Must have at least 60 rows for reliable indicator computation.

    Returns:
        Original DataFrame with indicator columns appended.
    """
    if len(df) < 30:
        logger.warning(f"[features] Only {len(df)} rows — some indicators may be NaN-heavy")

    df = df.copy().sort_values("time").reset_index(drop=True)

    # ── Momentum ────────────────────────────────────────────────────────────
    df.ta.rsi(length=14, append=True)         # RSI_14
    df.ta.rsi(length=9,  append=True)         # RSI_9

    macd = df.ta.macd(fast=12, slow=26, signal=9, append=True)
    # Adds: MACD_12_26_9, MACDh_12_26_9 (histogram), MACDs_12_26_9 (signal)

    stoch = df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
    # Adds: STOCHk_14_3_3, STOCHd_14_3_3

    df.ta.roc(length=10, append=True)         # ROC_10 (rate of change)
    df.ta.roc(length=20, append=True)         # ROC_20

    # ── Trend ───────────────────────────────────────────────────────────────
    for period in [9, 21, 50, 100, 200]:
        df.ta.ema(length=period, append=True) # EMA_9 … EMA_200

    for period in [20, 50, 200]:
        df.ta.sma(length=period, append=True) # SMA_20 … SMA_200

    df.ta.adx(length=14, append=True)         # ADX_14, DMP_14, DMN_14

    # Ichimoku Cloud
    ichimoku, _ = df.ta.ichimoku(lookahead=False)
    if ichimoku is not None:
        df = pd.concat([df, ichimoku], axis=1)

    # ── Volatility ──────────────────────────────────────────────────────────
    df.ta.atr(length=14, append=True)         # ATRr_14
    df.ta.bbands(length=20, std=2, append=True)
    # Adds: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0

    df.ta.donchian(lower_length=20, upper_length=20, append=True)
    # Adds: DCL_20_20, DCM_20_20, DCU_20_20

    # ── Volume ──────────────────────────────────────────────────────────────
    df.ta.obv(append=True)                    # OBV
    df.ta.vwap(append=True)                   # VWAP_D

    # Volume ratio vs 20-day average
    df["volume_ratio_20"] = df["volume"] / df["volume"].rolling(20).mean()

    # ── Derived / Composite ─────────────────────────────────────────────────
    # EMA crossover signals
    if "EMA_9" in df.columns and "EMA_21" in df.columns:
        df["ema_9_21_cross"] = (df["EMA_9"] > df["EMA_21"]).astype(int)

    if "EMA_50" in df.columns and "EMA_200" in df.columns:
        df["golden_cross"] = (df["EMA_50"] > df["EMA_200"]).astype(int)

    # Price relative to 52-week high/low
    df["pct_from_52w_high"] = (df["close"] - df["high"].rolling(252).max()) / df["high"].rolling(252).max()
    df["pct_from_52w_low"]  = (df["close"] - df["low"].rolling(252).min()) / df["low"].rolling(252).min()

    # ATR as % of price (normalised volatility)
    if "ATRr_14" in df.columns:
        df["atr_pct"] = df["ATRr_14"] / df["close"]

    # BB position within band
    if "BBL_20_2.0" in df.columns and "BBU_20_2.0" in df.columns:
        band_width = df["BBU_20_2.0"] - df["BBL_20_2.0"]
        df["bb_position"] = (df["close"] - df["BBL_20_2.0"]) / band_width.replace(0, float("nan"))

    logger.debug(f"[features] Computed {len(df.columns)} columns for {len(df)} rows")
    return df


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add log returns and forward returns for ML labeling."""
    df = df.copy()
    df["log_return_1d"]  = df["close"].pct_change(1).apply(lambda x: x)
    df["log_return_5d"]  = df["close"].pct_change(5)
    df["log_return_20d"] = df["close"].pct_change(20)

    # Forward returns (shift backward — used for labeling in training)
    df["fwd_return_1d"]  = df["close"].pct_change(1).shift(-1)
    df["fwd_return_5d"]  = df["close"].pct_change(5).shift(-5)
    df["fwd_return_20d"] = df["close"].pct_change(20).shift(-20)
    return df


def label_signals(
    df: pd.DataFrame,
    horizon: int = 5,
    buy_threshold: float = 0.01,
    sell_threshold: float = -0.01,
) -> pd.DataFrame:
    """
    Generate BUY/SELL/HOLD labels from forward returns for ML training.
    Default: BUY if 5-day forward return > 1%, SELL if < -1%, else HOLD.
    """
    fwd_col = f"fwd_return_{horizon}d"
    if fwd_col not in df.columns:
        df = compute_returns(df)

    df["label"] = "HOLD"
    df.loc[df[fwd_col] > buy_threshold,  "label"] = "BUY"
    df.loc[df[fwd_col] < sell_threshold, "label"] = "SELL"
    return df
