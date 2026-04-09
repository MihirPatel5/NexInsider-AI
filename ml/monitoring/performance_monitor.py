"""
ml/monitoring/performance_monitor.py — Real-time model performance monitoring.
Tracks predictions, actual outcomes, and calculates rolling performance metrics.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

import numpy as np
import pandas as pd
from sqlalchemy import text
from loguru import logger

from data.db import get_session


class PerformanceMonitor:
    """
    Monitors model performance in production.
    
    Key features:
    1. Logs all predictions with features and confidence
    2. Tracks actual outcomes when available
    3. Calculates rolling performance metrics
    4. Detects performance degradation
    5. Sends alerts on significant degradation
    """
    
    def __init__(
        self,
        degradation_threshold: float = 0.10,  # 10% drop triggers alert
        rolling_window_days: int = 7,
        min_samples_for_metrics: int = 100
    ):
        """
        Initialize performance monitor.
        
        Args:
            degradation_threshold: Percentage drop that triggers alert (0.10 = 10%)
            rolling_window_days: Days to use for rolling metrics
            min_samples_for_metrics: Minimum samples needed to calculate metrics
        """
        self.degradation_threshold = degradation_threshold
        self.rolling_window_days = rolling_window_days
        self.min_samples_for_metrics = min_samples_for_metrics
        
        self._baseline_accuracy = None
    
    async def log_prediction(
        self,
        symbol: str,
        model_version: str,
        prediction: int,
        confidence: float,
        features: Dict[str, float],
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Log a model prediction.
        
        Args:
            symbol: Stock symbol
            model_version: Version of the model
            prediction: Predicted class (0=SELL, 1=HOLD, 2=BUY)
            confidence: Prediction confidence (0-1)
            features: Feature values used for prediction
            timestamp: Prediction timestamp (defaults to now)
        
        Returns:
            Prediction ID
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        async with get_session() as session:
            query = text("""
                INSERT INTO model_predictions 
                (timestamp, symbol, model_version, prediction, confidence, features)
                VALUES (:timestamp, :symbol, :model_version, :prediction, :confidence, :features)
                RETURNING id
            """)
            
            result = await session.execute(
                query,
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "model_version": model_version,
                    "prediction": prediction,
                    "confidence": confidence,
                    "features": json.dumps(features)
                }
            )
            
            await session.commit()
            prediction_id = result.scalar()
            
            logger.debug(f"Logged prediction {prediction_id} for {symbol}: {prediction} (confidence: {confidence:.4f})")
            
            return prediction_id
    
    async def update_actual_outcome(
        self,
        prediction_id: int,
        actual_outcome: int
    ):
        """
        Update a prediction with the actual outcome.
        
        Args:
            prediction_id: ID of the prediction
            actual_outcome: Actual class (0=SELL, 1=HOLD, 2=BUY)
        """
        async with get_session() as session:
            query = text("""
                UPDATE model_predictions
                SET actual_outcome = :actual_outcome
                WHERE id = :prediction_id
            """)
            
            await session.execute(
                query,
                {
                    "prediction_id": prediction_id,
                    "actual_outcome": actual_outcome
                }
            )
            
            await session.commit()
            
            logger.debug(f"Updated prediction {prediction_id} with actual outcome: {actual_outcome}")
    
    async def update_outcomes_by_symbol(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        actual_outcomes: List[int]
    ):
        """
        Batch update actual outcomes for a symbol in a time range.
        
        Args:
            symbol: Stock symbol
            start_time: Start of time range
            end_time: End of time range
            actual_outcomes: List of actual outcomes in chronological order
        """
        async with get_session() as session:
            # Get predictions in time range
            query = text("""
                SELECT id FROM model_predictions
                WHERE symbol = :symbol
                AND timestamp >= :start_time
                AND timestamp < :end_time
                AND actual_outcome IS NULL
                ORDER BY timestamp
            """)
            
            result = await session.execute(
                query,
                {
                    "symbol": symbol,
                    "start_time": start_time,
                    "end_time": end_time
                }
            )
            
            prediction_ids = [row[0] for row in result.fetchall()]
            
            # Update outcomes
            for pred_id, outcome in zip(prediction_ids, actual_outcomes):
                await self.update_actual_outcome(pred_id, outcome)
            
            logger.info(f"Updated {len(prediction_ids)} outcomes for {symbol}")
    
    async def calculate_rolling_metrics(
        self,
        model_version: str,
        window_days: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate rolling performance metrics.
        
        Args:
            model_version: Version of the model
            window_days: Days to look back (defaults to self.rolling_window_days)
        
        Returns:
            Dict with accuracy, precision, recall, f1_score
        """
        if window_days is None:
            window_days = self.rolling_window_days
        
        cutoff_time = datetime.now() - timedelta(days=window_days)
        
        async with get_session() as session:
            query = text("""
                SELECT prediction, actual_outcome
                FROM model_predictions
                WHERE model_version = :model_version
                AND timestamp >= :cutoff_time
                AND actual_outcome IS NOT NULL
            """)
            
            result = await session.execute(
                query,
                {
                    "model_version": model_version,
                    "cutoff_time": cutoff_time
                }
            )
            
            rows = result.fetchall()
            
            if len(rows) < self.min_samples_for_metrics:
                logger.warning(f"Not enough samples for metrics: {len(rows)} < {self.min_samples_for_metrics}")
                return {
                    "accuracy": None,
                    "precision": None,
                    "recall": None,
                    "f1_score": None,
                    "sample_count": len(rows)
                }
            
            predictions = np.array([row[0] for row in rows])
            actuals = np.array([row[1] for row in rows])
            
            # Calculate metrics
            accuracy = np.mean(predictions == actuals)
            
            # Per-class precision and recall
            precisions = []
            recalls = []
            
            for class_idx in range(3):  # 0=SELL, 1=HOLD, 2=BUY
                # Precision: of all predictions for this class, how many were correct?
                pred_mask = predictions == class_idx
                if pred_mask.sum() > 0:
                    precision = np.mean(actuals[pred_mask] == class_idx)
                    precisions.append(precision)
                
                # Recall: of all actual instances of this class, how many did we predict?
                actual_mask = actuals == class_idx
                if actual_mask.sum() > 0:
                    recall = np.mean(predictions[actual_mask] == class_idx)
                    recalls.append(recall)
            
            # Weighted average
            precision = np.mean(precisions) if precisions else 0.0
            recall = np.mean(recalls) if recalls else 0.0
            
            # F1 score
            if precision + recall > 0:
                f1_score = 2 * (precision * recall) / (precision + recall)
            else:
                f1_score = 0.0
            
            metrics = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1_score),
                "sample_count": len(rows)
            }
            
            logger.info(f"Rolling metrics ({window_days}d): accuracy={accuracy:.4f}, samples={len(rows)}")
            
            return metrics
    
    async def check_degradation(
        self,
        model_version: str,
        baseline_accuracy: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Check for performance degradation.
        
        Args:
            model_version: Version of the model
            baseline_accuracy: Expected baseline accuracy (from validation)
        
        Returns:
            Dict with degradation status and details
        """
        if baseline_accuracy is not None:
            self._baseline_accuracy = baseline_accuracy
        
        if self._baseline_accuracy is None:
            logger.warning("No baseline accuracy set, cannot check degradation")
            return {
                "degraded": False,
                "reason": "no_baseline",
                "current_accuracy": None,
                "baseline_accuracy": None,
                "drop_percentage": None
            }
        
        # Get current rolling metrics
        metrics = await self.calculate_rolling_metrics(model_version)
        
        if metrics["accuracy"] is None:
            return {
                "degraded": False,
                "reason": "insufficient_samples",
                "current_accuracy": None,
                "baseline_accuracy": self._baseline_accuracy,
                "drop_percentage": None,
                "sample_count": metrics["sample_count"]
            }
        
        current_accuracy = metrics["accuracy"]
        drop = self._baseline_accuracy - current_accuracy
        drop_percentage = drop / self._baseline_accuracy
        
        degraded = drop_percentage >= self.degradation_threshold
        
        result = {
            "degraded": degraded,
            "reason": "performance_drop" if degraded else "ok",
            "current_accuracy": current_accuracy,
            "baseline_accuracy": self._baseline_accuracy,
            "drop": float(drop),
            "drop_percentage": float(drop_percentage),
            "threshold": self.degradation_threshold,
            "sample_count": metrics["sample_count"]
        }
        
        if degraded:
            logger.warning(f"🚨 PERFORMANCE DEGRADATION DETECTED")
            logger.warning(f"   Baseline: {self._baseline_accuracy:.4f}")
            logger.warning(f"   Current:  {current_accuracy:.4f}")
            logger.warning(f"   Drop:     {drop:.4f} ({drop_percentage*100:.1f}%)")
        else:
            logger.info(f"✅ Performance OK: {current_accuracy:.4f} (baseline: {self._baseline_accuracy:.4f})")
        
        return result
    
    async def get_performance_summary(
        self,
        model_version: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.
        
        Args:
            model_version: Version of the model
            days: Days to look back
        
        Returns:
            Dict with performance summary
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        async with get_session() as session:
            # Total predictions
            query = text("""
                SELECT COUNT(*) FROM model_predictions
                WHERE model_version = :model_version
                AND timestamp >= :cutoff_time
            """)
            result = await session.execute(query, {"model_version": model_version, "cutoff_time": cutoff_time})
            total_predictions = result.scalar()
            
            # Predictions with outcomes
            query = text("""
                SELECT COUNT(*) FROM model_predictions
                WHERE model_version = :model_version
                AND timestamp >= :cutoff_time
                AND actual_outcome IS NOT NULL
            """)
            result = await session.execute(query, {"model_version": model_version, "cutoff_time": cutoff_time})
            predictions_with_outcomes = result.scalar()
            
            # Average confidence
            query = text("""
                SELECT AVG(confidence) FROM model_predictions
                WHERE model_version = :model_version
                AND timestamp >= :cutoff_time
            """)
            result = await session.execute(query, {"model_version": model_version, "cutoff_time": cutoff_time})
            avg_confidence = result.scalar()
            
            # Prediction distribution
            query = text("""
                SELECT prediction, COUNT(*) as count
                FROM model_predictions
                WHERE model_version = :model_version
                AND timestamp >= :cutoff_time
                GROUP BY prediction
                ORDER BY prediction
            """)
            result = await session.execute(query, {"model_version": model_version, "cutoff_time": cutoff_time})
            pred_dist = {row[0]: row[1] for row in result.fetchall()}
        
        # Get rolling metrics
        metrics = await self.calculate_rolling_metrics(model_version, window_days=days)
        
        summary = {
            "model_version": model_version,
            "period_days": days,
            "total_predictions": total_predictions,
            "predictions_with_outcomes": predictions_with_outcomes,
            "outcome_coverage": predictions_with_outcomes / total_predictions if total_predictions > 0 else 0,
            "average_confidence": float(avg_confidence) if avg_confidence else None,
            "prediction_distribution": {
                "SELL": pred_dist.get(0, 0),
                "HOLD": pred_dist.get(1, 0),
                "BUY": pred_dist.get(2, 0)
            },
            "metrics": metrics
        }
        
        return summary


async def log_model_prediction(
    symbol: str,
    model_version: str,
    prediction: int,
    confidence: float,
    features: Dict[str, float]
) -> int:
    """
    Convenience function to log a prediction.
    
    Args:
        symbol: Stock symbol
        model_version: Version of the model
        prediction: Predicted class (0=SELL, 1=HOLD, 2=BUY)
        confidence: Prediction confidence (0-1)
        features: Feature values
    
    Returns:
        Prediction ID
    """
    monitor = PerformanceMonitor()
    return await monitor.log_prediction(symbol, model_version, prediction, confidence, features)
