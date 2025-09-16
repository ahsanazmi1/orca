"""
XGBoost Inference Module for Orca Core

This module provides XGBoost model inference with fallback to stub
if model artifacts are missing.
"""

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .features import FeatureExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XGBoostInference:
    """XGBoost model inference with fallback capabilities."""

    def __init__(self, model_dir: str = "models"):
        """Initialize inference engine."""
        self.model_dir = Path(model_dir)
        self.model: Any | None = None
        self.calibrator: Any | None = None
        self.scaler: Any | None = None
        self.metadata: dict[str, Any] | None = None
        self.feature_names: list[str] | None = None
        self.feature_extractor = FeatureExtractor()
        self.is_loaded = False

        # Try to load model
        self._load_model()

    def _load_model(self) -> bool:
        """Load XGBoost model and artifacts."""
        try:
            # Check if all required files exist
            model_path = self.model_dir / "xgb_model.joblib"
            calibrator_path = self.model_dir / "calibrator.joblib"
            scaler_path = self.model_dir / "scaler.joblib"
            metadata_path = self.model_dir / "metadata.json"

            if not all(
                [
                    model_path.exists(),
                    calibrator_path.exists(),
                    scaler_path.exists(),
                    metadata_path.exists(),
                ]
            ):
                logger.warning("XGBoost model artifacts not found, will use stub")
                return False

            # Load model artifacts
            self.model = joblib.load(model_path)
            self.calibrator = joblib.load(calibrator_path)
            self.scaler = joblib.load(scaler_path)

            # Load metadata
            with open(metadata_path) as f:
                self.metadata = json.load(f)

            self.feature_names = self.metadata.get("feature_names", []) if self.metadata else []
            self.is_loaded = True

            logger.info("✅ XGBoost model loaded successfully")
            logger.info(
                f"📊 Model version: {self.metadata.get('version', 'unknown') if self.metadata else 'unknown'}"
            )
            logger.info(f"📊 Features: {len(self.feature_names)}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to load XGBoost model: {e}")
            self.is_loaded = False
            return False

    def predict_risk(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """
        Predict risk using XGBoost model with fallback to stub.

        Args:
            request_data: Transaction request data

        Returns:
            Risk prediction dictionary
        """
        if not self.is_loaded:
            logger.warning("XGBoost model not available, using stub")
            return self._fallback_to_stub(request_data)

        try:
            # Extract features
            features = self.feature_extractor.extract_features(request_data)

            # Convert to feature vector
            feature_vector = self._features_to_vector(features)

            # Scale features
            if self.scaler is None:
                raise ValueError("Scaler not loaded")
            feature_vector_scaled = self.scaler.transform(feature_vector.reshape(1, -1))

            # Predict risk score
            if self.calibrator is None:
                raise ValueError("Calibrator not loaded")
            risk_score = self.calibrator.predict_proba(feature_vector_scaled)[0, 1]

            # Generate reason codes based on feature importance
            reason_codes = self._generate_reason_codes(features, risk_score)

            return {
                "risk_score": float(risk_score),
                "reason_codes": reason_codes,
                "version": self.metadata.get("version", "1.0.0") if self.metadata else "1.0.0",
                "model_type": "xgboost",
                "feature_contributions": self._get_feature_contributions(features, risk_score),
            }

        except Exception as e:
            logger.error(f"❌ XGBoost prediction failed: {e}")
            return self._fallback_to_stub(request_data)

    def _features_to_vector(self, features: dict[str, float]) -> np.ndarray:
        """Convert features dictionary to numpy array in correct order."""
        if not self.feature_names:
            raise ValueError("Feature names not loaded")

        return np.array([features.get(name, 0.0) for name in self.feature_names])

    def _generate_reason_codes(self, features: dict[str, float], risk_score: float) -> list[str]:
        """Generate reason codes based on feature values and importance."""
        reason_codes = []

        # Get feature importance from metadata
        feature_importance: dict[str, float] = (
            self.metadata.get("training_metrics", {}).get("feature_importance", {})
            if self.metadata
            else {}
        )

        # Define thresholds for different risk factors
        thresholds = {
            "amount": 500.0,
            "velocity_24h": 3.0,
            "cross_border": 0.5,
            "location_mismatch": 0.5,
            "payment_method_risk": 0.4,
            "chargebacks_12m": 0.5,
        }

        # Check each feature against thresholds
        for feature_name, threshold in thresholds.items():
            if feature_name in features and features[feature_name] > threshold:
                # Only include if feature has significant importance
                importance = feature_importance.get(feature_name, 0.0)
                if importance > 0.01:  # 1% importance threshold
                    reason_codes.append(feature_name.upper())

        # Add risk level reason code
        if risk_score > 0.8:
            reason_codes.append("HIGH_RISK")
        elif risk_score > 0.6:
            reason_codes.append("MEDIUM_RISK")
        elif risk_score > 0.4:
            reason_codes.append("ELEVATED_RISK")
        else:
            reason_codes.append("LOW_RISK")

        # Ensure at least one reason code
        if not reason_codes:
            reason_codes.append("BASELINE")

        return reason_codes

    def _get_feature_contributions(
        self, features: dict[str, float], risk_score: float
    ) -> dict[str, float]:
        """Get feature contributions to the risk score."""
        contributions = {}

        # Get feature importance
        feature_importance: dict[str, float] = (
            self.metadata.get("training_metrics", {}).get("feature_importance", {})
            if self.metadata
            else {}
        )

        # Calculate contributions (simplified)
        for feature_name, importance in feature_importance.items():
            if feature_name in features:
                # Weight the feature value by its importance
                contribution = features[feature_name] * importance * risk_score
                contributions[feature_name] = float(contribution)

        # Sort by contribution
        return dict(sorted(contributions.items(), key=lambda x: x[1], reverse=True))

    def _fallback_to_stub(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Fallback to stub model if XGBoost is not available."""
        logger.info("🔄 Falling back to stub model")

        # Extract features for stub
        features = self.feature_extractor.extract_features(request_data)

        # Use stub model logic directly (avoid circular import)
        risk_score = 0.35
        reason_codes = []

        # Extract features with defaults
        amount = features.get("amount", 0.0)
        velocity_24h = features.get("velocity_24h", 0.0)
        cross_border = features.get("cross_border", 0.0)

        # Apply scoring rules
        if amount > 500:
            risk_score += 0.2
            reason_codes.append("DUMMY_MCC")

        if velocity_24h > 2:
            risk_score += 0.1
            reason_codes.append("VELOCITY")

        if cross_border > 0:
            risk_score += 0.1
            reason_codes.append("CROSS_BORDER")

        # Clamp to [0, 1] range
        risk_score = max(0.0, min(1.0, risk_score))

        # If no specific reason codes, add default
        if not reason_codes:
            reason_codes.append("BASELINE")

        return {
            "risk_score": risk_score,
            "reason_codes": reason_codes,
            "version": "stub-0.1.0",
            "model_type": "stub",
        }

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        if not self.is_loaded:
            return {
                "model_type": "stub",
                "version": "stub-0.1.0",
                "status": "not_loaded",
                "message": "XGBoost model not available, using stub",
            }

        return {
            "model_type": "xgboost",
            "version": self.metadata.get("version", "1.0.0") if self.metadata else "1.0.0",
            "status": "loaded",
            "features": len(self.feature_names) if self.feature_names else 0,
            "training_date": (
                self.metadata.get("training_metrics", {}).get("training_date")
                if self.metadata
                else None
            ),
            "auc_score": (
                self.metadata.get("training_metrics", {}).get("auc_score")
                if self.metadata
                else None
            ),
            "feature_names": (
                self.feature_names[:10] if self.feature_names else []
            ),  # First 10 features
        }

    def reload_model(self) -> bool:
        """Reload the model from disk."""
        logger.info("🔄 Reloading XGBoost model...")
        return self._load_model()


# Global inference instance
_xgb_inference = None


def get_xgb_inference() -> XGBoostInference:
    """Get global XGBoost inference instance."""
    global _xgb_inference
    if _xgb_inference is None:
        _xgb_inference = XGBoostInference()
    return _xgb_inference


def predict_risk_xgb(request_data: dict[str, Any]) -> dict[str, Any]:
    """Predict risk using XGBoost model with fallback."""
    inference = get_xgb_inference()
    return inference.predict_risk(request_data)


def get_xgb_model_info() -> dict[str, Any]:
    """Get XGBoost model information."""
    inference = get_xgb_inference()
    return inference.get_model_info()
