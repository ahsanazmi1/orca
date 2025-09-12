"""Feature extraction for ML scoring."""


from ..models import DecisionRequest


def extract_features(request: DecisionRequest) -> dict[str, float]:
    """
    Extract features from decision request for ML scoring.

    Args:
        request: The decision request to extract features from

    Returns:
        Dictionary of feature values for ML model
    """
    features = {}

    # Basic cart features
    features["cart_total"] = float(request.cart_total)
    features["item_count"] = float(request.context.get("item_count", 1))

    # Velocity features
    features["velocity_24h"] = float(request.context.get("velocity_24h", 0))
    features["velocity_7d"] = float(request.context.get("velocity_7d", 0))

    # Location features
    features["location_mismatch"] = float(request.context.get("location_mismatch", 0))

    # Rail and channel features (encoded as numeric)
    features["rail_card"] = 1.0 if request.rail == "Card" else 0.0
    features["rail_ach"] = 1.0 if request.rail == "ACH" else 0.0
    features["channel_online"] = 1.0 if request.channel == "online" else 0.0
    features["channel_pos"] = 1.0 if request.channel == "pos" else 0.0

    # Additional context features
    features["user_age_days"] = float(request.context.get("user_age_days", 0))
    features["previous_chargebacks"] = float(request.context.get("previous_chargebacks", 0))
    features["account_verification_status"] = float(
        request.context.get("account_verification_status", 0)
    )

    # Merge any additional features from request.features
    for key, value in request.features.items():
        if isinstance(value, bool):
            features[key] = 1.0 if value else 0.0
        elif isinstance(value, int | float):
            features[key] = float(value)

    return features
