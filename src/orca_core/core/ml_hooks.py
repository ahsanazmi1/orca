"""ML hooks for Orca Core decision engine."""

from ..ml.stub_model import get_features_used, get_model_version
from ..ml.stub_model import predict_risk as stub_predict_risk


def predict_risk(features: dict[str, float]) -> float:
    """
    Predict risk score based on features.

    Args:
        features: Dictionary of feature values

    Returns:
        Risk score between 0.0 and 1.0 (0.0 = low risk, 1.0 = high risk)
    """
    return stub_predict_risk(features)


def get_ml_metadata() -> tuple[str, list[str]]:
    """
    Get ML model metadata.

    Returns:
        Tuple of (model_version, features_used)
    """
    return get_model_version(), get_features_used()
