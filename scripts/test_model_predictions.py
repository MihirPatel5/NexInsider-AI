"""
scripts/test_model_predictions.py - Test trained model predictions

Tests the accuracy and performance of trained XGBoost and Random Forest models
on historical data to evaluate their predictive power.
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import joblib
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.features.technical import FeatureEngineer

load_dotenv()


def load_models():
    """Load trained models."""
    logger.info("Loading trained models...")
    
    xgb_model = joblib.load("models/trained/xgboost_latest.joblib")
    rf_model = joblib.load("models/trained/random_forest_latest.joblib")
    feature_names = joblib.load("models/trained/feature_names_latest.joblib")
    
    logger.info(f"✅ Loaded models with {len(feature_names)} features")
    
    return xgb_model, rf_model, feature_names


def load_test_data(symbol: str, start_date: str, end_date: str):
    """Load test data from database."""
    logger.info(f"Loading {symbol} data...")
    
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB', 'algotrading'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )
    
    query = """
        SELECT time, open, high, low, close, volume
        FROM ohlcv
        WHERE symbol = %s AND exchange = 'NSE' AND interval = '1d'
        AND time >= %s AND time <= %s
        ORDER BY time
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
    conn.close()
    
    logger.info(f"  Loaded {len(df)} bars")
    return df


def create_features(df: pd.DataFrame, feature_names: list):
    """Create technical features."""
    logger.info("Creating features...")
    
    engineer = FeatureEngineer()
    df_features = engineer.extract_features(df)
    
    # Add back close price for label creation
    df_features['close'] = df['close'].values[:len(df_features)]
    
    # Create labels (5-day forward return)
    df_features['forward_return'] = df_features['close'].pct_change(5).shift(-5)
    
    # Create labels: BUY (1), HOLD (0), SELL (-1)
    df_features['label'] = 0  # HOLD
    df_features.loc[df_features['forward_return'] > 0.02, 'label'] = 1  # BUY
    df_features.loc[df_features['forward_return'] < -0.02, 'label'] = -1  # SELL
    
    # Select only the features used in training
    available_features = [f for f in feature_names if f in df_features.columns]
    df_features = df_features[available_features + ['label', 'forward_return']]
    
    # Drop rows with NaN
    df_features = df_features.dropna()
    
    logger.info(f"  Created {len(df_features)} samples")
    logger.info(f"  BUY: {(df_features['label'] == 1).sum()}")
    logger.info(f"  HOLD: {(df_features['label'] == 0).sum()}")
    logger.info(f"  SELL: {(df_features['label'] == -1).sum()}")
    
    return df_features


def test_model_predictions(xgb_model, rf_model, feature_names, df_features):
    """Test model predictions."""
    logger.info("\nTesting model predictions...")
    
    # Select features
    X = df_features[feature_names]
    y_true = df_features['label']
    
    # Get predictions
    xgb_pred = xgb_model.predict(X)
    rf_pred = rf_model.predict(X)
    
    # Get probabilities
    xgb_proba = xgb_model.predict_proba(X)
    rf_proba = rf_model.predict_proba(X)
    
    # Ensemble prediction (average probabilities)
    ensemble_proba = (xgb_proba + rf_proba) / 2
    ensemble_pred = np.argmax(ensemble_proba, axis=1) - 1  # Convert to -1, 0, 1
    
    # Calculate accuracies
    xgb_acc = (xgb_pred == y_true).mean()
    rf_acc = (rf_pred == y_true).mean()
    ensemble_acc = (ensemble_pred == y_true).mean()
    
    logger.info(f"\n{'='*80}")
    logger.info("MODEL ACCURACIES")
    logger.info(f"{'='*80}")
    logger.info(f"XGBoost:      {xgb_acc:.1%}")
    logger.info(f"Random Forest: {rf_acc:.1%}")
    logger.info(f"Ensemble:     {ensemble_acc:.1%}")
    
    # Analyze predictions by class
    logger.info(f"\n{'='*80}")
    logger.info("PREDICTIONS BY CLASS")
    logger.info(f"{'='*80}")
    
    for model_name, predictions in [("XGBoost", xgb_pred), ("Random Forest", rf_pred), ("Ensemble", ensemble_pred)]:
        logger.info(f"\n{model_name}:")
        logger.info(f"  BUY predictions:  {(predictions == 1).sum()}")
        logger.info(f"  HOLD predictions: {(predictions == 0).sum()}")
        logger.info(f"  SELL predictions: {(predictions == -1).sum()}")
    
    # Calculate confidence statistics
    logger.info(f"\n{'='*80}")
    logger.info("CONFIDENCE STATISTICS")
    logger.info(f"{'='*80}")
    
    # Get max probability for each prediction (confidence)
    xgb_confidence = np.max(xgb_proba, axis=1)
    rf_confidence = np.max(rf_proba, axis=1)
    ensemble_confidence = np.max(ensemble_proba, axis=1)
    
    logger.info(f"\nXGBoost Confidence:")
    logger.info(f"  Mean: {xgb_confidence.mean():.3f}")
    logger.info(f"  Min:  {xgb_confidence.min():.3f}")
    logger.info(f"  Max:  {xgb_confidence.max():.3f}")
    logger.info(f"  >0.6: {(xgb_confidence > 0.6).sum()} ({(xgb_confidence > 0.6).mean():.1%})")
    logger.info(f"  >0.7: {(xgb_confidence > 0.7).sum()} ({(xgb_confidence > 0.7).mean():.1%})")
    logger.info(f"  >0.8: {(xgb_confidence > 0.8).sum()} ({(xgb_confidence > 0.8).mean():.1%})")
    
    logger.info(f"\nEnsemble Confidence:")
    logger.info(f"  Mean: {ensemble_confidence.mean():.3f}")
    logger.info(f"  Min:  {ensemble_confidence.min():.3f}")
    logger.info(f"  Max:  {ensemble_confidence.max():.3f}")
    logger.info(f"  >0.6: {(ensemble_confidence > 0.6).sum()} ({(ensemble_confidence > 0.6).mean():.1%})")
    logger.info(f"  >0.7: {(ensemble_confidence > 0.7).sum()} ({(ensemble_confidence > 0.7).mean():.1%})")
    logger.info(f"  >0.8: {(ensemble_confidence > 0.8).sum()} ({(ensemble_confidence > 0.8).mean():.1%})")
    
    # Test trading signals with different confidence thresholds
    logger.info(f"\n{'='*80}")
    logger.info("TRADING SIGNALS AT DIFFERENT CONFIDENCE THRESHOLDS")
    logger.info(f"{'='*80}")
    
    for threshold in [0.5, 0.6, 0.7, 0.8]:
        # Filter BUY signals by confidence
        buy_signals = (ensemble_pred == 1) & (ensemble_confidence >= threshold)
        num_signals = buy_signals.sum()
        
        if num_signals > 0:
            # Calculate accuracy of high-confidence BUY signals
            buy_accuracy = (y_true[buy_signals] == 1).mean()
            logger.info(f"\nConfidence >= {threshold}:")
            logger.info(f"  BUY signals: {num_signals}")
            logger.info(f"  Accuracy: {buy_accuracy:.1%}")
        else:
            logger.info(f"\nConfidence >= {threshold}: No BUY signals")
    
    return {
        'xgb_acc': xgb_acc,
        'rf_acc': rf_acc,
        'ensemble_acc': ensemble_acc,
        'xgb_pred': xgb_pred,
        'rf_pred': rf_pred,
        'ensemble_pred': ensemble_pred,
        'xgb_confidence': xgb_confidence,
        'rf_confidence': rf_confidence,
        'ensemble_confidence': ensemble_confidence,
        'y_true': y_true
    }


def main():
    """Main execution."""
    logger.info("="*80)
    logger.info("MODEL PREDICTION TESTING")
    logger.info("="*80)
    logger.info("")
    
    # Load models
    xgb_model, rf_model, feature_names = load_models()
    
    # Test on multiple symbols
    symbols = ['RELIANCE', 'TCS', 'HDFCBANK']
    start_date = '2024-01-01'
    end_date = '2026-04-08'
    
    all_results = []
    
    for symbol in symbols:
        logger.info(f"\n{'='*80}")
        logger.info(f"TESTING ON {symbol}")
        logger.info(f"{'='*80}")
        
        # Load data
        df = load_test_data(symbol, start_date, end_date)
        
        if len(df) < 100:
            logger.warning(f"Insufficient data for {symbol}")
            continue
        
        # Create features
        df_features = create_features(df, feature_names)
        
        if len(df_features) < 50:
            logger.warning(f"Insufficient features for {symbol}")
            continue
        
        # Test predictions
        results = test_model_predictions(xgb_model, rf_model, feature_names, df_features)
        results['symbol'] = symbol
        all_results.append(results)
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("SUMMARY")
    logger.info(f"{'='*80}")
    
    if all_results:
        avg_xgb = np.mean([r['xgb_acc'] for r in all_results])
        avg_rf = np.mean([r['rf_acc'] for r in all_results])
        avg_ensemble = np.mean([r['ensemble_acc'] for r in all_results])
        
        logger.info(f"\nAverage Accuracies:")
        logger.info(f"  XGBoost:      {avg_xgb:.1%}")
        logger.info(f"  Random Forest: {avg_rf:.1%}")
        logger.info(f"  Ensemble:     {avg_ensemble:.1%}")
        
        logger.info(f"\n{'='*80}")
        logger.info("DIAGNOSIS")
        logger.info(f"{'='*80}")
        
        if avg_ensemble < 0.55:
            logger.warning("⚠️  Models have low accuracy (<55%)")
            logger.info("\nPossible reasons:")
            logger.info("1. Insufficient training data")
            logger.info("2. Features not predictive enough")
            logger.info("3. Market is too noisy for 5-day predictions")
            logger.info("\nRecommendations:")
            logger.info("1. Collect more training data (you have 6 months)")
            logger.info("2. Try shorter prediction horizons (1-3 days)")
            logger.info("3. Add more features (sentiment, volume patterns)")
            logger.info("4. Use ensemble with technical signals")
        elif avg_ensemble < 0.65:
            logger.info("✅ Models have moderate accuracy (55-65%)")
            logger.info("\nThis is acceptable for trading when combined with:")
            logger.info("1. Proper risk management")
            logger.info("2. Technical signal confirmation")
            logger.info("3. Position sizing based on confidence")
        else:
            logger.info("🎉 Models have good accuracy (>65%)")
            logger.info("\nReady for live trading with proper risk management!")
    
    logger.info(f"\n{'='*80}")


if __name__ == '__main__':
    main()
