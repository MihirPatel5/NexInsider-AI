"""
scripts/analyze_regimes.py - Analyze regime distribution in historical data.

This script analyzes the distribution of market regimes (BULL, BEAR, SIDEWAYS, HIGH_VOL)
in the historical data to help optimize regime-specific model weights.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import asyncio
from loguru import logger
from collections import Counter
from typing import Dict, List

from data.db import get_session
from sqlalchemy import text
from data.features.regime import detect_regime


async def load_ohlcv_data(
    symbol: str,
    start_date: str = "2020-01-01",
    end_date: str = "2026-04-09",
) -> pd.DataFrame:
    """
    Load OHLCV data from database.
    
    Args:
        symbol: Symbol to load
        start_date: Start date
        end_date: End date
    
    Returns:
        DataFrame with OHLCV data
    """
    from datetime import datetime
    
    async with get_session() as session:
        query = text("""
            SELECT time, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = :symbol
              AND exchange = 'NSE'
              AND interval = '1d'
              AND time >= :start_date
              AND time <= :end_date
            ORDER BY time ASC
        """)
        
        result = await session.execute(
            query,
            {
                "symbol": symbol,
                "start_date": datetime.fromisoformat(start_date),
                "end_date": datetime.fromisoformat(end_date),
            }
        )
        
        rows = result.fetchall()
        
        if not rows:
            return None
        
        df = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert Decimal to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df


async def analyze_regime_distribution(
    symbols: List[str],
    start_date: str = "2020-01-01",
    end_date: str = "2026-04-09",
    vix_value: float = 20.0,
) -> Dict:
    """
    Analyze regime distribution across symbols and time periods.
    
    Args:
        symbols: List of symbols to analyze
        start_date: Start date for analysis
        end_date: End date for analysis
        vix_value: VIX value to use for regime detection
    
    Returns:
        Dict with regime statistics
    """
    all_regimes = []
    regime_by_symbol = {}
    regime_transitions = []
    
    for symbol in symbols:
        logger.info(f"Analyzing {symbol}...")
        
        # Load data
        df = await load_ohlcv_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        
        if df is None or len(df) < 200:
            logger.warning(f"Insufficient data for {symbol}")
            continue
        
        logger.info(f"Loaded {len(df)} bars for {symbol}")
        
        # Detect regime for each bar (using rolling window)
        regimes = []
        for i in range(200, len(df)):
            window_df = df.iloc[i-200:i+1].copy()
            regime = detect_regime(window_df, vix_value)
            regimes.append(regime)
        
        # Track regime transitions
        for i in range(1, len(regimes)):
            if regimes[i] != regimes[i-1]:
                regime_transitions.append((regimes[i-1], regimes[i]))
        
        regime_by_symbol[symbol] = regimes
        all_regimes.extend(regimes)
        
        logger.info(f"{symbol}: {len(regimes)} regime detections")
    
    # Calculate statistics
    regime_counts = Counter(all_regimes)
    total_bars = len(all_regimes)
    
    regime_percentages = {
        regime: (count / total_bars * 100) if total_bars > 0 else 0
        for regime, count in regime_counts.items()
    }
    
    # Transition matrix
    transition_counts = Counter(regime_transitions)
    
    # Calculate average regime duration
    regime_durations = {regime: [] for regime in ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOL"]}
    
    for symbol, regimes in regime_by_symbol.items():
        current_regime = regimes[0] if regimes else None
        duration = 1
        
        for i in range(1, len(regimes)):
            if regimes[i] == current_regime:
                duration += 1
            else:
                if current_regime:
                    regime_durations[current_regime].append(duration)
                current_regime = regimes[i]
                duration = 1
        
        # Add final duration
        if current_regime:
            regime_durations[current_regime].append(duration)
    
    avg_durations = {
        regime: np.mean(durations) if durations else 0
        for regime, durations in regime_durations.items()
    }
    
    return {
        "total_bars": total_bars,
        "regime_counts": dict(regime_counts),
        "regime_percentages": regime_percentages,
        "transition_counts": dict(transition_counts),
        "avg_durations": avg_durations,
        "regime_by_symbol": regime_by_symbol,
    }


def print_regime_analysis(stats: Dict):
    """Print regime analysis results."""
    print("\n" + "="*80)
    print("REGIME DISTRIBUTION ANALYSIS")
    print("="*80)
    
    print(f"\nTotal Bars Analyzed: {stats['total_bars']}")
    
    print("\n--- Regime Distribution ---")
    for regime in ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOL"]:
        count = stats['regime_counts'].get(regime, 0)
        pct = stats['regime_percentages'].get(regime, 0)
        print(f"{regime:12s}: {count:5d} bars ({pct:5.1f}%)")
    
    print("\n--- Average Regime Duration (days) ---")
    for regime in ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOL"]:
        duration = stats['avg_durations'].get(regime, 0)
        print(f"{regime:12s}: {duration:5.1f} days")
    
    print("\n--- Top 10 Regime Transitions ---")
    sorted_transitions = sorted(
        stats['transition_counts'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    for (from_regime, to_regime), count in sorted_transitions:
        print(f"{from_regime:12s} → {to_regime:12s}: {count:4d} times")
    
    print("\n" + "="*80)


def suggest_regime_weights(stats: Dict) -> Dict[str, Dict[str, float]]:
    """
    Suggest regime weights based on distribution analysis.
    
    Strategy:
    - More common regimes get more balanced weights
    - Less common regimes get more specialized weights
    - Transitions inform weight smoothing
    """
    percentages = stats['regime_percentages']
    
    # Base weights (current defaults)
    suggested_weights = {
        "BULL": {
            "xgb": 0.25,
            "lstm": 0.35,  # LSTM good at trends
            "transformer": 0.25,
            "rl": 0.15,
        },
        "BEAR": {
            "xgb": 0.35,  # XGBoost good at reversals
            "lstm": 0.25,
            "transformer": 0.25,
            "rl": 0.15,
        },
        "SIDEWAYS": {
            "xgb": 0.30,
            "lstm": 0.20,
            "transformer": 0.30,  # Transformer good at range-bound
            "rl": 0.20,
        },
        "HIGH_VOL": {
            "xgb": 0.40,  # XGBoost more conservative
            "lstm": 0.20,
            "transformer": 0.20,
            "rl": 0.20,
        },
    }
    
    # Adjust based on regime frequency
    # If a regime is very common, we want more balanced weights
    # If rare, we want more specialized weights
    
    for regime in ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOL"]:
        pct = percentages.get(regime, 0)
        
        if pct > 40:  # Very common regime
            # Make weights more balanced
            logger.info(f"{regime} is very common ({pct:.1f}%), using balanced weights")
            suggested_weights[regime] = {
                "xgb": 0.28,
                "lstm": 0.28,
                "transformer": 0.26,
                "rl": 0.18,
            }
        elif pct < 10:  # Rare regime
            # Make weights more specialized
            logger.info(f"{regime} is rare ({pct:.1f}%), using specialized weights")
            if regime == "HIGH_VOL":
                suggested_weights[regime] = {
                    "xgb": 0.45,  # Very conservative
                    "lstm": 0.20,
                    "transformer": 0.20,
                    "rl": 0.15,
                }
    
    return suggested_weights


async def main():
    """Main execution."""
    logger.info("Starting regime distribution analysis...")
    
    # Analyze NSE symbols
    symbols = ["HDFCBANK", "RELIANCE", "TCS"]
    
    stats = await analyze_regime_distribution(
        symbols=symbols,
        start_date="2020-01-01",
        end_date="2026-04-09",
        vix_value=20.0,
    )
    
    # Print analysis
    print_regime_analysis(stats)
    
    # Suggest weights
    print("\n" + "="*80)
    print("SUGGESTED REGIME WEIGHTS")
    print("="*80)
    
    suggested_weights = suggest_regime_weights(stats)
    
    for regime in ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOL"]:
        print(f"\n{regime}:")
        weights = suggested_weights[regime]
        for model, weight in weights.items():
            print(f"  {model:12s}: {weight:.2f}")
    
    print("\n" + "="*80)
    print("\nTo apply these weights, update DEFAULT_REGIME_WEIGHTS in ml/regime_ensemble.py")
    print("="*80)
    
    logger.info("Regime analysis complete!")


if __name__ == "__main__":
    asyncio.run(main())
