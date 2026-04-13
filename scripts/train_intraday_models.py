"""
Train ML models for intraday trading strategy.

This script:
1. Loads intraday data (5-min candles) from database
2. Calculates 27 technical indicators
3. Creates labels based on 30-minute forward returns
4. Trains XGBoost and Random Forest models
5. Saves models for intraday trading
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
from typing import Tuple, Dict
import joblib
import asyncpg
import asyncio

# ML libraries
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# Our modules
from data.features.technical import FeatureEngineer


# Model save directory
MODEL_DIR = Path("models/trained")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


async def load_intraday_data(
    symbol: str = "NIFTY50",
    interval: str = "5m",
    db_host: str = "localhost",
    db_port: int = 5432,
    db_name: str = "algotrading",
    db_user: str = "postgres",
    db_password: str = "postgres",
) -> pd.DataFrame:
    """
    Load intraday data from database.
    
    Args:
        symbol: Symbol to load
        interval: Candle interval (5m, 15m, etc.)
        db_*: Database connection parameters
    
    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Loading {symbol} {interval} data from database...")
    
    conn = await asyncpg.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
    )
    
    try:
        # Load data
        query = """
            SELECT time, open, high, low, close, volume
            FROM ohlcv_intraday
            WHERE symbol = $1 AND interval = $2
            ORDER BY time ASC
        """
        
        rows = await conn.fetch(query, symbol, interval)
        
        if not rows:
            logger.error(f"No data found for {symbol} {interval}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        logger.info(f"✅ Loaded {len(df)} candles")
        logger.info(f"   Date range: {df['time'].min()} to {df['time'].max()}")
        
        return df
    
    finally:
        await conn.close()


def create_intraday_labels(
    df: pd.DataFrame,
    forward_candles: int = 2,  # 2 candles = 10 minutes for 5m interval (AGGRESSIVE)
    threshold: float = 0.002,  # 0.2% for intraday (LOWER for more signals)
) -> pd.DataFrame:
    """
    Create labels for intraday classification.
    
    Labels based on forward price movement:
    - 1 (BUY): Price up > threshold in next N candles
    - 0 (HOLD): Price change between -threshold and threshold
    - -1 (SELL): Price down > threshold in next N candles
    
    Args:
        df: DataFrame with 'close' column
        forward_candles: Number of candles to look forward (default: 6 = 30 min for 5m)
        threshold: Return threshold for BUY/SELL (default: 0.3%)
    
    Returns:
        DataFrame with 'label' column
    """
    logger.info(f"Creating intraday labels...")
    logger.info(f"  Forward candles: {forward_candles} (= {forward_candles * 5} minutes for 5m interval)")
    logger.info(f"  Threshold: {threshold * 100:.1f}%")
    
    # Calculate forward return
    df['future_close'] = df['close'].shift(-forward_candles)
    df['future_return'] = (df['future_close'] - df['close']) / df['close']
    
    # Create labels
    df['label'] = 1  # HOLD (will be mapped to 1)
    df.loc[df['future_return'] > threshold, 'label'] = 2  # BUY (will be mapped to 2)
    df.loc[df['future_return'] < -threshold, 'label'] = 0  # SELL (will be mapped to 0)
    
    # Remove rows with NaN (last forward_candles rows)
    df = df[:-forward_candles].copy()
    
    # Remove rows with NaN in future_return
    df = df.dropna(subset=['future_return'])
    
    logger.info(f"✅ Created labels:")
    logger.info(f"  SELL (0): {(df['label'] == 0).sum()} ({(df['label'] == 0).sum() / len(df) * 100:.1f}%)")
    logger.info(f"  HOLD (1): {(df['label'] == 1).sum()} ({(df['label'] == 1).sum() / len(df) * 100:.1f}%)")
    logger.info(f"  BUY (2): {(df['label'] == 2).sum()} ({(df['label'] == 2).sum() / len(df) * 100:.1f}%)")
    
    return df


def prepare_training_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, list]:
    """
    Prepare features and labels for training.
    
    Args:
        df: DataFrame with features and labels
    
    Returns:
        Tuple of (X, y, feature_names)
    """
    logger.info("Preparing training data...")
    
    # Feature columns (exclude metadata and label columns)
    exclude_cols = ['time', 'open', 'high', 'low', 'close', 'volume', 
                    'label', 'future_close', 'future_return']
    
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    # Remove any remaining NaN
    df = df.dropna(subset=feature_cols + ['label'])
    
    X = df[feature_cols]
    y = df['label']
    
    logger.info(f"✅ Training data prepared:")
    logger.info(f"  Samples: {len(X)}")
    logger.info(f"  Features: {len(feature_cols)}")
    logger.info(f"  Feature names: {feature_cols[:5]}... (showing first 5)")
    
    return X, y, feature_cols


def train_models(X_train, X_test, y_train, y_test, feature_names: list) -> Dict:
    """
    Train XGBoost and Random Forest models.
    
    Args:
        X_train, X_test: Training and test features
        y_train, y_test: Training and test labels
        feature_names: List of feature names
    
    Returns:
        Dict with trained models and metrics
    """
    logger.info("="*80)
    logger.info("TRAINING MODELS")
    logger.info("="*80)
    
    results = {}
    
    # 1. Train XGBoost
    logger.info("\n1. Training XGBoost...")
    xgb_model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1,
    )
    
    xgb_model.fit(X_train, y_train)
    
    # Evaluate
    y_pred_xgb = xgb_model.predict(X_test)
    xgb_accuracy = accuracy_score(y_test, y_pred_xgb)
    
    logger.info(f"\n✅ XGBoost trained!")
    logger.info(f"   Accuracy: {xgb_accuracy * 100:.1f}%")
    logger.info(f"\nClassification Report:")
    print(classification_report(y_test, y_pred_xgb, target_names=['SELL', 'HOLD', 'BUY']))
    
    results['xgboost'] = {
        'model': xgb_model,
        'accuracy': xgb_accuracy,
        'predictions': y_pred_xgb,
    }
    
    # 2. Train Random Forest
    logger.info("\n2. Training Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    
    rf_model.fit(X_train, y_train)
    
    # Evaluate
    y_pred_rf = rf_model.predict(X_test)
    rf_accuracy = accuracy_score(y_test, y_pred_rf)
    
    logger.info(f"\n✅ Random Forest trained!")
    logger.info(f"   Accuracy: {rf_accuracy * 100:.1f}%")
    logger.info(f"\nClassification Report:")
    print(classification_report(y_test, y_pred_rf, target_names=['SELL', 'HOLD', 'BUY']))
    
    results['random_forest'] = {
        'model': rf_model,
        'accuracy': rf_accuracy,
        'predictions': y_pred_rf,
    }
    
    # Feature importance (XGBoost)
    logger.info("\n" + "="*80)
    logger.info("FEATURE IMPORTANCE (XGBoost)")
    logger.info("="*80)
    
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': xgb_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("\nTop 10 features:")
    for idx, row in feature_importance.head(10).iterrows():
        logger.info(f"  {row['feature']:<30} {row['importance']:.4f}")
    
    results['feature_importance'] = feature_importance
    
    return results


async def main():
    """Main training pipeline."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Train intraday ML models')
    parser.add_argument('--symbol', type=str, default='NIFTY50',
                       help='Symbol to train on (default: NIFTY50)')
    parser.add_argument('--interval', type=str, default='5m',
                       help='Candle interval (default: 5m)')
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("INTRADAY ML MODEL TRAINING")
    logger.info("="*80)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Interval: {args.interval}")
    logger.info("")
    
    # 1. Load intraday data
    df = await load_intraday_data(symbol=args.symbol, interval=args.interval)
    
    if df is None or df.empty:
        logger.error("Failed to load data!")
        return 1
    
    # 2. Calculate technical indicators
    logger.info("\n" + "="*80)
    logger.info("CALCULATING TECHNICAL INDICATORS")
    logger.info("="*80)
    
    feature_engineer = FeatureEngineer()
    df_features = feature_engineer.extract_features(df, include_all=True)
    
    logger.info(f"✅ Calculated {len(df_features.columns)} features")
    logger.info(f"   Features: {list(df_features.columns[:5])}... (showing first 5)")
    
    # Merge with original data
    df = df.join(df_features)
    
    # 3. Create labels
    logger.info("\n" + "="*80)
    logger.info("CREATING LABELS")
    logger.info("="*80)
    
    df = create_intraday_labels(
        df,
        forward_candles=6,  # 30 minutes for 5m interval
        threshold=0.003,  # 0.3%
    )
    
    # 4. Prepare training data
    logger.info("\n" + "="*80)
    logger.info("PREPARING TRAINING DATA")
    logger.info("="*80)
    
    X, y, feature_names = prepare_training_data(df)
    
    # 5. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"\nTrain/Test Split:")
    logger.info(f"  Training samples: {len(X_train)}")
    logger.info(f"  Test samples: {len(X_test)}")
    
    # 6. Train models
    logger.info("\n" + "="*80)
    logger.info("TRAINING MODELS")
    logger.info("="*80)
    
    results = train_models(X_train, X_test, y_train, y_test, feature_names)
    
    # 7. Save models
    logger.info("\n" + "="*80)
    logger.info("SAVING MODELS")
    logger.info("="*80)
    
    # Save XGBoost
    xgb_path = MODEL_DIR / f"xgboost_intraday_{args.symbol}.joblib"
    joblib.dump(results['xgboost']['model'], xgb_path)
    logger.info(f"✅ Saved XGBoost: {xgb_path}")
    
    # Save Random Forest
    rf_path = MODEL_DIR / f"random_forest_intraday_{args.symbol}.joblib"
    joblib.dump(results['random_forest']['model'], rf_path)
    logger.info(f"✅ Saved Random Forest: {rf_path}")
    
    # Save feature names
    features_path = MODEL_DIR / f"feature_names_intraday_{args.symbol}.joblib"
    joblib.dump(feature_names, features_path)
    logger.info(f"✅ Saved feature names: {features_path}")
    
    # 8. Summary
    logger.info("\n" + "="*80)
    logger.info("TRAINING COMPLETE")
    logger.info("="*80)
    logger.info(f"\nModels trained on {len(X_train)} samples")
    logger.info(f"Tested on {len(X_test)} samples")
    logger.info(f"\nResults:")
    logger.info(f"  XGBoost accuracy: {results['xgboost']['accuracy'] * 100:.1f}%")
    logger.info(f"  Random Forest accuracy: {results['random_forest']['accuracy'] * 100:.1f}%")
    logger.info(f"\nModels saved to: {MODEL_DIR}")
    logger.info(f"  - xgboost_intraday_{args.symbol}.joblib")
    logger.info(f"  - random_forest_intraday_{args.symbol}.joblib")
    logger.info(f"  - feature_names_intraday_{args.symbol}.joblib")
    logger.info("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
