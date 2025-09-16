"""
Feature Engineering Module for Orca Core ML Models

This module provides consistent feature extraction and engineering
for both the XGBoost model and the ML stub.
"""

from datetime import datetime
from typing import Any

import numpy as np


class FeatureExtractor:
    """Feature extraction and engineering for Orca risk prediction."""

    def __init__(self) -> None:
        """Initialize feature extractor with default configurations."""
        self.feature_names = [
            # Transaction features
            "amount",
            "cart_total",
            "velocity_24h",
            "velocity_7d",
            "velocity_30d",
            # Customer features
            "customer_age_days",
            "loyalty_score",
            "chargebacks_12m",
            "time_since_last_purchase",
            # Location features
            "cross_border",
            "location_mismatch",
            "high_ip_distance",
            # Payment features
            "payment_method_risk",
            "card_bin_risk",
            # Temporal features
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "is_holiday",
            # Derived features
            "amount_velocity_ratio",
            "risk_velocity_interaction",
            "location_velocity_interaction",
        ]

    def extract_features(self, request_data: dict[str, Any]) -> dict[str, float]:
        """
        Extract and engineer features from request data.

        Args:
            request_data: Dictionary containing transaction and context data

        Returns:
            Dictionary of feature names to values
        """
        features = {}

        # Extract basic features
        features.update(self._extract_basic_features(request_data))

        # Extract customer features
        features.update(self._extract_customer_features(request_data))

        # Extract location features
        features.update(self._extract_location_features(request_data))

        # Extract payment features
        features.update(self._extract_payment_features(request_data))

        # Extract temporal features
        features.update(self._extract_temporal_features(request_data))

        # Create derived features
        features.update(self._create_derived_features(features))

        # Ensure all expected features are present
        features = self._ensure_all_features(features)

        return features

    def _extract_basic_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract basic transaction features."""
        features = {}

        # Amount features
        features["amount"] = float(
            data.get("features", {}).get("amount", data.get("cart_total", 0.0))
        )
        features["cart_total"] = float(data.get("cart_total", 0.0))

        # Velocity features
        features["velocity_24h"] = float(data.get("features", {}).get("velocity_24h", 1.0))
        features["velocity_7d"] = float(data.get("features", {}).get("velocity_7d", 3.0))
        features["velocity_30d"] = float(data.get("features", {}).get("velocity_30d", 10.0))

        return features

    def _extract_customer_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract customer-related features."""
        features = {}
        context = data.get("context", {})
        customer = context.get("customer", {})

        # Customer age (days since first transaction)
        features["customer_age_days"] = float(customer.get("age_days", 365.0))

        # Loyalty score (0-1)
        loyalty_tier = customer.get("loyalty_tier", "BRONZE")
        loyalty_scores = {"BRONZE": 0.2, "SILVER": 0.5, "GOLD": 0.8, "PLATINUM": 1.0}
        features["loyalty_score"] = loyalty_scores.get(loyalty_tier, 0.2)

        # Chargeback history
        features["chargebacks_12m"] = float(customer.get("chargebacks_12m", 0.0))

        # Time since last purchase (hours)
        features["time_since_last_purchase"] = float(
            customer.get("time_since_last_purchase_hours", 24.0)
        )

        return features

    def _extract_location_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract location-related features."""
        features = {}
        context = data.get("context", {})

        # Cross-border transaction
        features["cross_border"] = float(data.get("features", {}).get("cross_border", 0.0))

        # Location mismatch (IP vs billing)
        ip_country = context.get("location_ip_country", "US")
        billing_country = context.get("billing_country", "US")
        features["location_mismatch"] = 1.0 if ip_country != billing_country else 0.0

        # High IP distance (simplified)
        features["high_ip_distance"] = float(data.get("features", {}).get("high_ip_distance", 0.0))

        return features

    def _extract_payment_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract payment method features."""
        features = {}
        context = data.get("context", {})

        # Payment method risk scores
        payment_method = context.get("payment_method", {})
        if isinstance(payment_method, dict):
            method_type = payment_method.get("type", "card")
        else:
            method_type = str(payment_method).lower()

        # Risk scores by payment method
        method_risks = {
            "card": 0.3,
            "visa": 0.2,
            "mastercard": 0.2,
            "amex": 0.1,
            "ach": 0.4,
            "bank_transfer": 0.5,
            "paypal": 0.3,
            "apple_pay": 0.1,
            "google_pay": 0.1,
        }
        features["payment_method_risk"] = method_risks.get(method_type, 0.3)

        # Card BIN risk (simplified)
        features["card_bin_risk"] = float(data.get("features", {}).get("card_bin_risk", 0.2))

        return features

    def _extract_temporal_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract temporal features."""
        features = {}

        # Current timestamp
        now = datetime.now()

        # Hour of day (0-23)
        features["hour_of_day"] = float(now.hour)

        # Day of week (0-6, Monday=0)
        features["day_of_week"] = float(now.weekday())

        # Weekend flag
        features["is_weekend"] = 1.0 if now.weekday() >= 5 else 0.0

        # Holiday flag (simplified - just major US holidays)
        features["is_holiday"] = self._is_holiday(now)

        return features

    def _create_derived_features(self, features: dict[str, float]) -> dict[str, float]:
        """Create derived features from basic features."""
        derived = {}

        # Amount to velocity ratio
        if features["velocity_24h"] > 0:
            derived["amount_velocity_ratio"] = features["amount"] / features["velocity_24h"]
        else:
            derived["amount_velocity_ratio"] = features["amount"]

        # Risk-velocity interaction
        derived["risk_velocity_interaction"] = (
            features["payment_method_risk"] * features["velocity_24h"]
        )

        # Location-velocity interaction
        derived["location_velocity_interaction"] = (
            features["cross_border"] * features["velocity_24h"]
        )

        return derived

    def _ensure_all_features(self, features: dict[str, float]) -> dict[str, float]:
        """Ensure all expected features are present with default values."""
        complete_features = {}

        for feature_name in self.feature_names:
            if feature_name in features:
                complete_features[feature_name] = features[feature_name]
            else:
                # Provide sensible defaults
                defaults = {
                    "amount": 100.0,
                    "cart_total": 100.0,
                    "velocity_24h": 1.0,
                    "velocity_7d": 3.0,
                    "velocity_30d": 10.0,
                    "customer_age_days": 365.0,
                    "loyalty_score": 0.5,
                    "chargebacks_12m": 0.0,
                    "time_since_last_purchase": 24.0,
                    "cross_border": 0.0,
                    "location_mismatch": 0.0,
                    "high_ip_distance": 0.0,
                    "payment_method_risk": 0.3,
                    "card_bin_risk": 0.2,
                    "hour_of_day": 12.0,
                    "day_of_week": 2.0,
                    "is_weekend": 0.0,
                    "is_holiday": 0.0,
                    "amount_velocity_ratio": 100.0,
                    "risk_velocity_interaction": 0.3,
                    "location_velocity_interaction": 0.0,
                }
                complete_features[feature_name] = defaults.get(feature_name, 0.0)

        return complete_features

    def _is_holiday(self, date: datetime) -> float:
        """Check if date is a major US holiday (simplified)."""
        # Major US holidays (simplified check)
        holidays = [
            (1, 1),  # New Year's Day
            (7, 4),  # Independence Day
            (12, 25),  # Christmas
            (11, 24),  # Thanksgiving (approximate)
        ]

        return 1.0 if (date.month, date.day) in holidays else 0.0

    def get_feature_names(self) -> list[str]:
        """Get list of all feature names."""
        return self.feature_names.copy()

    def get_feature_vector(self, features: dict[str, float]) -> np.ndarray:
        """Convert features dictionary to numpy array in correct order."""
        return np.array([features[name] for name in self.feature_names])


# Global feature extractor instance
_feature_extractor = None


def get_feature_extractor() -> FeatureExtractor:
    """Get global feature extractor instance."""
    global _feature_extractor
    if _feature_extractor is None:
        _feature_extractor = FeatureExtractor()
    return _feature_extractor


def extract_features(request_data: dict[str, Any]) -> dict[str, float]:
    """Extract features from request data using global extractor."""
    extractor = get_feature_extractor()
    return extractor.extract_features(request_data)
