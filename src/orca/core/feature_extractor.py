"""Centralized feature extraction for AP2 mandates.

This module provides feature extraction from AP2 mandates for both rules engine
and ML models, ensuring consistent feature mapping across the system.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from ..mandates.ap2_types import (
    CartMandate,
    IntentMandate,
    PaymentMandate,
)
from .decision_contract import AP2DecisionContract


class AP2FeatureExtractor:
    """Feature extractor for AP2 mandates."""

    def __init__(self) -> None:
        """Initialize the AP2 feature extractor."""
        # Only extract features that the model expects
        self.feature_names = [
            "amount",
            "velocity_24h",
            "velocity_7d",
            "cross_border",
            "location_mismatch",
            "payment_method_risk",
            "chargebacks_12m",
            "customer_age_days",
            "loyalty_score",
            "time_since_last_purchase",
        ]

    def extract_features_from_ap2(
        self,
        ap2_contract: AP2DecisionContract,
        additional_features: Optional[dict[str, float]] = None,
    ) -> dict[str, float]:
        """
        Extract features from AP2 decision contract.

        Args:
            ap2_contract: AP2 decision contract containing mandates
            additional_features: Optional additional features to include

        Returns:
            Dictionary of feature names to values

        Raises:
            ValueError: If required AP2 fields are missing or invalid
        """
        features = {}

        # Extract only the features the model expects
        features.update(self._extract_model_features(ap2_contract))

        # Add additional features if provided
        if additional_features:
            features.update(additional_features)

        # Ensure all expected features are present
        features = self._ensure_all_features(features)

        return features

    def _extract_model_features(self, ap2_contract: AP2DecisionContract) -> dict[str, float]:
        """Extract only the features the model expects."""
        features = {}

        # amount - from cart
        features["amount"] = float(ap2_contract.cart.amount)

        # velocity_24h, velocity_7d - from cart (using defaults for now)
        features["velocity_24h"] = 1.0  # Default value
        features["velocity_7d"] = 1.0   # Default value

        # cross_border - from cart geo
        features["cross_border"] = 0.0  # Default value

        # location_mismatch - from cart geo
        features["location_mismatch"] = 0.0  # Default value

        # payment_method_risk - from payment
        features["payment_method_risk"] = 0.2  # Default value

        # chargebacks_12m - customer data (default)
        features["chargebacks_12m"] = 0.0  # Default value

        # customer_age_days - customer data (default)
        features["customer_age_days"] = 365.0  # Default value

        # loyalty_score - customer data (default)
        features["loyalty_score"] = 0.0  # Default value

        # time_since_last_purchase - customer data (default)
        features["time_since_last_purchase"] = 0.0  # Default value

        return features

    def extract_features_from_legacy(self, legacy_data: dict[str, Any]) -> dict[str, float]:
        """
        Extract features from legacy request format for backward compatibility.

        Args:
            legacy_data: Legacy request data

        Returns:
            Dictionary of feature names to values
        """
        features = {}

        # Extract basic features
        features.update(self._extract_legacy_basic_features(legacy_data))
        features.update(self._extract_legacy_customer_features(legacy_data))
        features.update(self._extract_legacy_location_features(legacy_data))
        features.update(self._extract_legacy_payment_features(legacy_data))
        features.update(self._extract_legacy_temporal_features(legacy_data))

        # Create derived features
        features.update(self._create_derived_features(features))

        # Ensure all expected features are present
        features = self._ensure_all_features(features)

        return features

    def _extract_cart_features(self, cart: CartMandate) -> dict[str, float]:
        """Extract features from cart mandate."""
        features = {}

        # Amount features
        features["amount"] = float(cart.amount)
        features["cart_total"] = float(cart.amount)

        # Currency risk (simplified mapping)
        currency_risk_map = {
            "USD": 0.1,
            "EUR": 0.1,
            "GBP": 0.1,
            "CAD": 0.1,
            "AUD": 0.1,
            "JPY": 0.2,
            "CNY": 0.3,
            "INR": 0.4,
            "BRL": 0.3,
            "MXN": 0.3,
        }
        features["currency_risk"] = currency_risk_map.get(cart.currency, 0.5)

        # MCC risk (simplified mapping)
        if cart.mcc:
            mcc_risk_map = {
                "5733": 0.1,  # Electronics
                "5411": 0.2,  # Groceries
                "5812": 0.3,  # Restaurants
                "7011": 0.4,  # Hotels
                "7999": 0.5,  # Entertainment
            }
            features["mcc_risk"] = mcc_risk_map.get(cart.mcc, 0.3)
        else:
            features["mcc_risk"] = 0.3  # Default risk for unknown MCC

        # Item count and complexity
        features["item_count"] = len(cart.items)
        features["avg_item_price"] = float(cart.amount) / len(cart.items) if cart.items else 0.0

        return features

    def _extract_payment_features(self, payment: PaymentMandate) -> dict[str, float]:
        """Extract features from payment mandate."""
        features = {}

        # Payment modality risk
        modality_risk_map = {
            "immediate": 0.1,
            "deferred": 0.3,
            "recurring": 0.4,
            "installment": 0.5,
        }
        features["modality_risk"] = modality_risk_map.get(payment.modality, 0.3)

        # Authentication requirement risk
        auth_risk_map = {
            "none": 0.5,
            "pin": 0.3,
            "biometric": 0.2,
            "two_factor": 0.1,
            "multi_factor": 0.05,
        }

        if payment.auth_requirements:
            # Use the highest risk requirement
            max_auth_risk = max(auth_risk_map.get(req, 0.3) for req in payment.auth_requirements)
            features["auth_requirement_risk"] = max_auth_risk
        else:
            features["auth_requirement_risk"] = 0.5

        # Payment method risk (simplified)
        if payment.instrument_ref:
            if "card_" in payment.instrument_ref:
                features["payment_method_risk"] = 0.2
            elif "bank_" in payment.instrument_ref:
                features["payment_method_risk"] = 0.3
            else:
                features["payment_method_risk"] = 0.4
        else:
            features["payment_method_risk"] = 0.4

        return features

    def _extract_intent_features(self, intent: IntentMandate) -> dict[str, float]:
        """Extract features from intent mandate."""
        features = {}

        # Actor risk
        actor_risk_map = {
            "human": 0.1,
            "agent": 0.3,
            "system": 0.5,
        }
        features["actor_risk"] = actor_risk_map.get(intent.actor, 0.3)

        # Channel risk
        channel_risk_map = {
            "web": 0.2,
            "mobile": 0.1,
            "api": 0.3,
            "voice": 0.4,
            "chat": 0.3,
            "pos": 0.1,
        }
        features["channel_risk"] = channel_risk_map.get(intent.channel, 0.3)

        # Agent presence risk
        agent_presence_risk_map = {
            "none": 0.2,
            "assisted": 0.1,
            "autonomous": 0.4,
        }
        features["agent_presence_risk"] = agent_presence_risk_map.get(intent.agent_presence, 0.2)

        # Intent type risk
        intent_type_risk_map = {
            "purchase": 0.1,
            "refund": 0.3,
            "transfer": 0.4,
            "subscription": 0.2,
            "donation": 0.3,
            "investment": 0.5,
        }
        features["intent_type_risk"] = intent_type_risk_map.get(intent.intent_type, 0.3)

        return features

    def _extract_geo_features(self, cart: CartMandate) -> dict[str, float]:
        """Extract geographic features from cart mandate."""
        features = {}

        if cart.geo:
            # Country risk (simplified mapping)
            country_risk_map = {
                "US": 0.1,
                "CA": 0.1,
                "GB": 0.1,
                "DE": 0.1,
                "FR": 0.1,
                "AU": 0.1,
                "JP": 0.2,
                "CN": 0.3,
                "IN": 0.4,
                "BR": 0.3,
                "MX": 0.3,
                "RU": 0.5,
                "NG": 0.6,
                "VE": 0.6,
            }
            features["geo_risk_score"] = country_risk_map.get(cart.geo.country, 0.4)

            # Cross-border indicator (simplified)
            features["cross_border"] = 1.0 if cart.geo.country != "US" else 0.0
        else:
            features["geo_risk_score"] = 0.5  # Default risk for unknown location
            features["cross_border"] = 0.0

        # Location mismatch (would need additional context)
        features["location_mismatch"] = 0.0  # Default, would be calculated from IP vs billing

        return features

    def _extract_temporal_features(self, intent: IntentMandate) -> dict[str, float]:  # type: ignore[unreachable,unused-ignore]
        """Extract temporal features from intent mandate."""
        features = {}

        # Extract timestamp information
        created_time_raw = intent.timestamps.get("created")
        if created_time_raw:
            if isinstance(created_time_raw, str):  # type: ignore[unreachable]
                # Parse ISO format
                try:  # type: ignore[unreachable]
                    created_time = datetime.fromisoformat(created_time_raw.replace("Z", "+00:00"))
                except ValueError:
                    created_time = datetime.now(UTC)
            else:
                # Assume it's already a datetime
                created_time = created_time_raw
        else:
            created_time = datetime.now(UTC)

        # Ensure timezone awareness
        if created_time.tzinfo is None:
            created_time = created_time.replace(tzinfo=UTC)

        # Extract temporal features
        features["hour_of_day"] = float(created_time.hour)
        features["day_of_week"] = float(created_time.weekday())
        features["is_weekend"] = 1.0 if created_time.weekday() >= 5 else 0.0
        features["is_holiday"] = 0.0  # Would need holiday calendar

        return features

    def _extract_legacy_basic_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract basic features from legacy data."""
        features = {}

        # Amount features
        features["amount"] = float(data.get("cart_total", 0.0))
        features["cart_total"] = float(data.get("cart_total", 0.0))

        # Velocity features
        features_data = data.get("features", {})
        features["velocity_24h"] = float(features_data.get("velocity_24h", 1.0))
        features["velocity_7d"] = float(features_data.get("velocity_7d", 3.0))
        features["velocity_30d"] = float(features_data.get("velocity_30d", 10.0))

        return features

    def _extract_legacy_customer_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract customer features from legacy data."""
        features = {}

        context = data.get("context", {})
        customer = context.get("customer", {})

        features["customer_age_days"] = float(customer.get("account_age_days", 365))
        features["chargebacks_12m"] = float(customer.get("chargebacks_12m", 0))

        # Loyalty score mapping
        loyalty_tier = customer.get("loyalty_tier", "BRONZE")
        loyalty_map = {"BRONZE": 0.1, "SILVER": 0.2, "GOLD": 0.3, "PLATINUM": 0.4}
        features["loyalty_score"] = loyalty_map.get(loyalty_tier, 0.1)

        return features

    def _extract_legacy_location_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract location features from legacy data."""
        features = {}

        context = data.get("context", {})
        location = context.get("location", {})

        # Country risk
        country = location.get("country", "US")
        country_risk_map = {
            "US": 0.1,
            "CA": 0.1,
            "GB": 0.1,
            "DE": 0.1,
            "FR": 0.1,
            "AU": 0.1,
            "JP": 0.2,
            "CN": 0.3,
            "IN": 0.4,
            "BR": 0.3,
        }
        features["geo_risk_score"] = country_risk_map.get(country, 0.4)

        # Cross-border
        features["cross_border"] = 1.0 if country != "US" else 0.0

        # Location mismatch
        ip_country = context.get("location_ip_country", country)
        billing_country = context.get("billing_country", country)
        features["location_mismatch"] = 1.0 if ip_country != billing_country else 0.0

        return features

    def _extract_legacy_payment_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract payment features from legacy data."""
        features = {}

        # Rail-based risk
        rail = data.get("rail", "Card")
        rail_risk_map = {"Card": 0.2, "ACH": 0.3}
        features["payment_method_risk"] = rail_risk_map.get(rail, 0.3)

        # Channel-based risk
        channel = data.get("channel", "online")
        channel_risk_map = {"online": 0.2, "pos": 0.1}
        features["channel_risk"] = channel_risk_map.get(channel, 0.2)

        return features

    def _extract_legacy_temporal_features(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract temporal features from legacy data."""
        features = {}

        # Use current time if no timestamp provided
        now = datetime.now(UTC)
        features["hour_of_day"] = float(now.hour)
        features["day_of_week"] = float(now.weekday())
        features["is_weekend"] = 1.0 if now.weekday() >= 5 else 0.0
        features["is_holiday"] = 0.0

        return features

    def _create_derived_features(self, features: dict[str, float]) -> dict[str, float]:
        """Create derived features from base features."""
        derived = {}

        # Amount-velocity ratio
        amount = features.get("amount", 0.0)
        velocity_24h = features.get("velocity_24h", 1.0)
        derived["amount_velocity_ratio"] = amount / max(velocity_24h, 1.0)

        # Risk-velocity interaction
        base_risk = (
            features.get("currency_risk", 0.3)
            + features.get("mcc_risk", 0.3)
            + features.get("modality_risk", 0.3)
        ) / 3.0
        derived["risk_velocity_interaction"] = base_risk * velocity_24h

        # Location-velocity interaction
        geo_risk = features.get("geo_risk_score", 0.3)
        derived["location_velocity_interaction"] = geo_risk * velocity_24h

        # Composite risk score
        composite_risk = (
            features.get("actor_risk", 0.3)
            + features.get("channel_risk", 0.3)
            + features.get("modality_risk", 0.3)
            + features.get("geo_risk_score", 0.3)
            + features.get("payment_method_risk", 0.3)
        ) / 5.0
        derived["composite_risk_score"] = composite_risk

        return derived

    def _ensure_all_features(self, features: dict[str, float]) -> dict[str, float]:
        """Ensure all expected features are present with default values."""
        for feature_name in self.feature_names:
            if feature_name not in features:
                # Set appropriate defaults based on feature type
                if "risk" in feature_name:
                    features[feature_name] = 0.3  # Default risk
                elif "velocity" in feature_name:
                    features[feature_name] = 1.0  # Default velocity
                elif "age" in feature_name or "days" in feature_name:
                    features[feature_name] = 365.0  # Default age
                elif "count" in feature_name:
                    features[feature_name] = 1.0  # Default count
                else:
                    features[feature_name] = 0.0  # Default value

        return features

    def validate_ap2_contract(self, ap2_contract: AP2DecisionContract) -> None:
        """
        Validate that AP2 contract has required fields for feature extraction.

        Args:
            ap2_contract: AP2 decision contract to validate

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if ap2_contract is None:
            raise ValueError("AP2 contract is required")

        # Validate cart mandate
        if not ap2_contract.cart:
            raise ValueError("Cart mandate is required for feature extraction")

        if not ap2_contract.cart.items:
            raise ValueError("Cart must contain at least one item")

        if ap2_contract.cart.amount <= 0:
            raise ValueError("Cart amount must be greater than 0")

        # Validate payment mandate
        if not ap2_contract.payment:
            raise ValueError("Payment mandate is required for feature extraction")

        if not ap2_contract.payment.instrument_ref and not ap2_contract.payment.instrument_token:
            raise ValueError("Payment must have either instrument_ref or instrument_token")

        # Validate intent mandate
        if not ap2_contract.intent:
            raise ValueError("Intent mandate is required for feature extraction")

        if not ap2_contract.intent.timestamps:
            raise ValueError("Intent must have timestamps")

        if "created" not in ap2_contract.intent.timestamps:
            raise ValueError("Intent must have 'created' timestamp")


# Global feature extractor instance
_feature_extractor: Optional[AP2FeatureExtractor] = None


def get_ap2_feature_extractor() -> AP2FeatureExtractor:
    """Get the global AP2 feature extractor instance."""
    global _feature_extractor
    if _feature_extractor is None:
        _feature_extractor = AP2FeatureExtractor()
    return _feature_extractor


def extract_features_from_ap2(
    ap2_contract: AP2DecisionContract, additional_features: Optional[dict[str, float]] = None
) -> dict[str, float]:
    """Extract features from AP2 contract using global extractor."""
    extractor = get_ap2_feature_extractor()
    return extractor.extract_features_from_ap2(ap2_contract, additional_features)


def extract_features_from_legacy(legacy_data: dict[str, Any]) -> dict[str, float]:
    """Extract features from legacy data using global extractor."""
    extractor = get_ap2_feature_extractor()
    return extractor.extract_features_from_legacy(legacy_data)
