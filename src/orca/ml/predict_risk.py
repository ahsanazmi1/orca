"""Real ML Risk Prediction for Orca Core.

This module provides real XGBoost-based risk prediction with calibration,
SHAP support, and AP2 feature mapping, replacing the stub implementation.
"""

import os
from typing import Any, Optional

from .model_registry import get_model_registry, load_model


def predict_risk(features: dict[str, float]) -> dict[str, Any]:
    """
    Predict risk score using real XGBoost model with calibration.

    This function loads and uses a real XGBoost model with calibration
    to predict risk scores, replacing the previous stub implementation.

    Args:
        features: Dictionary of feature values extracted from AP2 contract

    Returns:
        Dictionary containing:
            - risk_score: Calibrated risk score (0.0-1.0)
            - key_signals: Top contributing features mapped to AP2 paths
            - model_meta: Model metadata including version and thresholds
            - shap_values: SHAP explanations if enabled
            - version: Model version identifier
            - model_type: "xgboost" (real model)
    """
    # Get model registry
    registry = get_model_registry()

    # Load model if not already loaded
    if not registry.is_loaded:
        success = load_model()
        if not success:
            # Fallback to stub if model loading fails
            return _fallback_to_stub(features)

    try:
        # Check if SHAP is enabled
        enable_shap = os.getenv("ORCA_ENABLE_SHAP", "false").lower() == "true"

        # Predict using real model
        result = registry.predict_risk(features, enable_shap=enable_shap)

        # Add version and model type for compatibility
        result["version"] = result["model_meta"]["model_version"]
        result["model_type"] = "xgboost"

        return result

    except Exception as e:
        print(f"⚠️ Real model prediction failed: {e}")
        return _fallback_to_stub(features)


def _fallback_to_stub(features: dict[str, float]) -> dict[str, Any]:
    """
    Fallback to deterministic stub logic if real model fails.

    This maintains backward compatibility and provides deterministic
    results when the real model is not available.

    Args:
        features: Dictionary of feature values

    Returns:
        Stub prediction results
    """
    # Initialize base score
    risk_score = 0.35
    reason_codes = []

    # Extract features with defaults
    amount = features.get("amount", 0.0)
    velocity_24h = features.get("velocity_24h", 0.0)
    cross_border = features.get("cross_border", 0.0)

    # Apply scoring rules
    if amount > 500:
        risk_score += 0.2
        reason_codes.append("HIGH_AMOUNT")

    if velocity_24h > 2:
        risk_score += 0.1
        reason_codes.append("HIGH_VELOCITY")

    if cross_border > 0:
        risk_score += 0.1
        reason_codes.append("CROSS_BORDER")

    # Clamp to [0, 1] range
    risk_score = max(0.0, min(1.0, risk_score))

    # If no specific reason codes, add default
    if not reason_codes:
        reason_codes.append("BASELINE")

    # Create key signals for stub
    key_signals = []
    if amount > 500:
        key_signals.append(
            {
                "feature_name": "amount",
                "ap2_path": "cart.amount",
                "value": float(amount),
                "importance": 0.8,
                "contribution": 0.2,
            }
        )

    if velocity_24h > 2:
        key_signals.append(
            {
                "feature_name": "velocity_24h",
                "ap2_path": "velocity.24h",
                "value": float(velocity_24h),
                "importance": 0.6,
                "contribution": 0.1,
            }
        )

    if cross_border > 0:
        key_signals.append(
            {
                "feature_name": "cross_border",
                "ap2_path": "cart.geo.cross_border",
                "value": float(cross_border),
                "importance": 0.5,
                "contribution": 0.1,
            }
        )

    return {
        "risk_score": risk_score,
        "key_signals": key_signals,
        "model_meta": {
            "model_version": "stub-0.1.0",
            "model_sha256": "stub",
            "trained_on": "deterministic",
            "thresholds": {
                "amount": 500.0,
                "velocity_24h": 2.0,
                "cross_border": 0.5,
            },
            "feature_count": len(features),
        },
        "shap_values": None,
        "version": "stub-0.1.0",
        "model_type": "stub",
    }


def get_model_info() -> dict[str, Any]:
    """Get information about the loaded model.

    Returns:
        Model information dictionary
    """
    registry = get_model_registry()
    return registry.get_model_info()


def load_model_version(version: str) -> bool:
    """Load a specific model version.

    Args:
        version: Model version to load

    Returns:
        True if model loaded successfully
    """
    return load_model(version)


def list_available_models() -> list[str]:
    """List available model versions.

    Returns:
        List of available model versions
    """
    registry = get_model_registry()
    return registry.list_versions()


def is_model_loaded() -> bool:
    """Check if a model is currently loaded.

    Returns:
        True if model is loaded
    """
    registry = get_model_registry()
    return registry.is_loaded


def get_feature_spec() -> Optional[dict[str, Any]]:
    """Get the feature specification for the loaded model.

    Returns:
        Feature specification dictionary or None if not loaded
    """
    registry = get_model_registry()
    if registry.is_loaded:
        return registry.feature_spec
    return None


def predict_with_shap(features: dict[str, float]) -> dict[str, Any]:
    """Predict risk with SHAP explanations enabled.

    Args:
        features: Dictionary of feature values

    Returns:
        Risk prediction results with SHAP values
    """
    # Temporarily enable SHAP
    original_shap_setting = os.environ.get("ORCA_ENABLE_SHAP", "false")
    os.environ["ORCA_ENABLE_SHAP"] = "true"

    try:
        result = predict_risk(features)
        return result
    finally:
        # Restore original setting
        os.environ["ORCA_ENABLE_SHAP"] = original_shap_setting
