"""
features/regime.py — Market regime detection.
Classifies the current market into BULL / BEAR / SIDEWAYS / HIGH_VOL.
Used to select the appropriate regime-specific ML model variant.
"""
from typing import Literal

import pandas as pd
from loguru import logger

Regime = Literal["BULL", "BEAR", "SIDEWAYS", "HIGH_VOL"]


def detect_regime(
    nifty_df: pd.DataFrame,
    vix: float,
    vix_high_threshold: float = 20.0,
    vix_very_high_threshold: float = 30.0,
    ema_period: int = 200,
    adx_period: int = 14,
    adx_trend_threshold: float = 25.0,
) -> Regime:
    """
    Classify the current market regime.

    Logic:
      1. If VIX > 30: HIGH_VOL (overrides all)
      2. If Nifty close > EMA_200 AND ADX > 25: BULL
      3. If Nifty close < EMA_200 AND ADX > 25: BEAR
      4. Else: SIDEWAYS

    Args:
        nifty_df: Daily OHLCV DataFrame for Nifty 50 (at least 250 bars)
        vix:      Current India VIX value
    """
    if len(nifty_df) < ema_period:
        logger.warning("[regime] Insufficient data for regime detection — defaulting SIDEWAYS")
        return "SIDEWAYS"

    nifty_df = nifty_df.sort_values("time").tail(ema_period + 50).copy()

    from ta.trend import EMAIndicator, ADXIndicator
    
    # Calculate EMA
    ema_indicator = EMAIndicator(close=nifty_df["close"], window=ema_period)
    nifty_df[f"EMA_{ema_period}"] = ema_indicator.ema_indicator()
    
    # Calculate ADX
    adx_indicator = ADXIndicator(high=nifty_df["high"], low=nifty_df["low"], close=nifty_df["close"], window=adx_period)
    nifty_df[f"ADX_{adx_period}"] = adx_indicator.adx()

    last = nifty_df.iloc[-1]
    ema_col = f"EMA_{ema_period}"
    adx_col = f"ADX_{adx_period}"

    ema_val = last.get(ema_col, None)
    adx_val = last.get(adx_col, None)
    close   = last["close"]

    # VIX override
    if vix >= vix_very_high_threshold:
        regime: Regime = "HIGH_VOL"
    elif ema_val and adx_val:
        trending = float(adx_val) > adx_trend_threshold
        above_ema = float(close) > float(ema_val)
        if trending and above_ema:
            regime = "BULL"
        elif trending and not above_ema:
            regime = "BEAR"
        else:
            regime = "SIDEWAYS"
    else:
        regime = "SIDEWAYS"

    ema_str = f"{ema_val:.1f}" if ema_val is not None else "N/A"
    adx_str = f"{adx_val:.1f}" if adx_val is not None else "N/A"
    
    logger.info(
        f"[regime] VIX={vix:.1f} | Close={close:.1f} | "
        f"EMA{ema_period}={ema_str} | ADX={adx_str} → {regime}"
    )
    return regime


def compute_regime_features(nifty_df: pd.DataFrame, vix: float) -> dict:
    """
    Return a flat dict of regime context features for the feature store.
    """
    regime = detect_regime(nifty_df, vix)
    nifty_df = nifty_df.sort_values("time")
    last = nifty_df.iloc[-1]

    advance_decline = nifty_df.get("advance_decline_ratio", pd.Series([1.0])).iloc[-1]

    return {
        "regime":              regime,
        "india_vix":           vix,
        "nifty_close":         float(last["close"]),
        "nifty_1d_return":     float(nifty_df["close"].pct_change(1).iloc[-1]),
        "nifty_5d_return":     float(nifty_df["close"].pct_change(5).iloc[-1]),
        "nifty_20d_return":    float(nifty_df["close"].pct_change(20).iloc[-1]),
        "advance_decline":     float(advance_decline),
        "regime_bull":         int(regime == "BULL"),
        "regime_bear":         int(regime == "BEAR"),
        "regime_sideways":     int(regime == "SIDEWAYS"),
        "regime_high_vol":     int(regime == "HIGH_VOL"),
    }
