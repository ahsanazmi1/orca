"""ML hooks for Orca Core decision engine."""


def predict_risk(features: dict[str, float]) -> float:
    """
    Predict risk score based on features.

    Args:
        features: Dictionary of feature values

    Returns:
        Risk score between 0.0 and 1.0 (0.0 = low risk, 1.0 = high risk)
    """
    # TODO: Implement actual ML model prediction
    # For now, return a fixed value of 0.15, but allow override for testing
    if "risk_score" in features:
        return features["risk_score"]
    return 0.15
