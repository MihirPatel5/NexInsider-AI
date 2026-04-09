"""
ml/holdout_validator.py — Final validation on holdout dataset.
Provides unbiased performance estimates before production deployment.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
from loguru import logger

from ml.data_split import DataSplitter


class HoldoutValidator:
    """
    Validates model performance on holdout dataset.
    
    Key principles:
    1. Holdout set is only used once for final validation
    2. No hyperparameter tuning based on holdout results
    3. Results are logged and cannot be modified
    4. Minimum performance thresholds enforced
    """
    
    def __init__(
        self,
        min_accuracy: float = 0.55,
        min_precision: float = 0.50,
        min_recall: float = 0.50,
        results_path: str = ".ml_metadata/holdout_results.json"
    ):
        """
        Initialize holdout validator.
        
        Args:
            min_accuracy: Minimum acceptable accuracy
            min_precision: Minimum acceptable precision
            min_recall: Minimum acceptable recall
            results_path: Path to store validation results
        """
        self.min_accuracy = min_accuracy
        self.min_precision = min_precision
        self.min_recall = min_recall
        self.results_path = Path(results_path)
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_results()
    
    def _load_results(self):
        """Load previous validation results if they exist."""
        if self.results_path.exists():
            with open(self.results_path, 'r') as f:
                self.results = json.load(f)
        else:
            self.results = {
                "validations": []
            }
    
    def _save_results(self):
        """Save validation results."""
        with open(self.results_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
    
    def validate(
        self,
        model: Any,
        holdout_features: pd.DataFrame,
        holdout_labels: pd.Series,
        model_name: str = "ensemble",
        model_version: str = "v1"
    ) -> Dict[str, Any]:
        """
        Validate model on holdout dataset.
        
        Args:
            model: Trained model with predict() method
            holdout_features: Holdout feature DataFrame
            holdout_labels: Holdout labels (0=SELL, 1=HOLD, 2=BUY)
            model_name: Name of the model
            model_version: Version of the model
        
        Returns:
            Dict with validation results and pass/fail status
        """
        logger.info(f"🔍 Starting holdout validation for {model_name} {model_version}")
        logger.info(f"   Holdout samples: {len(holdout_features)}")
        
        # Make predictions
        predictions = model.predict(holdout_features)
        
        # Calculate metrics
        accuracy = accuracy_score(holdout_labels, predictions)
        precision = precision_score(holdout_labels, predictions, average='weighted', zero_division=0)
        recall = recall_score(holdout_labels, predictions, average='weighted', zero_division=0)
        f1 = f1_score(holdout_labels, predictions, average='weighted', zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(holdout_labels, predictions)
        
        # Per-class metrics
        class_report = classification_report(
            holdout_labels,
            predictions,
            target_names=['SELL', 'HOLD', 'BUY'],
            output_dict=True,
            zero_division=0
        )
        
        # Check if passes minimum thresholds
        passes_accuracy = accuracy >= self.min_accuracy
        passes_precision = precision >= self.min_precision
        passes_recall = recall >= self.min_recall
        passes_all = passes_accuracy and passes_precision and passes_recall
        
        # Create results dict
        result = {
            "model_name": model_name,
            "model_version": model_version,
            "timestamp": datetime.now().isoformat(),
            "holdout_samples": len(holdout_features),
            "metrics": {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1)
            },
            "confusion_matrix": cm.tolist(),
            "per_class_metrics": {
                "SELL": {
                    "precision": float(class_report['SELL']['precision']),
                    "recall": float(class_report['SELL']['recall']),
                    "f1_score": float(class_report['SELL']['f1-score']),
                    "support": int(class_report['SELL']['support'])
                },
                "HOLD": {
                    "precision": float(class_report['HOLD']['precision']),
                    "recall": float(class_report['HOLD']['recall']),
                    "f1_score": float(class_report['HOLD']['f1-score']),
                    "support": int(class_report['HOLD']['support'])
                },
                "BUY": {
                    "precision": float(class_report['BUY']['precision']),
                    "recall": float(class_report['BUY']['recall']),
                    "f1_score": float(class_report['BUY']['f1-score']),
                    "support": int(class_report['BUY']['support'])
                }
            },
            "thresholds": {
                "min_accuracy": self.min_accuracy,
                "min_precision": self.min_precision,
                "min_recall": self.min_recall
            },
            "passes": {
                "accuracy": passes_accuracy,
                "precision": passes_precision,
                "recall": passes_recall,
                "all": passes_all
            }
        }
        
        # Save results
        self.results["validations"].append(result)
        self._save_results()
        
        # Log results
        self._log_results(result)
        
        return result
    
    def _log_results(self, result: Dict[str, Any]):
        """Log validation results in a readable format."""
        logger.info("=" * 60)
        logger.info(f"📊 HOLDOUT VALIDATION RESULTS")
        logger.info("=" * 60)
        logger.info(f"Model: {result['model_name']} {result['model_version']}")
        logger.info(f"Timestamp: {result['timestamp']}")
        logger.info(f"Samples: {result['holdout_samples']}")
        logger.info("")
        logger.info("Overall Metrics:")
        logger.info(f"  Accuracy:  {result['metrics']['accuracy']:.4f} (min: {result['thresholds']['min_accuracy']}) {'✅' if result['passes']['accuracy'] else '❌'}")
        logger.info(f"  Precision: {result['metrics']['precision']:.4f} (min: {result['thresholds']['min_precision']}) {'✅' if result['passes']['precision'] else '❌'}")
        logger.info(f"  Recall:    {result['metrics']['recall']:.4f} (min: {result['thresholds']['min_recall']}) {'✅' if result['passes']['recall'] else '❌'}")
        logger.info(f"  F1 Score:  {result['metrics']['f1_score']:.4f}")
        logger.info("")
        logger.info("Per-Class Metrics:")
        for class_name in ['SELL', 'HOLD', 'BUY']:
            metrics = result['per_class_metrics'][class_name]
            logger.info(f"  {class_name}:")
            logger.info(f"    Precision: {metrics['precision']:.4f}")
            logger.info(f"    Recall:    {metrics['recall']:.4f}")
            logger.info(f"    F1 Score:  {metrics['f1_score']:.4f}")
            logger.info(f"    Support:   {metrics['support']}")
        logger.info("")
        logger.info("Confusion Matrix:")
        logger.info("              Predicted")
        logger.info("           SELL  HOLD   BUY")
        cm = result['confusion_matrix']
        logger.info(f"  SELL  [{cm[0][0]:5d} {cm[0][1]:5d} {cm[0][2]:5d}]")
        logger.info(f"  HOLD  [{cm[1][0]:5d} {cm[1][1]:5d} {cm[1][2]:5d}]")
        logger.info(f"  BUY   [{cm[2][0]:5d} {cm[2][1]:5d} {cm[2][2]:5d}]")
        logger.info("")
        
        if result['passes']['all']:
            logger.info("✅ VALIDATION PASSED - Model meets all minimum thresholds")
        else:
            logger.warning("❌ VALIDATION FAILED - Model does not meet minimum thresholds")
            if not result['passes']['accuracy']:
                logger.warning(f"   Accuracy too low: {result['metrics']['accuracy']:.4f} < {result['thresholds']['min_accuracy']}")
            if not result['passes']['precision']:
                logger.warning(f"   Precision too low: {result['metrics']['precision']:.4f} < {result['thresholds']['min_precision']}")
            if not result['passes']['recall']:
                logger.warning(f"   Recall too low: {result['metrics']['recall']:.4f} < {result['thresholds']['min_recall']}")
        
        logger.info("=" * 60)
    
    def get_validation_history(self) -> List[Dict[str, Any]]:
        """Get all validation results."""
        return self.results["validations"]
    
    def get_latest_validation(self) -> Optional[Dict[str, Any]]:
        """Get the most recent validation result."""
        if self.results["validations"]:
            return self.results["validations"][-1]
        return None
    
    def has_passed_validation(self, model_name: str, model_version: str) -> bool:
        """
        Check if a specific model version has passed validation.
        
        Args:
            model_name: Name of the model
            model_version: Version of the model
        
        Returns:
            True if model has passed validation, False otherwise
        """
        for validation in self.results["validations"]:
            if (validation["model_name"] == model_name and 
                validation["model_version"] == model_version and
                validation["passes"]["all"]):
                return True
        return False


def validate_on_holdout(
    model: Any,
    df: pd.DataFrame,
    feature_cols: List[str],
    label_col: str = "label",
    time_column: str = "time",
    model_name: str = "ensemble",
    model_version: str = "v1",
    min_accuracy: float = 0.55
) -> Dict[str, Any]:
    """
    Convenience function to validate model on holdout set.
    
    Args:
        model: Trained model with predict() method
        df: Full DataFrame
        feature_cols: List of feature column names
        label_col: Name of label column
        time_column: Name of time column
        model_name: Name of the model
        model_version: Version of the model
        min_accuracy: Minimum acceptable accuracy
    
    Returns:
        Dict with validation results
    """
    # Get holdout set
    splitter = DataSplitter()
    holdout_df = splitter.get_holdout(df, time_column, reason="final_validation")
    
    # Prepare features and labels
    holdout_features = holdout_df[feature_cols]
    
    # Convert labels if needed
    if holdout_df[label_col].dtype == 'object':
        label_map = {"SELL": 0, "HOLD": 1, "BUY": 2}
        holdout_labels = holdout_df[label_col].map(label_map)
    else:
        holdout_labels = holdout_df[label_col]
    
    # Validate
    validator = HoldoutValidator(min_accuracy=min_accuracy)
    return validator.validate(
        model,
        holdout_features,
        holdout_labels,
        model_name,
        model_version
    )
