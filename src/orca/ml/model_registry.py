"""Model Registry for Orca Core ML Models.

This module provides model loading, versioning, and artifact management
for XGBoost models with calibration and feature specifications.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import xgboost as xgb


class ModelRegistry:
    """Registry for managing ML model artifacts and versions."""

    def __init__(self, model_dir: str = "models/xgb"):
        """Initialize model registry.

        Args:
            model_dir: Directory containing model artifacts
        """
        self.model_dir = Path(model_dir)
        self.model: xgb.Booster | None = None
        self.calibrator: Any | None = None
        self.scaler: Any | None = None
        self.feature_spec: dict[str, Any] | None = None
        self.metadata: dict[str, Any] | None = None
        self.is_loaded = False

        # Set deterministic random states
        self._set_deterministic_seeds()

    def _set_deterministic_seeds(self) -> None:
        """Set deterministic random seeds for reproducibility."""
        # Set XGBoost random state
        os.environ["XGBOOST_RANDOM_STATE"] = "42"

        # Set numpy random seed
        np.random.seed(42)

        # Set Python hash seed for deterministic behavior
        os.environ["PYTHONHASHSEED"] = "0"

    def load_model(self, version: str | None = None) -> bool:
        """Load XGBoost model and artifacts from disk.

        Args:
            version: Specific model version to load (default: latest)

        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Determine model version
            if version is None:
                version = self._get_latest_version()

            if version is None:
                print("⚠️ No model versions found")
                return False

            model_path = self.model_dir / version

            # Check required artifacts
            required_files = ["model.json", "calibrator.pkl", "feature_spec.json"]

            for file_name in required_files:
                if not (model_path / file_name).exists():
                    print(f"❌ Missing required artifact: {file_name}")
                    return False

            # Load model
            self.model = xgb.Booster()
            self.model.load_model(str(model_path / "model.json"))

            # Load calibrator
            self.calibrator = joblib.load(model_path / "calibrator.pkl")

            # Load feature specification
            with open(model_path / "feature_spec.json") as f:
                self.feature_spec = json.load(f)

            # Load metadata if available
            metadata_path = model_path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {"version": version}

            # Load scaler if available
            scaler_path = model_path / "scaler.pkl"
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)

            self.is_loaded = True

            print(f"✅ Model {version} loaded successfully")
            if self.feature_spec:
                print(f"📊 Features: {len(self.feature_spec.get('feature_names', []))}")
            else:
                print("📊 Features: 0")
            print(f"📊 Model SHA256: {self._get_model_hash()}")

            return True

        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            self.is_loaded = False
            return False

    def _get_latest_version(self) -> str | None:
        """Get the latest model version."""
        if not self.model_dir.exists():
            return None

        versions = []
        for item in self.model_dir.iterdir():
            if item.is_dir() and (item / "model.json").exists():
                versions.append(item.name)

        if not versions:
            return None

        # Sort versions (assuming semantic versioning)
        versions.sort(reverse=True)
        return versions[0]

    def _get_model_hash(self) -> str:
        """Get SHA256 hash of the model file."""
        if not self.model or not self.metadata:
            return "unknown"

        version = self.metadata.get("version", "unknown")
        model_path = self.model_dir / version / "model.json"

        if not model_path.exists():
            return "unknown"

        with open(model_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]

    def predict_risk(self, features: dict[str, float], enable_shap: bool = False) -> dict[str, Any]:
        """Predict risk score with calibration and feature analysis.

        Args:
            features: Feature dictionary from AP2 contract
            enable_shap: Whether to compute SHAP values

        Returns:
            Dictionary containing:
                - risk_score: Calibrated risk score (0-1)
                - key_signals: Top contributing features mapped to AP2 paths
                - model_meta: Model metadata including version and thresholds
                - shap_values: SHAP values if enabled
        """
        if not self.is_loaded:
            raise ValueError("Model not loaded. Call load_model() first.")

        # Convert features to model input
        feature_vector = self._features_to_vector(features)

        # Store raw features for calibration
        raw_feature_vector = feature_vector.copy()

        # Apply scaling if available
        if self.scaler is not None:
            # Convert to DataFrame with feature names for proper scaling
            import pandas as pd

            feature_names = self.feature_spec.get("feature_names", []) if self.feature_spec else []
            if feature_names:
                feature_df = pd.DataFrame(feature_vector.reshape(1, -1), columns=feature_names)
                feature_vector = self.scaler.transform(feature_df)
            else:
                feature_vector = self.scaler.transform(feature_vector.reshape(1, -1))

        # Get raw prediction (use scaled features for XGBoost)
        if self.model is not None:
            dmatrix = xgb.DMatrix(feature_vector)
            raw_score = self.model.predict(dmatrix)[0]
        else:
            raw_score = 0.5  # Default fallback

        # Apply calibration (use raw features, not scaled)
        if self.calibrator is not None:
            calibrated_score = self.calibrator.predict_proba(raw_feature_vector.reshape(1, -1))[
                0, 1
            ]
        else:
            calibrated_score = raw_score  # Fallback to raw score

        # Get key signals (top contributing features)
        key_signals = self._get_key_signals(features, calibrated_score)

        # Compute SHAP values if enabled (use original unscaled features)
        shap_values = None
        if enable_shap and os.getenv("ORCA_ENABLE_SHAP", "false").lower() == "true":
            # Use original unscaled features for SHAP
            original_features = self._features_to_vector(features)
            shap_values = self._compute_shap_values(original_features)

        return {
            "risk_score": float(calibrated_score),
            "key_signals": key_signals,
            "model_meta": {
                "model_version": (
                    self.metadata.get("version", "unknown") if self.metadata else "unknown"
                ),
                "model_sha256": self._get_model_hash(),
                "trained_on": (
                    self.metadata.get("trained_on", "unknown") if self.metadata else "unknown"
                ),
                "thresholds": self.metadata.get("thresholds", {}) if self.metadata else {},
                "feature_count": (
                    len(self.feature_spec.get("feature_names", [])) if self.feature_spec else 0
                ),
            },
            "shap_values": shap_values,
        }

    def _features_to_vector(self, features: dict[str, float]) -> np.ndarray:
        """Convert features dictionary to numpy array in correct order.

        Args:
            features: Feature dictionary

        Returns:
            Feature vector in the order expected by the model
        """
        if not self.feature_spec:
            raise ValueError("Feature specification not loaded")

        feature_names = self.feature_spec.get("feature_names", [])
        if not feature_names:
            raise ValueError("Feature specification not loaded")

        # Check for feature drift
        self._check_feature_drift(features, feature_names)

        # Create feature vector in correct order
        feature_vector = []
        for feature_name in feature_names:
            if feature_name in features:
                feature_vector.append(float(features[feature_name]))
            else:
                # Use default value from feature spec
                defaults = self.feature_spec.get("defaults", {})
                default_value = defaults.get(feature_name, 0.0)
                feature_vector.append(float(default_value))

        return np.array(feature_vector)

    def _check_feature_drift(
        self, features: dict[str, float], expected_features: list[str]
    ) -> None:
        """Check for feature drift and fail if detected.

        Args:
            features: Input features
            expected_features: Expected feature names from model

        Raises:
            ValueError: If feature drift is detected
        """
        # Check if all expected features are present
        missing_features = set(expected_features) - set(features.keys())
        if missing_features:
            raise ValueError(
                f"Feature drift detected: missing features {missing_features}. "
                f"Model version {self.metadata.get('version', 'unknown') if self.metadata else 'unknown'} expects "
                f"{len(expected_features)} features but got {len(features)}. "
                "Please retrain model or update feature extraction."
            )

        # Check for unexpected features (warn only)
        unexpected_features = set(features.keys()) - set(expected_features)
        if unexpected_features:
            print(f"⚠️ Warning: unexpected features {unexpected_features} will be ignored")

    def _get_key_signals(
        self, features: dict[str, float], risk_score: float
    ) -> list[dict[str, Any]]:
        """Get key contributing features mapped to AP2 paths.

        Args:
            features: Input features
            risk_score: Predicted risk score

        Returns:
            List of key signals with AP2 path mappings
        """
        # Get feature importance from metadata
        feature_importance = self.metadata.get("feature_importance", {}) if self.metadata else {}

        # Map features to AP2 paths
        ap2_mappings = self.feature_spec.get("ap2_mappings", {}) if self.feature_spec else {}

        # Calculate contributions
        contributions = []
        for feature_name, value in features.items():
            if feature_name in feature_importance:
                importance = feature_importance[feature_name]
                contribution = value * importance * risk_score

                # Get AP2 path mapping
                ap2_path = ap2_mappings.get(feature_name, f"feature.{feature_name}")

                contributions.append(
                    {
                        "feature_name": feature_name,
                        "ap2_path": ap2_path,
                        "value": float(value),
                        "importance": float(importance),
                        "contribution": float(contribution),
                    }
                )

        # Sort by contribution and return top 5
        contributions.sort(key=lambda x: x["contribution"], reverse=True)
        return contributions[:5]

    def _compute_shap_values(self, feature_vector: np.ndarray) -> dict[str, Any] | None:
        """Compute SHAP values for feature explanation.

        Args:
            feature_vector: Input feature vector

        Returns:
            SHAP values dictionary or None if SHAP not available
        """
        try:
            import shap

            # Create SHAP explainer
            explainer = shap.TreeExplainer(self.model)

            # Compute SHAP values (ensure 2D input)
            if feature_vector.ndim == 1:
                feature_vector = feature_vector.reshape(1, -1)
            shap_values = explainer.shap_values(feature_vector)

            # Map to feature names
            if self.feature_spec:
                feature_names = self.feature_spec.get("feature_names", [])
                ap2_mappings = self.feature_spec.get("ap2_mappings", {})
            else:
                feature_names = []
                ap2_mappings = {}

            shap_explanations = []
            for feature_name, shap_value in zip(feature_names, shap_values[0], strict=False):
                ap2_path = ap2_mappings.get(feature_name, f"feature.{feature_name}")
                shap_explanations.append(
                    {
                        "feature_name": feature_name,
                        "ap2_path": ap2_path,
                        "shap_value": float(shap_value),
                    }
                )

            # Sort by absolute SHAP value
            shap_explanations.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

            return {
                "explanations": shap_explanations[:10],  # Top 10 features
                "base_value": float(explainer.expected_value),
            }

        except ImportError:
            print("⚠️ SHAP not available. Install with: pip install shap")
            return None
        except Exception as e:
            print(f"⚠️ SHAP computation failed: {e}")
            return None

    def get_model_info(self) -> dict[str, Any]:
        """Get comprehensive model information.

        Returns:
            Model information dictionary
        """
        if not self.is_loaded:
            return {
                "status": "not_loaded",
                "message": "No model loaded",
            }

        return {
            "status": "loaded",
            "model_version": (
                self.metadata.get("version", "unknown") if self.metadata else "unknown"
            ),
            "model_sha256": self._get_model_hash(),
            "trained_on": (
                self.metadata.get("trained_on", "unknown") if self.metadata else "unknown"
            ),
            "feature_count": (
                len(self.feature_spec.get("feature_names", [])) if self.feature_spec else 0
            ),
            "has_scaler": self.scaler is not None,
            "has_calibrator": self.calibrator is not None,
            "thresholds": self.metadata.get("thresholds", {}) if self.metadata else {},
            "feature_names": (
                self.feature_spec.get("feature_names", [])[:10] if self.feature_spec else []
            ),  # First 10
        }

    def list_versions(self) -> list[str]:
        """List available model versions.

        Returns:
            List of available model versions
        """
        if not self.model_dir.exists():
            return []

        versions = []
        for item in self.model_dir.iterdir():
            if item.is_dir() and (item / "model.json").exists():
                versions.append(item.name)

        return sorted(versions, reverse=True)


# Global model registry instance
_model_registry: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    """Get global model registry instance."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry


def load_model(version: str | None = None) -> bool:
    """Load model using global registry.

    Args:
        version: Model version to load (default: latest)

    Returns:
        True if model loaded successfully
    """
    registry = get_model_registry()
    return registry.load_model(version)


def predict_risk(features: dict[str, float], enable_shap: bool = False) -> dict[str, Any]:
    """Predict risk using loaded model.

    Args:
        features: Feature dictionary
        enable_shap: Whether to compute SHAP values

    Returns:
        Risk prediction results
    """
    registry = get_model_registry()
    if not registry.is_loaded:
        raise ValueError("Model not loaded. Call load_model() first.")

    return registry.predict_risk(features, enable_shap)


def get_model_info() -> dict[str, Any]:
    """Get model information."""
    registry = get_model_registry()
    return registry.get_model_info()
