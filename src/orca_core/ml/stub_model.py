"""Stub ML model for deterministic risk scoring."""

import hashlib

# Model version constant
MODEL_VERSION = "stub-0.1"


def predict_risk(features: dict[str, float]) -> float:
    """
    Predict risk score based on features using a deterministic stub model.

    This is a placeholder implementation that returns deterministic values
    based on feature combinations for testing and development purposes.

    Args:
        features: Dictionary of feature values

    Returns:
        Risk score between 0.0 and 1.0 (0.0 = low risk, 1.0 = high risk)
    """
    # Allow override for testing
    if "risk_score" in features:
        return float(features["risk_score"])

    # Extract key features with defaults
    cart_total = features.get("cart_total", 0.0)
    item_count = features.get("item_count", 1.0)
    velocity_24h = features.get("velocity_24h", 0.0)
    location_mismatch = features.get("location_mismatch", 0.0)

    # Deterministic scoring based on feature combinations
    base_score = 0.1  # Base risk score

    # Cart total risk (higher amounts = higher risk)
    if cart_total > 1000:
        base_score += 0.3
    elif cart_total > 500:
        base_score += 0.2
    elif cart_total > 100:
        base_score += 0.1

    # Item count risk (many items = higher risk)
    if item_count > 10:
        base_score += 0.2
    elif item_count > 5:
        base_score += 0.1

    # Velocity risk (high velocity = higher risk)
    if velocity_24h > 5:
        base_score += 0.3
    elif velocity_24h > 2:
        base_score += 0.2
    elif velocity_24h > 1:
        base_score += 0.1

    # Location mismatch risk
    if location_mismatch > 0:
        base_score += 0.2

    # Add some deterministic "randomness" based on feature hash
    feature_str = f"{cart_total}_{item_count}_{velocity_24h}_{location_mismatch}"
    feature_hash = int(
        hashlib.md5(feature_str.encode(), usedforsecurity=False).hexdigest()[:8], 16
    )  # nosec B324
    hash_factor = (feature_hash % 100) / 1000  # 0.000 to 0.099

    final_score = min(base_score + hash_factor, 1.0)

    return round(final_score, 3)


def get_model_version() -> str:
    """Get the current model version."""
    return MODEL_VERSION


def get_features_used() -> list[str]:
    """Get the list of features used by this model."""
    return ["cart_total", "item_count", "velocity_24h", "location_mismatch"]
