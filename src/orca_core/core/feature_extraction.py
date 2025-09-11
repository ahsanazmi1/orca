"""Feature extraction utilities for Orca Core decision engine."""

from typing import Any


def extract_features(raw: dict[str, Any]) -> dict[str, float]:
    """
    Extract and derive features from raw request data.

    This function processes raw request data to create a standardized feature set
    suitable for ML models and rule evaluation. It copies numeric-safe features
    and derives additional boolean features as 0/1 values.

    Args:
        raw: Raw request data containing cart_total, features, and context

    Returns:
        Dictionary of extracted features with string keys and float values

    Examples:
        >>> raw = {
        ...     "cart_total": 750.0,
        ...     "features": {"velocity_24h": 3.5, "high_ip_distance": True},
        ...     "context": {
        ...         "location_ip_country": "GB",
        ...         "billing_country": "US",
        ...         "customer": {"chargebacks_12m": 2}
        ...     }
        ... }
        >>> features = extract_features(raw)
        >>> features["velocity_24h"]
        3.5
        >>> features["is_high_ticket"]
        1.0
        >>> features["ip_country_mismatch"]
        1.0
        >>> features["has_chargebacks"]
        1.0
    """
    features: dict[str, float] = {}

    # Copy numeric-safe keys from request.features
    if "features" in raw and isinstance(raw["features"], dict):
        for key, value in raw["features"].items():
            if isinstance(value, int | float):
                features[key] = float(value)
            elif isinstance(value, bool):
                features[key] = 1.0 if value else 0.0

    # Derive is_high_ticket from cart_total > 500
    cart_total = raw.get("cart_total", 0.0)
    if isinstance(cart_total, int | float):
        features["is_high_ticket"] = 1.0 if cart_total > 500.0 else 0.0
    else:
        features["is_high_ticket"] = 0.0

    # Derive ip_country_mismatch from location vs billing country
    context = raw.get("context", {})
    if isinstance(context, dict):
        ip_country = context.get("location_ip_country", "")
        billing_country = context.get("billing_country", "")

        if isinstance(ip_country, str) and isinstance(billing_country, str):
            features["ip_country_mismatch"] = 1.0 if ip_country != billing_country else 0.0
        else:
            features["ip_country_mismatch"] = 0.0
    else:
        features["ip_country_mismatch"] = 0.0

    # Derive has_chargebacks from customer chargeback history
    customer = context.get("customer", {}) if isinstance(context, dict) else {}
    if isinstance(customer, dict):
        chargebacks = customer.get("chargebacks_12m", 0)
        if isinstance(chargebacks, int | float):
            features["has_chargebacks"] = 1.0 if chargebacks > 0 else 0.0
        else:
            features["has_chargebacks"] = 0.0
    else:
        features["has_chargebacks"] = 0.0

    return features
