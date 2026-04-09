"""
ml/drift_detection.py — Model drift detection using PSI (Population Stability Index).

Detects feature drift and prediction drift to identify when models need retraining.
PSI < 0.1: No significant change
PSI 0.1-0.2: Moderate change (monitor)
PSI > 0.2: Significant change (action required - pause model)
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from data.db import get_session


class DriftDetector:
    """Detect feature and prediction drift using PSI"""
    
    def __init__(
        self,
        threshold: float = 0.2,
        moderate_threshold: float = 0.1,
        bins: int = 10
    ):
        """
        Args:
            threshold: PSI threshold for significant drift (default 0.2)
            moderate_threshold: PSI threshold for moderate drift (default 0.1)
            bins: Number of bins for PSI calculation (default 10)
        """
        self.threshold = threshold
        self.moderate_threshold = moderate_threshold
        self.bins = bins
        self.baseline_distributions = {}
    
    def calculate_psi(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
        bins: Optional[int] = None
    ) -> float:
        """
        Calculate Population Stability Index (PSI)
        
        PSI measures the shift in distribution between two datasets.
        
        Args:
            baseline: Reference distribution (training data)
            current: Current distribution (production data)
            bins: Number of bins (uses self.bins if not provided)
        
        Returns:
            PSI score (float)
        """
        if bins is None:
            bins = self.bins
        
        # Remove NaN values
        baseline = baseline[~np.isnan(baseline)]
        current = current[~np.isnan(current)]
        
        if len(baseline) == 0 or len(current) == 0:
            logger.warning("Empty arrays provided to PSI calculation")
            return 0.0
        
        # Create bins based on baseline percentiles
        breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))
        breakpoints = np.unique(breakpoints)
        
        # Handle case where all values are the same
        if len(breakpoints) <= 1:
            return 0.0
        
        # Calculate distributions
        baseline_dist = np.histogram(baseline, bins=breakpoints)[0] / len(baseline)
        current_dist = np.histogram(current, bins=breakpoints)[0] / len(current)
        
        # Avoid division by zero and log(0)
        baseline_dist = np.where(baseline_dist == 0, 0.0001, baseline_dist)
        current_dist = np.where(current_dist == 0, 0.0001, current_dist)
        
        # Calculate PSI
        psi = np.sum((current_dist - baseline_dist) * np.log(current_dist / baseline_dist))
        
        return float(psi)
    
    def set_baseline(
        self,
        baseline_features: pd.DataFrame,
        name: str = "default"
    ) -> None:
        """
        Set baseline distributions for features
        
        Args:
            baseline_features: DataFrame with feature columns
            name: Name for this baseline (e.g., "model_v1")
        """
        self.baseline_distributions[name] = {}
        
        for col in baseline_features.columns:
            if baseline_features[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
                self.baseline_distributions[name][col] = baseline_features[col].values
        
        logger.info(f"Baseline set for {len(self.baseline_distributions[name])} features (name={name})")
    
    def detect_feature_drift(
        self,
        current_features: pd.DataFrame,
        baseline_name: str = "default"
    ) -> Dict[str, float]:
        """
        Detect drift in features compared to baseline
        
        Args:
            current_features: Current feature DataFrame
            baseline_name: Name of baseline to compare against
        
        Returns:
            Dictionary of {feature_name: psi_score}
        """
        if baseline_name not in self.baseline_distributions:
            logger.error(f"Baseline '{baseline_name}' not found. Call set_baseline() first.")
            return {}
        
        baseline = self.baseline_distributions[baseline_name]
        drift_scores = {}
        
        for col in current_features.columns:
            if col in baseline:
                psi = self.calculate_psi(
                    baseline[col],
                    current_features[col].values
                )
                drift_scores[col] = psi
                
                # Log based on severity
                if psi > self.threshold:
                    logger.warning(f"🚨 SIGNIFICANT drift detected: {col} (PSI={psi:.3f})")
                elif psi > self.moderate_threshold:
                    logger.info(f"⚠️  Moderate drift detected: {col} (PSI={psi:.3f})")
        
        return drift_scores
    
    def detect_prediction_drift(
        self,
        baseline_predictions: np.ndarray,
        current_predictions: np.ndarray
    ) -> float:
        """
        Detect drift in model predictions
        
        Args:
            baseline_predictions: Predictions from training/validation
            current_predictions: Current production predictions
        
        Returns:
            PSI score for predictions
        """
        psi = self.calculate_psi(baseline_predictions, current_predictions)
        
        if psi > self.threshold:
            logger.warning(f"🚨 SIGNIFICANT prediction drift detected (PSI={psi:.3f})")
        elif psi > self.moderate_threshold:
            logger.info(f"⚠️  Moderate prediction drift detected (PSI={psi:.3f})")
        
        return psi
    
    def should_pause_model(
        self,
        drift_scores: Dict[str, float],
        max_drifted_features: int = 3
    ) -> Tuple[bool, str]:
        """
        Determine if model should be paused due to drift
        
        Args:
            drift_scores: Dictionary of {feature_name: psi_score}
            max_drifted_features: Maximum number of features allowed to have significant drift
        
        Returns:
            (should_pause: bool, reason: str)
        """
        # Count features with significant drift
        significant_drifts = [
            (name, score) for name, score in drift_scores.items()
            if score > self.threshold
        ]
        
        if len(significant_drifts) > max_drifted_features:
            reason = f"{len(significant_drifts)} features with significant drift (threshold={max_drifted_features})"
            logger.critical(f"🛑 MODEL PAUSED: {reason}")
            logger.critical(f"Drifted features: {[name for name, _ in significant_drifts[:5]]}")
            return True, reason
        
        return False, ""
    
    async def log_drift_to_db(
        self,
        symbol: str,
        model_version: str,
        drift_scores: Dict[str, float],
        prediction_drift: Optional[float] = None,
        paused: bool = False
    ) -> None:
        """
        Log drift detection results to database
        
        Args:
            symbol: Symbol being monitored
            model_version: Version of the model
            drift_scores: Feature drift scores
            prediction_drift: Prediction drift score (optional)
            paused: Whether model was paused
        """
        async with get_session() as session:
            # Log overall drift event
            await session.execute(
                text("""
                    INSERT INTO model_drift_log (
                        timestamp, symbol, model_version,
                        num_features_drifted, max_drift_score,
                        prediction_drift, model_paused
                    ) VALUES (
                        NOW(), :symbol, :model_version,
                        :num_drifted, :max_drift,
                        :pred_drift, :paused
                    )
                """),
                {
                    "symbol": symbol,
                    "model_version": model_version,
                    "num_drifted": sum(1 for s in drift_scores.values() if s > self.threshold),
                    "max_drift": max(drift_scores.values()) if drift_scores else 0.0,
                    "pred_drift": prediction_drift,
                    "paused": paused
                }
            )
            
            # Log individual feature drifts
            for feature, score in drift_scores.items():
                if score > self.moderate_threshold:  # Only log moderate+ drift
                    await session.execute(
                        text("""
                            INSERT INTO feature_drift_log (
                                timestamp, symbol, model_version,
                                feature_name, psi_score, severity
                            ) VALUES (
                                NOW(), :symbol, :model_version,
                                :feature, :psi, :severity
                            )
                        """),
                        {
                            "symbol": symbol,
                            "model_version": model_version,
                            "feature": feature,
                            "psi": score,
                            "severity": "CRITICAL" if score > self.threshold else "WARNING"
                        }
                    )
            
            await session.commit()
        
        logger.info(f"Drift logged to database for {symbol} (model={model_version})")


class DriftMonitor:
    """
    Continuous drift monitoring service
    
    Monitors features and predictions in production and triggers alerts
    """
    
    def __init__(
        self,
        detector: DriftDetector,
        check_interval_hours: int = 24
    ):
        """
        Args:
            detector: DriftDetector instance
            check_interval_hours: How often to check for drift
        """
        self.detector = detector
        self.check_interval_hours = check_interval_hours
        self.model_status = {}  # {model_version: {"paused": bool, "reason": str}}
    
    async def check_drift(
        self,
        symbol: str,
        model_version: str,
        current_features: pd.DataFrame,
        current_predictions: Optional[np.ndarray] = None,
        baseline_predictions: Optional[np.ndarray] = None
    ) -> Dict:
        """
        Check for drift and update model status
        
        Returns:
            {
                "drift_detected": bool,
                "feature_drift": Dict[str, float],
                "prediction_drift": float,
                "should_pause": bool,
                "reason": str
            }
        """
        # Detect feature drift
        drift_scores = self.detector.detect_feature_drift(
            current_features,
            baseline_name=model_version
        )
        
        # Detect prediction drift if provided
        prediction_drift = None
        if current_predictions is not None and baseline_predictions is not None:
            prediction_drift = self.detector.detect_prediction_drift(
                baseline_predictions,
                current_predictions
            )
        
        # Determine if model should be paused
        should_pause, reason = self.detector.should_pause_model(drift_scores)
        
        # Update model status
        if should_pause:
            self.model_status[model_version] = {
                "paused": True,
                "reason": reason,
                "paused_at": datetime.now()
            }
        
        # Log to database
        await self.detector.log_drift_to_db(
            symbol=symbol,
            model_version=model_version,
            drift_scores=drift_scores,
            prediction_drift=prediction_drift,
            paused=should_pause
        )
        
        return {
            "drift_detected": len([s for s in drift_scores.values() if s > self.detector.moderate_threshold]) > 0,
            "feature_drift": drift_scores,
            "prediction_drift": prediction_drift,
            "should_pause": should_pause,
            "reason": reason
        }
    
    def is_model_paused(self, model_version: str) -> bool:
        """Check if a model is currently paused"""
        return self.model_status.get(model_version, {}).get("paused", False)
    
    def unpause_model(self, model_version: str) -> None:
        """Manually unpause a model (e.g., after retraining)"""
        if model_version in self.model_status:
            self.model_status[model_version]["paused"] = False
            logger.info(f"Model {model_version} unpaused")
