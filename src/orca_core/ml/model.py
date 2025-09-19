"""
ML Model Dispatcher for Orca Core Phase 2

This module provides a dispatcher that chooses between real XGBoost model
and deterministic ML stub based on configuration.
"""

import os
from typing import Any

# Import the new real ML system
try:
    from src.orca.ml.model_registry import get_model_registry
    from src.orca.ml.predict_risk import predict_risk as predict_risk_real

    REAL_ML_AVAILABLE = True
except ImportError:
    REAL_ML_AVAILABLE = False

from .xgb_infer import get_xgb_model_info


def predict_risk(features: dict[str, float]) -> dict[str, Any]:
    """
    Predict risk score using model dispatcher.

    This function dispatches to either real XGBoost model or deterministic stub
    based on the ORCA_USE_XGB environment variable.

    Args:
        features: Dictionary of feature values

    Returns:
        Dictionary containing:
            - risk_score: Float between 0.0 and 1.0
            - reason_codes: List of reason codes that contributed to the score
            - version: Model version identifier
            - model_type: Type of model used ("xgboost" or "stub")
    """
    # Check if real ML system should be used
    use_real_ml = os.getenv("ORCA_USE_XGB", "false").lower() == "true"

    if use_real_ml and REAL_ML_AVAILABLE:
        try:
            # Ensure model is loaded
            registry = get_model_registry()
            if not registry.is_loaded:
                registry.load_model()

            # Use real XGBoost model with calibration
            result = predict_risk_real(features)

            # Convert to legacy format for compatibility
            return {
                "risk_score": result["risk_score"],
                "reason_codes": [
                    signal["feature_name"].upper() for signal in result["key_signals"][:3]
                ],
                "version": result["version"],
                "model_type": result["model_type"],
                "key_signals": result["key_signals"],
                "model_meta": result["model_meta"],
            }
        except Exception as e:
            import traceback

            print(f"⚠️ Real ML model failed, falling back to stub: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return predict_risk_stub(features)
    else:
        # Use deterministic stub
        return predict_risk_stub(features)


def predict_risk_stub(features: dict[str, float]) -> dict[str, Any]:
    """
    Predict risk score using deterministic stub logic.

    This is a Phase 2 stub implementation that provides deterministic
    risk scoring based on simple business rules.

    Scoring Logic:
    - Base score: 0.35
    - +0.2 if amount > 500
    - +0.1 if velocity_24h > 2
    - +0.1 if cross_border (location mismatch)
    - Clamp to [0, 1]

    Args:
        features: Dictionary of feature values including:
            - amount: Transaction amount
            - velocity_24h: 24-hour transaction velocity
            - cross_border: Boolean flag for cross-border transactions
            - Other features (ignored in stub)

    Returns:
        Dictionary containing:
            - risk_score: Float between 0.0 and 1.0
            - reason_codes: List of reason codes that contributed to the score
            - version: Model version identifier
            - model_type: "stub"
    """
    # Initialize base score
    risk_score = 0.35
    reason_codes: list[str] = []

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


def get_model_info() -> dict[str, Any]:
    """
    Get information about the current model.

    Returns:
        Dictionary with model metadata
    """
    use_xgb = os.getenv("ORCA_USE_XGB", "false").lower() == "true"

    if use_xgb:
        # Get XGBoost model info
        return get_xgb_model_info()
    else:
        # Return stub model info
        return {
            "name": "Orca Risk Prediction Stub",
            "version": "stub-0.1.0",
            "type": "deterministic",
            "description": "Phase 2 stub implementation with deterministic scoring",
            "features": ["amount", "velocity_24h", "cross_border"],
            "model_type": "stub",
            "status": "active",
        }
