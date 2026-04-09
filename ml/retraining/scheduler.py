"""
ml/retraining/scheduler.py — Automated model retraining scheduler.

Handles scheduled retraining (weekly incremental, monthly full) and
trigger-based retraining (drift detection, performance degradation).
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import mlflow

from ml.training_pipeline import train_all_models
from ml.drift_detection import DriftDetector
from ml.monitoring.performance_monitor import PerformanceMonitor


class RetrainingScheduler:
    """
    Automated model retraining scheduler.
    
    Features:
    - Weekly incremental retraining (adds last week's data)
    - Monthly full retraining (retrains on full dataset)
    - Trigger-based retraining (drift, performance degradation)
    - Model versioning with semantic versioning
    - Rollback capability (keeps last N versions)
    """
    
    def __init__(
        self,
        scheduler: Optional[BackgroundScheduler] = None,
        max_versions: int = 5,
        drift_threshold: float = 0.2,
        performance_threshold: float = 0.10,  # 10% degradation
    ):
        """
        Initialize retraining scheduler.
        
        Args:
            scheduler: APScheduler instance (creates new if None)
            max_versions: Maximum number of model versions to keep
            drift_threshold: PSI threshold to trigger retraining
            performance_threshold: Performance drop threshold (0.10 = 10%)
        """
        self.scheduler = scheduler or BackgroundScheduler()
        self.max_versions = max_versions
        self.drift_threshold = drift_threshold
        self.performance_threshold = performance_threshold
        
        self.drift_detector = DriftDetector()
        self.performance_monitor = PerformanceMonitor()
        
        # Track retraining history
        self.retraining_history: List[Dict] = []
        
        logger.info(
            f"[RetrainingScheduler] Initialized with max_versions={max_versions}, "
            f"drift_threshold={drift_threshold}, performance_threshold={performance_threshold}"
        )
    
    def start(self):
        """Start the scheduler with configured jobs."""
        # Weekly incremental retraining (every Monday at 2 AM)
        self.scheduler.add_job(
            func=self.incremental_retrain,
            trigger=CronTrigger(day_of_week='mon', hour=2, minute=0),
            id='weekly_incremental_retrain',
            name='Weekly Incremental Retraining',
            replace_existing=True,
        )
        
        # Monthly full retraining (1st of month at 3 AM)
        self.scheduler.add_job(
            func=self.full_retrain,
            trigger=CronTrigger(day=1, hour=3, minute=0),
            id='monthly_full_retrain',
            name='Monthly Full Retraining',
            replace_existing=True,
        )
        
        # Check for drift/performance triggers (every 6 hours)
        self.scheduler.add_job(
            func=self.check_triggers,
            trigger=CronTrigger(hour='*/6'),
            id='check_retraining_triggers',
            name='Check Retraining Triggers',
            replace_existing=True,
        )
        
        self.scheduler.start()
        logger.info("[RetrainingScheduler] Scheduler started with 3 jobs")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("[RetrainingScheduler] Scheduler stopped")
    
    def incremental_retrain(self, manual: bool = False):
        """
        Perform incremental retraining with last week's data.
        
        Args:
            manual: Whether this is a manual trigger
        """
        logger.info("[RetrainingScheduler] Starting incremental retraining...")
        
        try:
            # Get last week's data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Train models with incremental data
            results = train_all_models(
                start_date=start_date,
                end_date=end_date,
                incremental=True,
            )
            
            # Version the models
            version = self._get_next_version(patch=True)
            self._save_models_with_version(results, version)
            
            # Record retraining
            self._record_retraining(
                retrain_type='incremental',
                version=version,
                trigger='manual' if manual else 'scheduled',
                results=results,
            )
            
            logger.info(
                f"[RetrainingScheduler] Incremental retraining complete: v{version}"
            )
            
            return version
        
        except Exception as e:
            logger.error(f"[RetrainingScheduler] Incremental retraining failed: {e}")
            raise
    
    def full_retrain(self, manual: bool = False):
        """
        Perform full retraining on entire dataset.
        
        Args:
            manual: Whether this is a manual trigger
        """
        logger.info("[RetrainingScheduler] Starting full retraining...")
        
        try:
            # Train models on full dataset
            results = train_all_models(
                start_date=None,  # Use all available data
                end_date=None,
                incremental=False,
            )
            
            # Version the models (minor version bump)
            version = self._get_next_version(minor=True)
            self._save_models_with_version(results, version)
            
            # Record retraining
            self._record_retraining(
                retrain_type='full',
                version=version,
                trigger='manual' if manual else 'scheduled',
                results=results,
            )
            
            # Cleanup old versions
            self._cleanup_old_versions()
            
            logger.info(
                f"[RetrainingScheduler] Full retraining complete: v{version}"
            )
            
            return version
        
        except Exception as e:
            logger.error(f"[RetrainingScheduler] Full retraining failed: {e}")
            raise
    
    def check_triggers(self):
        """Check for drift and performance triggers."""
        logger.debug("[RetrainingScheduler] Checking retraining triggers...")
        
        try:
            # Check drift
            drift_detected = self._check_drift_trigger()
            
            # Check performance degradation
            performance_degraded = self._check_performance_trigger()
            
            if drift_detected:
                logger.warning(
                    "[RetrainingScheduler] Drift detected, triggering full retraining"
                )
                self.full_retrain(manual=False)
            
            elif performance_degraded:
                logger.warning(
                    "[RetrainingScheduler] Performance degradation detected, "
                    "triggering incremental retraining"
                )
                self.incremental_retrain(manual=False)
            
            else:
                logger.debug("[RetrainingScheduler] No triggers detected")
        
        except Exception as e:
            logger.error(f"[RetrainingScheduler] Error checking triggers: {e}")
    
    def _check_drift_trigger(self) -> bool:
        """Check if drift exceeds threshold."""
        try:
            # Get recent drift metrics
            drift_metrics = self.drift_detector.get_recent_drift(days=7)
            
            if not drift_metrics:
                return False
            
            # Check if any feature has significant drift
            significant_drift_count = sum(
                1 for metric in drift_metrics
                if metric.get('psi', 0) > self.drift_threshold
            )
            
            # Trigger if >3 features have significant drift
            return significant_drift_count > 3
        
        except Exception as e:
            logger.error(f"[RetrainingScheduler] Error checking drift: {e}")
            return False
    
    def _check_performance_trigger(self) -> bool:
        """Check if performance has degraded."""
        try:
            # Get recent performance metrics
            recent_perf = self.performance_monitor.get_rolling_metrics(days=7)
            baseline_perf = self.performance_monitor.get_rolling_metrics(days=30)
            
            if not recent_perf or not baseline_perf:
                return False
            
            # Check if accuracy dropped by more than threshold
            recent_acc = recent_perf.get('accuracy', 0)
            baseline_acc = baseline_perf.get('accuracy', 0)
            
            if baseline_acc == 0:
                return False
            
            degradation = (baseline_acc - recent_acc) / baseline_acc
            
            return degradation > self.performance_threshold
        
        except Exception as e:
            logger.error(f"[RetrainingScheduler] Error checking performance: {e}")
            return False
    
    def _get_next_version(
        self,
        major: bool = False,
        minor: bool = False,
        patch: bool = False
    ) -> str:
        """
        Get next semantic version.
        
        Args:
            major: Bump major version (breaking changes)
            minor: Bump minor version (new features)
            patch: Bump patch version (bug fixes, incremental)
        
        Returns:
            Version string (e.g., "1.2.3")
        """
        # Get current version from MLflow
        current_version = self._get_current_version()
        
        if current_version == "0.0.0":
            return "1.0.0"
        
        parts = [int(x) for x in current_version.split('.')]
        
        if major:
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif minor:
            parts[1] += 1
            parts[2] = 0
        elif patch:
            parts[2] += 1
        
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    
    def _get_current_version(self) -> str:
        """Get current production model version."""
        try:
            # Get latest version from MLflow
            client = mlflow.tracking.MlflowClient()
            
            # Try to get production model
            try:
                model_versions = client.get_latest_versions(
                    name="ensemble_model",
                    stages=["Production"]
                )
                
                if model_versions:
                    version = model_versions[0].tags.get('version', '0.0.0')
                    return version
            except:
                pass
            
            # Fallback: get latest version
            try:
                model_versions = client.get_latest_versions(
                    name="ensemble_model",
                    stages=["None"]
                )
                
                if model_versions:
                    version = model_versions[0].tags.get('version', '0.0.0')
                    return version
            except:
                pass
            
            return "0.0.0"
        
        except Exception as e:
            logger.warning(f"[RetrainingScheduler] Error getting current version: {e}")
            return "0.0.0"
    
    def _save_models_with_version(self, results: Dict, version: str):
        """Save models with version tag in MLflow."""
        try:
            with mlflow.start_run(run_name=f"retrain_v{version}"):
                # Log version
                mlflow.set_tag("version", version)
                mlflow.set_tag("retrain_date", datetime.now().isoformat())
                
                # Log metrics
                for model_name, metrics in results.items():
                    for metric_name, value in metrics.items():
                        mlflow.log_metric(f"{model_name}_{metric_name}", value)
                
                logger.info(f"[RetrainingScheduler] Models saved with version {version}")
        
        except Exception as e:
            logger.error(f"[RetrainingScheduler] Error saving models: {e}")
            raise
    
    def _record_retraining(
        self,
        retrain_type: str,
        version: str,
        trigger: str,
        results: Dict,
    ):
        """Record retraining event in history."""
        record = {
            'timestamp': datetime.now().isoformat(),
            'type': retrain_type,
            'version': version,
            'trigger': trigger,
            'results': results,
        }
        
        self.retraining_history.append(record)
        
        # Save to file
        history_file = Path('.ml_metadata/retraining_history.json')
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump(self.retraining_history, f, indent=2)
        
        logger.info(f"[RetrainingScheduler] Retraining recorded: {retrain_type} v{version}")
    
    def _cleanup_old_versions(self):
        """Remove old model versions, keeping only last N."""
        try:
            client = mlflow.tracking.MlflowClient()
            
            # Get all versions
            all_versions = client.search_model_versions(
                filter_string="name='ensemble_model'"
            )
            
            # Sort by version number
            sorted_versions = sorted(
                all_versions,
                key=lambda v: v.tags.get('version', '0.0.0'),
                reverse=True
            )
            
            # Keep only last N versions
            if len(sorted_versions) > self.max_versions:
                for version in sorted_versions[self.max_versions:]:
                    client.delete_model_version(
                        name="ensemble_model",
                        version=version.version
                    )
                    logger.info(
                        f"[RetrainingScheduler] Deleted old version: {version.version}"
                    )
        
        except Exception as e:
            logger.warning(f"[RetrainingScheduler] Error cleaning up versions: {e}")
    
    def rollback(self, version: Optional[str] = None) -> str:
        """
        Rollback to a previous model version.
        
        Args:
            version: Version to rollback to (None = previous version)
        
        Returns:
            Version that was rolled back to
        """
        try:
            client = mlflow.tracking.MlflowClient()
            
            if version is None:
                # Get previous version
                all_versions = client.search_model_versions(
                    filter_string="name='ensemble_model'"
                )
                
                sorted_versions = sorted(
                    all_versions,
                    key=lambda v: v.tags.get('version', '0.0.0'),
                    reverse=True
                )
                
                if len(sorted_versions) < 2:
                    raise ValueError("No previous version available for rollback")
                
                version = sorted_versions[1].tags.get('version')
            
            # Set version as production
            model_versions = client.search_model_versions(
                filter_string=f"name='ensemble_model' and tags.version='{version}'"
            )
            
            if not model_versions:
                raise ValueError(f"Version {version} not found")
            
            client.transition_model_version_stage(
                name="ensemble_model",
                version=model_versions[0].version,
                stage="Production"
            )
            
            logger.info(f"[RetrainingScheduler] Rolled back to version {version}")
            
            return version
        
        except Exception as e:
            logger.error(f"[RetrainingScheduler] Rollback failed: {e}")
            raise
    
    def get_retraining_history(self, limit: int = 10) -> List[Dict]:
        """Get recent retraining history."""
        return self.retraining_history[-limit:]
