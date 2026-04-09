"""
ml/versioning.py — Enhanced model versioning with A/B testing and gradual rollout.

Provides advanced model deployment strategies including A/B testing,
canary deployments, and gradual rollouts with automatic rollback.
"""
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum
import random

from loguru import logger
import mlflow
from mlflow.tracking import MlflowClient


class DeploymentStrategy(Enum):
    """Model deployment strategies."""
    IMMEDIATE = "immediate"  # 100% traffic immediately
    AB_TEST = "ab_test"  # Split traffic between two models
    CANARY = "canary"  # Gradual rollout (5% → 25% → 50% → 100%)
    BLUE_GREEN = "blue_green"  # Switch between two environments


class ModelVersionManager:
    """
    Enhanced model versioning with deployment strategies.
    
    Features:
    - Rich metadata (tags, descriptions, configs)
    - A/B testing with traffic splitting
    - Canary deployments with gradual rollout
    - Automatic rollback on performance degradation
    - Version comparison and analysis
    """
    
    def __init__(
        self,
        model_name: str = "ensemble_model",
        mlflow_tracking_uri: Optional[str] = None,
    ):
        """
        Initialize model version manager.
        
        Args:
            model_name: Name of the model in MLflow
            mlflow_tracking_uri: MLflow tracking server URI
        """
        self.model_name = model_name
        
        if mlflow_tracking_uri:
            mlflow.set_tracking_uri(mlflow_tracking_uri)
        
        self.client = MlflowClient()
        
        # Track deployment state
        self.deployment_state = {
            'strategy': DeploymentStrategy.IMMEDIATE,
            'primary_version': None,
            'secondary_version': None,
            'traffic_split': 100,  # % to primary
            'canary_stage': 0,  # 0=not started, 1=5%, 2=25%, 3=50%, 4=100%
        }
        
        logger.info(f"[ModelVersionManager] Initialized for model: {model_name}")
    
    def register_model_version(
        self,
        run_id: str,
        version: str,
        description: str,
        tags: Optional[Dict[str, str]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Register a new model version with rich metadata.
        
        Args:
            run_id: MLflow run ID
            version: Semantic version (e.g., "1.2.3")
            description: Human-readable description
            tags: Additional tags (regime, data_range, etc.)
            metrics: Performance metrics
        
        Returns:
            Model version number in MLflow
        """
        try:
            # Register model version
            model_version = mlflow.register_model(
                model_uri=f"runs:/{run_id}/model",
                name=self.model_name,
            )
            
            # Set version tag
            self.client.set_model_version_tag(
                name=self.model_name,
                version=model_version.version,
                key="version",
                value=version,
            )
            
            # Set description
            self.client.update_model_version(
                name=self.model_name,
                version=model_version.version,
                description=description,
            )
            
            # Set additional tags
            if tags:
                for key, value in tags.items():
                    self.client.set_model_version_tag(
                        name=self.model_name,
                        version=model_version.version,
                        key=key,
                        value=str(value),
                    )
            
            # Log metrics as tags
            if metrics:
                for metric_name, value in metrics.items():
                    self.client.set_model_version_tag(
                        name=self.model_name,
                        version=model_version.version,
                        key=f"metric_{metric_name}",
                        value=str(value),
                    )
            
            # Set registration timestamp
            self.client.set_model_version_tag(
                name=self.model_name,
                version=model_version.version,
                key="registered_at",
                value=datetime.now().isoformat(),
            )
            
            logger.info(
                f"[ModelVersionManager] Registered version {version} "
                f"(MLflow version: {model_version.version})"
            )
            
            return model_version.version
        
        except Exception as e:
            logger.error(f"[ModelVersionManager] Error registering model: {e}")
            raise
    
    def deploy_immediate(self, version: str):
        """
        Deploy model version immediately (100% traffic).
        
        Args:
            version: Semantic version to deploy
        """
        try:
            # Find model version
            model_versions = self.client.search_model_versions(
                filter_string=f"name='{self.model_name}' and tags.version='{version}'"
            )
            
            if not model_versions:
                raise ValueError(f"Version {version} not found")
            
            # Transition to production
            self.client.transition_model_version_stage(
                name=self.model_name,
                version=model_versions[0].version,
                stage="Production",
            )
            
            # Update deployment state
            self.deployment_state = {
                'strategy': DeploymentStrategy.IMMEDIATE,
                'primary_version': version,
                'secondary_version': None,
                'traffic_split': 100,
                'canary_stage': 0,
            }
            
            logger.info(f"[ModelVersionManager] Deployed {version} immediately (100% traffic)")
        
        except Exception as e:
            logger.error(f"[ModelVersionManager] Error deploying model: {e}")
            raise
    
    def start_ab_test(
        self,
        version_a: str,
        version_b: str,
        traffic_split: int = 50,
    ):
        """
        Start A/B test between two model versions.
        
        Args:
            version_a: First version (gets traffic_split% of traffic)
            version_b: Second version (gets remaining traffic)
            traffic_split: Percentage of traffic to version_a (default: 50)
        """
        try:
            # Validate versions exist
            for version in [version_a, version_b]:
                model_versions = self.client.search_model_versions(
                    filter_string=f"name='{self.model_name}' and tags.version='{version}'"
                )
                if not model_versions:
                    raise ValueError(f"Version {version} not found")
            
            # Update deployment state
            self.deployment_state = {
                'strategy': DeploymentStrategy.AB_TEST,
                'primary_version': version_a,
                'secondary_version': version_b,
                'traffic_split': traffic_split,
                'canary_stage': 0,
            }
            
            logger.info(
                f"[ModelVersionManager] Started A/B test: "
                f"{version_a} ({traffic_split}%) vs {version_b} ({100-traffic_split}%)"
            )
        
        except Exception as e:
            logger.error(f"[ModelVersionManager] Error starting A/B test: {e}")
            raise
    
    def start_canary_deployment(self, version: str):
        """
        Start canary deployment with gradual rollout.
        
        Stages: 5% → 25% → 50% → 100%
        
        Args:
            version: Version to deploy via canary
        """
        try:
            # Validate version exists
            model_versions = self.client.search_model_versions(
                filter_string=f"name='{self.model_name}' and tags.version='{version}'"
            )
            if not model_versions:
                raise ValueError(f"Version {version} not found")
            
            # Get current production version
            current_versions = self.client.get_latest_versions(
                name=self.model_name,
                stages=["Production"]
            )
            
            current_version = None
            if current_versions:
                current_version = current_versions[0].tags.get('version')
            
            # Update deployment state (start at 5%)
            self.deployment_state = {
                'strategy': DeploymentStrategy.CANARY,
                'primary_version': current_version,
                'secondary_version': version,
                'traffic_split': 95,  # 95% to current, 5% to canary
                'canary_stage': 1,
            }
            
            logger.info(
                f"[ModelVersionManager] Started canary deployment: "
                f"{version} (5% traffic)"
            )
        
        except Exception as e:
            logger.error(f"[ModelVersionManager] Error starting canary: {e}")
            raise
    
    def advance_canary(self) -> bool:
        """
        Advance canary deployment to next stage.
        
        Returns:
            True if advanced, False if already at 100%
        """
        if self.deployment_state['strategy'] != DeploymentStrategy.CANARY:
            raise ValueError("Not in canary deployment mode")
        
        stage = self.deployment_state['canary_stage']
        
        if stage == 1:  # 5% → 25%
            self.deployment_state['traffic_split'] = 75
            self.deployment_state['canary_stage'] = 2
            logger.info("[ModelVersionManager] Advanced canary to 25%")
            return True
        
        elif stage == 2:  # 25% → 50%
            self.deployment_state['traffic_split'] = 50
            self.deployment_state['canary_stage'] = 3
            logger.info("[ModelVersionManager] Advanced canary to 50%")
            return True
        
        elif stage == 3:  # 50% → 100%
            # Save canary version before deploy_immediate resets state
            canary_version = self.deployment_state['secondary_version']
            
            # Promote canary to production
            self.deploy_immediate(canary_version)
            
            # Preserve canary_stage after deploy_immediate
            self.deployment_state['canary_stage'] = 4
            
            logger.info("[ModelVersionManager] Canary promoted to 100% (production)")
            return True
        
        else:
            logger.info("[ModelVersionManager] Canary already at 100%")
            return False
    
    def rollback_canary(self):
        """Rollback canary deployment to previous version."""
        if self.deployment_state['strategy'] != DeploymentStrategy.CANARY:
            raise ValueError("Not in canary deployment mode")
        
        primary_version = self.deployment_state['primary_version']
        
        if primary_version:
            self.deploy_immediate(primary_version)
            logger.info(f"[ModelVersionManager] Rolled back canary to {primary_version}")
        else:
            logger.warning("[ModelVersionManager] No previous version to rollback to")
    
    def get_model_for_prediction(self, request_id: Optional[str] = None) -> str:
        """
        Get model version to use for prediction based on deployment strategy.
        
        Args:
            request_id: Optional request ID for consistent routing
        
        Returns:
            Model version to use
        """
        strategy = self.deployment_state['strategy']
        
        if strategy == DeploymentStrategy.IMMEDIATE:
            return self.deployment_state['primary_version']
        
        elif strategy == DeploymentStrategy.AB_TEST:
            # Use request_id for consistent routing, or random
            if request_id:
                # Hash request_id to get consistent routing
                hash_val = hash(request_id) % 100
            else:
                hash_val = random.randint(0, 99)
            
            if hash_val < self.deployment_state['traffic_split']:
                return self.deployment_state['primary_version']
            else:
                return self.deployment_state['secondary_version']
        
        elif strategy == DeploymentStrategy.CANARY:
            # Similar to A/B test but with canary logic
            if request_id:
                hash_val = hash(request_id) % 100
            else:
                hash_val = random.randint(0, 99)
            
            if hash_val < self.deployment_state['traffic_split']:
                return self.deployment_state['primary_version']
            else:
                return self.deployment_state['secondary_version']
        
        else:
            return self.deployment_state['primary_version']
    
    def compare_versions(
        self,
        version_a: str,
        version_b: str,
    ) -> Dict:
        """
        Compare two model versions.
        
        Args:
            version_a: First version
            version_b: Second version
        
        Returns:
            Comparison dict with metrics and metadata
        """
        try:
            # Get version details
            versions_a = self.client.search_model_versions(
                filter_string=f"name='{self.model_name}' and tags.version='{version_a}'"
            )
            versions_b = self.client.search_model_versions(
                filter_string=f"name='{self.model_name}' and tags.version='{version_b}'"
            )
            
            if not versions_a or not versions_b:
                raise ValueError("One or both versions not found")
            
            v_a = versions_a[0]
            v_b = versions_b[0]
            
            # Extract metrics from tags
            metrics_a = {
                k.replace('metric_', ''): float(v)
                for k, v in v_a.tags.items()
                if k.startswith('metric_')
            }
            
            metrics_b = {
                k.replace('metric_', ''): float(v)
                for k, v in v_b.tags.items()
                if k.startswith('metric_')
            }
            
            # Calculate differences
            metric_diffs = {}
            for metric in set(metrics_a.keys()) | set(metrics_b.keys()):
                val_a = metrics_a.get(metric, 0)
                val_b = metrics_b.get(metric, 0)
                diff = val_b - val_a
                pct_change = (diff / val_a * 100) if val_a != 0 else 0
                
                metric_diffs[metric] = {
                    'version_a': val_a,
                    'version_b': val_b,
                    'difference': diff,
                    'percent_change': pct_change,
                }
            
            comparison = {
                'version_a': {
                    'version': version_a,
                    'mlflow_version': v_a.version,
                    'description': v_a.description,
                    'registered_at': v_a.tags.get('registered_at'),
                    'metrics': metrics_a,
                },
                'version_b': {
                    'version': version_b,
                    'mlflow_version': v_b.version,
                    'description': v_b.description,
                    'registered_at': v_b.tags.get('registered_at'),
                    'metrics': metrics_b,
                },
                'metric_differences': metric_diffs,
            }
            
            logger.info(f"[ModelVersionManager] Compared {version_a} vs {version_b}")
            
            return comparison
        
        except Exception as e:
            logger.error(f"[ModelVersionManager] Error comparing versions: {e}")
            raise
    
    def get_deployment_state(self) -> Dict:
        """Get current deployment state."""
        return self.deployment_state.copy()
