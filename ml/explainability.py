"""
ml/explainability.py — Model explainability with SHAP integration.

Provides feature importance and prediction explanations using SHAP
(SHapley Additive exPlanations) for model interpretability.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from loguru import logger

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("[Explainability] SHAP not installed. Install with: pip install shap")


class ModelExplainer:
    """
    Model explainability using SHAP values.
    
    Features:
    - Global feature importance
    - Per-prediction SHAP values
    - Human-readable explanations
    - Minimal performance overhead
    """
    
    def __init__(
        self,
        model,
        feature_names: List[str],
        background_data: Optional[np.ndarray] = None,
        max_background_samples: int = 100,
    ):
        """
        Initialize model explainer.
        
        Args:
            model: Trained model (must have predict_proba method)
            feature_names: List of feature names
            background_data: Background dataset for SHAP (optional)
            max_background_samples: Max samples for background (default: 100)
        """
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP not installed. Install with: pip install shap")
        
        self.model = model
        self.feature_names = feature_names
        self.max_background_samples = max_background_samples
        
        # Initialize SHAP explainer
        if background_data is not None:
            # Limit background data size for performance
            if len(background_data) > max_background_samples:
                indices = np.random.choice(
                    len(background_data),
                    max_background_samples,
                    replace=False
                )
                background_data = background_data[indices]
            
            self.background_data = background_data
        else:
            self.background_data = None
        
        # Create explainer (will be initialized on first use)
        self.explainer = None
        
        logger.info(
            f"[ModelExplainer] Initialized with {len(feature_names)} features"
        )
    
    def _get_explainer(self):
        """Get or create SHAP explainer (lazy initialization)."""
        if self.explainer is None:
            if self.background_data is not None:
                # Use KernelExplainer with background data
                self.explainer = shap.KernelExplainer(
                    self.model.predict_proba,
                    self.background_data
                )
            else:
                # Use TreeExplainer for tree-based models (faster)
                try:
                    self.explainer = shap.TreeExplainer(self.model)
                except Exception:
                    # Fallback to KernelExplainer
                    logger.warning(
                        "[ModelExplainer] TreeExplainer failed, using KernelExplainer"
                    )
                    # Create small background dataset
                    self.explainer = shap.KernelExplainer(
                        self.model.predict_proba,
                        np.zeros((10, len(self.feature_names)))
                    )
        
        return self.explainer
    
    def calculate_shap_values(
        self,
        X: np.ndarray,
        max_samples: Optional[int] = None,
    ) -> np.ndarray:
        """
        Calculate SHAP values for predictions.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            max_samples: Max samples to explain (for performance)
        
        Returns:
            SHAP values array (n_samples, n_features, n_classes)
        """
        try:
            explainer = self._get_explainer()
            
            # Limit samples for performance
            if max_samples and len(X) > max_samples:
                indices = np.random.choice(len(X), max_samples, replace=False)
                X_sample = X[indices]
            else:
                X_sample = X
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(X_sample)
            
            logger.info(
                f"[ModelExplainer] Calculated SHAP values for {len(X_sample)} samples"
            )
            
            return shap_values
        
        except Exception as e:
            logger.error(f"[ModelExplainer] Error calculating SHAP values: {e}")
            raise
    
    def get_feature_importance(
        self,
        X: np.ndarray,
        class_idx: int = 2,  # BUY class by default
    ) -> Dict[str, float]:
        """
        Get global feature importance using mean absolute SHAP values.
        
        Args:
            X: Feature matrix
            class_idx: Class index (0=SELL, 1=HOLD, 2=BUY)
        
        Returns:
            Dict mapping feature names to importance scores
        """
        try:
            shap_values = self.calculate_shap_values(X)
            
            # Handle different SHAP value formats
            if isinstance(shap_values, list):
                # Multi-class: list of arrays
                shap_class = shap_values[class_idx]
            else:
                # Single array
                shap_class = shap_values
            
            # Calculate mean absolute SHAP values
            importance = np.abs(shap_class).mean(axis=0)
            
            # Create feature importance dict
            feature_importance = {
                name: float(imp)
                for name, imp in zip(self.feature_names, importance)
            }
            
            # Sort by importance
            feature_importance = dict(
                sorted(
                    feature_importance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            )
            
            logger.info(
                f"[ModelExplainer] Calculated feature importance for class {class_idx}"
            )
            
            return feature_importance
        
        except Exception as e:
            logger.error(f"[ModelExplainer] Error calculating feature importance: {e}")
            raise
    
    def explain_prediction(
        self,
        X: np.ndarray,
        prediction: int,
        confidence: float,
        top_k: int = 5,
    ) -> Dict:
        """
        Generate human-readable explanation for a prediction.
        
        Args:
            X: Feature vector (1D array)
            prediction: Predicted class (0=SELL, 1=HOLD, 2=BUY)
            confidence: Prediction confidence
            top_k: Number of top features to include
        
        Returns:
            Explanation dict with SHAP values and text
        """
        try:
            # Ensure X is 2D
            if X.ndim == 1:
                X = X.reshape(1, -1)
            
            # Calculate SHAP values
            shap_values = self.calculate_shap_values(X)
            
            # Handle different formats
            if isinstance(shap_values, list):
                shap_pred = shap_values[prediction][0]
            else:
                shap_pred = shap_values[0]
            
            # Get top contributing features
            feature_contributions = [
                (name, float(shap_val), float(X[0, i]))
                for i, (name, shap_val) in enumerate(
                    zip(self.feature_names, shap_pred)
                )
            ]
            
            # Sort by absolute SHAP value
            feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
            top_features = feature_contributions[:top_k]
            
            # Generate text explanation
            class_names = {0: "SELL", 1: "HOLD", 2: "BUY"}
            explanation_text = self._generate_explanation_text(
                prediction=class_names[prediction],
                confidence=confidence,
                top_features=top_features,
            )
            
            explanation = {
                "prediction": class_names[prediction],
                "confidence": confidence,
                "top_features": [
                    {
                        "feature": name,
                        "shap_value": shap_val,
                        "feature_value": feat_val,
                        "contribution": "positive" if shap_val > 0 else "negative",
                    }
                    for name, shap_val, feat_val in top_features
                ],
                "explanation_text": explanation_text,
            }
            
            logger.info(
                f"[ModelExplainer] Generated explanation for {class_names[prediction]} prediction"
            )
            
            return explanation
        
        except Exception as e:
            logger.error(f"[ModelExplainer] Error explaining prediction: {e}")
            raise
    
    def _generate_explanation_text(
        self,
        prediction: str,
        confidence: float,
        top_features: List[Tuple[str, float, float]],
    ) -> str:
        """
        Generate human-readable explanation text.
        
        Args:
            prediction: Predicted class name
            confidence: Prediction confidence
            top_features: List of (feature_name, shap_value, feature_value)
        
        Returns:
            Explanation text
        """
        text = f"{prediction} signal (confidence: {confidence:.2%}) because:\n"
        
        for i, (name, shap_val, feat_val) in enumerate(top_features, 1):
            contribution = "supports" if shap_val > 0 else "opposes"
            text += f"  {i}. {name} = {feat_val:.4f} ({contribution} decision)\n"
        
        return text.strip()
    
    def get_explanation_summary(
        self,
        X: np.ndarray,
        predictions: np.ndarray,
        confidences: np.ndarray,
    ) -> pd.DataFrame:
        """
        Get explanation summary for multiple predictions.
        
        Args:
            X: Feature matrix
            predictions: Predicted classes
            confidences: Prediction confidences
        
        Returns:
            DataFrame with explanations
        """
        try:
            explanations = []
            
            for i in range(len(X)):
                exp = self.explain_prediction(
                    X[i],
                    predictions[i],
                    confidences[i],
                    top_k=3,  # Fewer features for summary
                )
                
                explanations.append({
                    "prediction": exp["prediction"],
                    "confidence": exp["confidence"],
                    "top_feature_1": exp["top_features"][0]["feature"],
                    "top_feature_2": exp["top_features"][1]["feature"],
                    "top_feature_3": exp["top_features"][2]["feature"],
                })
            
            df = pd.DataFrame(explanations)
            
            logger.info(
                f"[ModelExplainer] Generated explanation summary for {len(X)} predictions"
            )
            
            return df
        
        except Exception as e:
            logger.error(f"[ModelExplainer] Error generating explanation summary: {e}")
            raise
