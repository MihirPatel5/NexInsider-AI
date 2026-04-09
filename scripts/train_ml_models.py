"""
scripts/train_ml_models.py - Train ML models for trading strategy.

This script:
1. Loads historical data with 27 technical indicators
2. Creates labels (future returns)
3. Trains XGBoost and Random Forest models
4. Saves models to MLflow
5. Validates on test set
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

# ML libraries
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# Our modules
import psycopg2
from data.features.technical import FeatureEngineer


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="algotrading",
        user="postgres",
        password="postgres"
    )


# Model save directory
MODEL_DIR = Path("models/trained")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def create_labels(df: pd.DataFrame, forward_days: int = 5, threshold: float = 0.02) -> pd.DataFrame:
    """
    Create labels for classification.
    
    Labels:
    - 1 (BUY): Future return > threshold
    - 0 (HOLD): Future return between -threshold and threshold
    - -1 (SELL): Future return < -threshold
    
    Args:
        df: DataFrame with features (must have 'returns_1d' or similar price column)
        forward_days: Number of days to look forward (default: 5)
        threshold: Return threshold for BUY/SELL (default: 2%)
    
    Returns:
        DataFrame with 'label' column
    """
    # Use returns_1d to calculate future returns
    # First, we need to reconstruct close prices or use a price-based feature
    # Since we have price_to_sma20, sma_20, we can get close = price_to_sma20 * sma_20
    
    # But simpler: just use forward returns directly
    # Calculate cumulative return over forward_days
    df['future_return'] = df['returns_1d'].rolling(window=forward_days).sum().shift(-forward_days)
    
    # Create labels
    df['label'] = 0  # HOLD
    df.loc[df['future_return'] > threshold, 'label'] = 1  # BUY
    df.loc[df['future_return'] < -threshold, 'label'] = -1  # SELL
    
    # Remove rows with NaN (last forward_days rows)
    df = df[:-forward_days].copy()
    
    # Remove rows with NaN in future_return
    df = df.dropna(subset=['future_return'])
    
    logger.info(f"Created labels with {forward_days}-day forward return")
    logger.info(f"  BUY (1): {(df['label'] == 1).sum()} ({(df['label'] == 1).sum() / len(df) * 100:.1f}%)")
    logger.info(f"  HOLD (0): {(df['label'] == 0).sum()} ({(df['label'] == 0).sum() / len(df) * 100:.1f}%)")
    logger.info(f"  SELL (-1): {(df['label'] == -1).sum()} ({(df['label'] == -1).sum() / len(df) * 100:.1f}%)")
    
    return df


def load_data_from_db(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Load data from database.
    
    Args:
        symbol: Symbol to load
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        DataFrame with OHLCV data
    """
    conn = get_db_connection()
    
    query = """
        SELECT 
            time::date as date,
            open,
            high,
            low,
            close,
            volume
        FROM ohlcv
        WHERE symbol = %s
          AND exchange = %s
          AND interval = %s
          AND time >= %s
          AND time <= %s
        ORDER BY time ASC
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, 'NSE', '1d', start_date, end_date))
    conn.close()
    
    return df


def prepare_training_data(symbols: list) -> pd.DataFrame:
    """
    Prepare training data for all symbols.
    
    Args:
        symbols: List of symbols to load
    
    Returns:
        Combined DataFrame with features and labels
    """
    logger.info("="*80)
    logger.info("PREPARING TRAINING DATA")
    logger.info("="*80)
    
    feature_engineer = FeatureEngineer()
    
    all_data = []
    
    for symbol in symbols:
        logger.info(f"\nLoading {symbol}...")
        
        # Load data from database
        df = load_data_from_db(
            symbol=symbol,
            start_date="2020-01-01",
            end_date="2026-04-09"
        )
        
        if df.empty:
            logger.warning(f"No data for {symbol}")
            continue
        
        logger.info(f"  Loaded {len(df)} bars")
        
        # Extract features
        features_df = feature_engineer.extract_features(df)
        
        # Create labels
        labeled_df = create_labels(features_df, forward_days=5, threshold=0.02)
        
        # Add symbol column
        labeled_df['symbol'] = symbol
        
        all_data.append(labeled_df)
        
        logger.info(f"  ✅ {symbol}: {len(labeled_df)} samples")
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    logger.info(f"\n✅ Total samples: {len(combined_df)}")
    logger.info(f"   Symbols: {combined_df['symbol'].nunique()}")
    
    return combined_df


def select_features(df: pd.DataFrame) -> list:
    """
    Select features for training.
    
    Returns:
        List of feature column names
    """
    # All 27 technical indicators
    features = [
        # Price-based
        'returns_1d', 'returns_5d', 'returns_20d',
        'price_to_sma20', 'price_to_sma50', 'price_to_sma200',
        
        # Momentum
        'rsi_14', 'macd', 'macd_signal', 'macd_hist',
        'roc_10', 'stoch_k', 'stoch_d',
        
        # Trend
        'sma_20', 'sma_50', 'sma_200',
        'ema_12', 'ema_26',
        'adx',
        
        # Volatility
        'atr_14', 'bb_upper', 'bb_middle', 'bb_lower',
        
        # Volume
        'volume_ratio_5d', 'volume_ratio_20d', 'obv'
    ]
    
    # Filter to only features that exist in df
    available_features = [f for f in features if f in df.columns]
    
    logger.info(f"Selected {len(available_features)} features")
    
    return available_features


def train_xgboost(X_train, y_train, X_test, y_test) -> XGBClassifier:
    """
    Train XGBoost classifier.
    
    Args:
        X_train: Training features
        y_train: Training labels
        X_test: Test features
        y_test: Test labels
    
    Returns:
        Trained XGBoost model
    """
    logger.info("\n" + "="*80)
    logger.info("TRAINING XGBOOST MODEL")
    logger.info("="*80)
    
    # Initialize model
    model = XGBClassifier(
        max_depth=5,
        n_estimators=100,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss'
    )
    
    # Train
    logger.info("Training...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    logger.info(f"\n✅ XGBoost Training Complete")
    logger.info(f"   Accuracy: {accuracy:.4f}")
    
    # Classification report
    logger.info("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['SELL', 'HOLD', 'BUY']))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("\nTop 10 Features:")
    for idx, row in feature_importance.head(10).iterrows():
        logger.info(f"  {row['feature']:<20} {row['importance']:.4f}")
    
    return model


def train_random_forest(X_train, y_train, X_test, y_test) -> RandomForestClassifier:
    """
    Train Random Forest classifier.
    
    Args:
        X_train: Training features
        y_train: Training labels
        X_test: Test features
        y_test: Test labels
    
    Returns:
        Trained Random Forest model
    """
    logger.info("\n" + "="*80)
    logger.info("TRAINING RANDOM FOREST MODEL")
    logger.info("="*80)
    
    # Initialize model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    
    # Train
    logger.info("Training...")
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    logger.info(f"\n✅ Random Forest Training Complete")
    logger.info(f"   Accuracy: {accuracy:.4f}")
    
    # Classification report
    logger.info("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['SELL', 'HOLD', 'BUY']))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("\nTop 10 Features:")
    for idx, row in feature_importance.head(10).iterrows():
        logger.info(f"  {row['feature']:<20} {row['importance']:.4f}")
    
    return model


def save_models(xgb_model, rf_model, feature_names: list):
    """
    Save trained models to disk.
    
    Args:
        xgb_model: Trained XGBoost model
        rf_model: Trained Random Forest model
        feature_names: List of feature names
    """
    logger.info("\n" + "="*80)
    logger.info("SAVING MODELS")
    logger.info("="*80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save XGBoost
    xgb_path = MODEL_DIR / f"xgboost_{timestamp}.joblib"
    joblib.dump(xgb_model, xgb_path)
    logger.info(f"✅ Saved XGBoost: {xgb_path}")
    
    # Save Random Forest
    rf_path = MODEL_DIR / f"random_forest_{timestamp}.joblib"
    joblib.dump(rf_model, rf_path)
    logger.info(f"✅ Saved Random Forest: {rf_path}")
    
    # Save feature names
    features_path = MODEL_DIR / f"feature_names_{timestamp}.joblib"
    joblib.dump(feature_names, features_path)
    logger.info(f"✅ Saved feature names: {features_path}")
    
    # Save as "latest" for easy loading
    joblib.dump(xgb_model, MODEL_DIR / "xgboost_latest.joblib")
    joblib.dump(rf_model, MODEL_DIR / "random_forest_latest.joblib")
    joblib.dump(feature_names, MODEL_DIR / "feature_names_latest.joblib")
    logger.info(f"✅ Saved as 'latest' versions")


def main():
    """Main execution."""
    logger.info("="*80)
    logger.info("ML MODEL TRAINING - PRODUCTION STRATEGY")
    logger.info("="*80)
    logger.info(f"Start Time: {datetime.now()}")
    logger.info("")
    
    # Symbols to train on
    symbols = ['RELIANCE', 'TCS', 'HDFCBANK']
    
    # Step 1: Prepare data
    combined_df = prepare_training_data(symbols)
    
    # Step 2: Select features
    feature_cols = select_features(combined_df)
    
    # Step 3: Prepare X and y
    X = combined_df[feature_cols].copy()
    y = combined_df['label'].copy()
    
    # Remap labels: -1 (SELL) -> 0, 0 (HOLD) -> 1, 1 (BUY) -> 2
    y = y.map({-1: 0, 0: 1, 1: 2})
    
    # Handle any remaining NaN values
    X = X.ffill().bfill().fillna(0)
    
    logger.info(f"\n✅ Feature matrix: {X.shape}")
    logger.info(f"   Features: {len(feature_cols)}")
    logger.info(f"   Samples: {len(X)}")
    
    # Step 4: Train/test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )
    
    logger.info(f"\n✅ Train/Test Split:")
    logger.info(f"   Train: {len(X_train)} samples")
    logger.info(f"   Test: {len(X_test)} samples")
    
    # Step 5: Train XGBoost
    xgb_model = train_xgboost(X_train, y_train, X_test, y_test)
    
    # Step 6: Train Random Forest
    rf_model = train_random_forest(X_train, y_train, X_test, y_test)
    
    # Step 7: Save models
    save_models(xgb_model, rf_model, feature_cols)
    
    logger.info("\n" + "="*80)
    logger.info("TRAINING COMPLETE")
    logger.info("="*80)
    logger.info(f"End Time: {datetime.now()}")
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Test models with backtesting")
    logger.info("2. Run: python3 scripts/backtest_ml_strategy.py")
    logger.info("="*80)


if __name__ == "__main__":
    main()
