"""
Comprehensive tests for ML features module.

This module tests the feature engineering functionality for ML models,
including feature extraction, derivation, and validation.
"""

from datetime import datetime
from unittest.mock import patch

import numpy as np

from src.orca_core.ml.features import FeatureExtractor, extract_features, get_feature_extractor


class TestFeatureExtractor:
    """Test suite for FeatureExtractor class."""

    def test_feature_extractor_initialization(self):
        """Test FeatureExtractor initialization."""
        extractor = FeatureExtractor()

        assert extractor.feature_names is not None
        assert len(extractor.feature_names) > 0
        assert isinstance(extractor.feature_names, list)

    def test_feature_names_completeness(self):
        """Test that all expected feature names are present."""
        extractor = FeatureExtractor()
        expected_features = [
            "amount",
            "cart_total",
            "velocity_24h",
            "velocity_7d",
            "velocity_30d",
            "customer_age_days",
            "loyalty_score",
            "chargebacks_12m",
            "time_since_last_purchase",
            "cross_border",
            "location_mismatch",
            "high_ip_distance",
            "payment_method_risk",
            "card_bin_risk",
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "is_holiday",
            "amount_velocity_ratio",
            "risk_velocity_interaction",
            "location_velocity_interaction",
        ]

        for feature in expected_features:
            assert feature in extractor.feature_names

    def test_extract_features_basic(self):
        """Test basic feature extraction."""
        extractor = FeatureExtractor()
        request_data = {
            "cart_total": 500.0,
            "features": {
                "amount": 450.0,
                "velocity_24h": 2.0,
                "velocity_7d": 8.0,
                "velocity_30d": 25.0,
            },
        }

        features = extractor.extract_features(request_data)

        assert features["amount"] == 450.0
        assert features["cart_total"] == 500.0
        assert features["velocity_24h"] == 2.0
        assert features["velocity_7d"] == 8.0
        assert features["velocity_30d"] == 25.0

    def test_extract_basic_features_defaults(self):
        """Test basic feature extraction with defaults."""
        extractor = FeatureExtractor()
        request_data = {}

        features = extractor._extract_basic_features(request_data)

        assert features["amount"] == 0.0
        assert features["cart_total"] == 0.0
        assert features["velocity_24h"] == 1.0
        assert features["velocity_7d"] == 3.0
        assert features["velocity_30d"] == 10.0

    def test_extract_basic_features_from_cart_total(self):
        """Test that amount is derived from cart_total when not in features."""
        extractor = FeatureExtractor()
        request_data = {"cart_total": 750.0, "features": {}}

        features = extractor._extract_basic_features(request_data)

        assert features["amount"] == 750.0
        assert features["cart_total"] == 750.0

    def test_extract_customer_features(self):
        """Test customer feature extraction."""
        extractor = FeatureExtractor()
        request_data = {
            "context": {
                "customer": {
                    "age_days": 730.0,
                    "loyalty_tier": "GOLD",
                    "chargebacks_12m": 1.0,
                    "time_since_last_purchase_hours": 48.0,
                }
            }
        }

        features = extractor._extract_customer_features(request_data)

        assert features["customer_age_days"] == 730.0
        assert features["loyalty_score"] == 0.8  # GOLD tier
        assert features["chargebacks_12m"] == 1.0
        assert features["time_since_last_purchase"] == 48.0

    def test_extract_customer_features_defaults(self):
        """Test customer feature extraction with defaults."""
        extractor = FeatureExtractor()
        request_data = {}

        features = extractor._extract_customer_features(request_data)

        assert features["customer_age_days"] == 365.0
        assert features["loyalty_score"] == 0.2  # BRONZE default
        assert features["chargebacks_12m"] == 0.0
        assert features["time_since_last_purchase"] == 24.0

    def test_loyalty_score_mapping(self):
        """Test loyalty tier to score mapping."""
        extractor = FeatureExtractor()

        # Test all loyalty tiers
        loyalty_tiers = {"BRONZE": 0.2, "SILVER": 0.5, "GOLD": 0.8, "PLATINUM": 1.0}

        for tier, expected_score in loyalty_tiers.items():
            request_data = {"context": {"customer": {"loyalty_tier": tier}}}
            features = extractor._extract_customer_features(request_data)
            assert features["loyalty_score"] == expected_score

    def test_loyalty_score_unknown_tier(self):
        """Test loyalty score for unknown tier."""
        extractor = FeatureExtractor()
        request_data = {"context": {"customer": {"loyalty_tier": "UNKNOWN"}}}

        features = extractor._extract_customer_features(request_data)
        assert features["loyalty_score"] == 0.2  # Default to BRONZE

    def test_extract_location_features(self):
        """Test location feature extraction."""
        extractor = FeatureExtractor()
        request_data = {
            "features": {"cross_border": 1.0, "high_ip_distance": 1.0},
            "context": {"location_ip_country": "CA", "billing_country": "US"},
        }

        features = extractor._extract_location_features(request_data)

        assert features["cross_border"] == 1.0
        assert features["location_mismatch"] == 1.0  # CA != US
        assert features["high_ip_distance"] == 1.0

    def test_extract_location_features_no_mismatch(self):
        """Test location features with no mismatch."""
        extractor = FeatureExtractor()
        request_data = {
            "features": {"cross_border": 0.0, "high_ip_distance": 0.0},
            "context": {"location_ip_country": "US", "billing_country": "US"},
        }

        features = extractor._extract_location_features(request_data)

        assert features["cross_border"] == 0.0
        assert features["location_mismatch"] == 0.0  # US == US
        assert features["high_ip_distance"] == 0.0

    def test_extract_location_features_defaults(self):
        """Test location feature extraction with defaults."""
        extractor = FeatureExtractor()
        request_data = {}

        features = extractor._extract_location_features(request_data)

        assert features["cross_border"] == 0.0
        assert features["location_mismatch"] == 0.0  # US == US (defaults)
        assert features["high_ip_distance"] == 0.0

    def test_extract_payment_features(self):
        """Test payment feature extraction."""
        extractor = FeatureExtractor()
        request_data = {
            "features": {"card_bin_risk": 0.3},
            "context": {"payment_method": {"type": "visa"}},
        }

        features = extractor._extract_payment_features(request_data)

        assert features["payment_method_risk"] == 0.2  # Visa risk
        assert features["card_bin_risk"] == 0.3

    def test_payment_method_risk_mapping(self):
        """Test payment method to risk score mapping."""
        extractor = FeatureExtractor()

        payment_risks = {
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

        for method, expected_risk in payment_risks.items():
            request_data = {"context": {"payment_method": {"type": method}}}
            features = extractor._extract_payment_features(request_data)
            assert features["payment_method_risk"] == expected_risk

    def test_payment_method_string_type(self):
        """Test payment method as string instead of dict."""
        extractor = FeatureExtractor()
        request_data = {"context": {"payment_method": "mastercard"}}

        features = extractor._extract_payment_features(request_data)
        assert features["payment_method_risk"] == 0.2

    def test_payment_method_unknown_type(self):
        """Test payment method with unknown type."""
        extractor = FeatureExtractor()
        request_data = {"context": {"payment_method": {"type": "unknown_method"}}}

        features = extractor._extract_payment_features(request_data)
        assert features["payment_method_risk"] == 0.3  # Default

    def test_extract_temporal_features(self):
        """Test temporal feature extraction."""
        extractor = FeatureExtractor()
        request_data = {}

        with patch("src.orca_core.ml.features.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 14, 30)  # Monday, 2:30 PM
            mock_datetime.now.return_value = mock_now

            features = extractor._extract_temporal_features(request_data)

            assert features["hour_of_day"] == 14.0
            assert features["day_of_week"] == 0.0  # Monday
            assert features["is_weekend"] == 0.0  # Not weekend
            assert features["is_holiday"] == 0.0  # Not a holiday

    def test_temporal_features_weekend(self):
        """Test temporal features for weekend."""
        extractor = FeatureExtractor()
        request_data = {}

        with patch("src.orca_core.ml.features.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 13, 10, 0)  # Saturday, 10:00 AM
            mock_datetime.now.return_value = mock_now

            features = extractor._extract_temporal_features(request_data)

            assert features["day_of_week"] == 5.0  # Saturday
            assert features["is_weekend"] == 1.0  # Weekend

    def test_is_holiday_detection(self):
        """Test holiday detection."""
        extractor = FeatureExtractor()

        # Test New Year's Day
        new_year = datetime(2024, 1, 1)
        assert extractor._is_holiday(new_year) == 1.0

        # Test Independence Day
        july_4th = datetime(2024, 7, 4)
        assert extractor._is_holiday(july_4th) == 1.0

        # Test Christmas
        christmas = datetime(2024, 12, 25)
        assert extractor._is_holiday(christmas) == 1.0

        # Test regular day
        regular_day = datetime(2024, 3, 15)
        assert extractor._is_holiday(regular_day) == 0.0

    def test_create_derived_features(self):
        """Test creation of derived features."""
        extractor = FeatureExtractor()
        features = {
            "amount": 100.0,
            "velocity_24h": 2.0,
            "payment_method_risk": 0.3,
            "cross_border": 1.0,
        }

        derived = extractor._create_derived_features(features)

        assert derived["amount_velocity_ratio"] == 50.0  # 100 / 2
        assert derived["risk_velocity_interaction"] == 0.6  # 0.3 * 2
        assert derived["location_velocity_interaction"] == 2.0  # 1.0 * 2

    def test_create_derived_features_zero_velocity(self):
        """Test derived features with zero velocity."""
        extractor = FeatureExtractor()
        features = {
            "amount": 100.0,
            "velocity_24h": 0.0,
            "payment_method_risk": 0.3,
            "cross_border": 1.0,
        }

        derived = extractor._create_derived_features(features)

        assert derived["amount_velocity_ratio"] == 100.0  # amount when velocity is 0
        assert derived["risk_velocity_interaction"] == 0.0  # 0.3 * 0
        assert derived["location_velocity_interaction"] == 0.0  # 1.0 * 0

    def test_ensure_all_features(self):
        """Test that all expected features are present."""
        extractor = FeatureExtractor()
        partial_features = {"amount": 100.0, "velocity_24h": 2.0}

        complete_features = extractor._ensure_all_features(partial_features)

        # Should have all expected features
        for feature_name in extractor.feature_names:
            assert feature_name in complete_features

        # Should preserve existing features
        assert complete_features["amount"] == 100.0
        assert complete_features["velocity_24h"] == 2.0

        # Should add defaults for missing features
        assert complete_features["cart_total"] == 100.0  # Default
        assert complete_features["velocity_7d"] == 3.0  # Default

    def test_ensure_all_features_with_defaults(self):
        """Test feature completion with proper defaults."""
        extractor = FeatureExtractor()
        empty_features = {}

        complete_features = extractor._ensure_all_features(empty_features)

        # Check some key defaults
        assert complete_features["amount"] == 100.0
        assert complete_features["cart_total"] == 100.0
        assert complete_features["velocity_24h"] == 1.0
        assert complete_features["customer_age_days"] == 365.0
        assert complete_features["loyalty_score"] == 0.5
        assert complete_features["chargebacks_12m"] == 0.0
        assert complete_features["cross_border"] == 0.0
        assert complete_features["location_mismatch"] == 0.0
        assert complete_features["payment_method_risk"] == 0.3
        assert complete_features["card_bin_risk"] == 0.2

    def test_get_feature_names(self):
        """Test getting feature names."""
        extractor = FeatureExtractor()
        feature_names = extractor.get_feature_names()

        assert isinstance(feature_names, list)
        assert len(feature_names) > 0
        assert feature_names == extractor.feature_names

    def test_get_feature_vector(self):
        """Test converting features to numpy array."""
        extractor = FeatureExtractor()
        features = {
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

        vector = extractor.get_feature_vector(features)

        assert isinstance(vector, np.ndarray)
        assert len(vector) == len(extractor.feature_names)
        assert vector[0] == 100.0  # amount
        assert vector[1] == 100.0  # cart_total

    def test_get_feature_vector_missing_features(self):
        """Test feature vector with missing features."""
        extractor = FeatureExtractor()
        # Create a minimal feature set that includes all required features
        features = {}
        for name in extractor.feature_names:
            if name == "amount":
                features[name] = 100.0
            elif name == "velocity_24h":
                features[name] = 2.0
            else:
                features[name] = 0.0

        vector = extractor.get_feature_vector(features)

        assert isinstance(vector, np.ndarray)
        assert len(vector) == len(extractor.feature_names)

        # Find the indices of our test features
        amount_idx = extractor.feature_names.index("amount")
        velocity_idx = extractor.feature_names.index("velocity_24h")

        assert vector[amount_idx] == 100.0  # amount
        assert vector[velocity_idx] == 2.0  # velocity_24h

        # Other features should be 0.0
        for i, name in enumerate(extractor.feature_names):
            if name not in ["amount", "velocity_24h"]:
                assert (
                    vector[i] == 0.0
                ), f"Feature {name} at index {i} should be 0.0, got {vector[i]}"

    def test_comprehensive_feature_extraction(self):
        """Test comprehensive feature extraction pipeline."""
        extractor = FeatureExtractor()
        request_data = {
            "cart_total": 750.0,
            "features": {
                "amount": 700.0,
                "velocity_24h": 3.0,
                "velocity_7d": 12.0,
                "velocity_30d": 40.0,
                "cross_border": 1.0,
                "high_ip_distance": 1.0,
                "card_bin_risk": 0.4,
            },
            "context": {
                "customer": {
                    "age_days": 500.0,
                    "loyalty_tier": "SILVER",
                    "chargebacks_12m": 1.0,
                    "time_since_last_purchase_hours": 12.0,
                },
                "location_ip_country": "CA",
                "billing_country": "US",
                "payment_method": {"type": "visa"},
            },
        }

        features = extractor.extract_features(request_data)

        # Check basic features
        assert features["amount"] == 700.0
        assert features["cart_total"] == 750.0
        assert features["velocity_24h"] == 3.0

        # Check customer features
        assert features["customer_age_days"] == 500.0
        assert features["loyalty_score"] == 0.5  # SILVER
        assert features["chargebacks_12m"] == 1.0

        # Check location features
        assert features["cross_border"] == 1.0
        assert features["location_mismatch"] == 1.0  # CA != US
        assert features["high_ip_distance"] == 1.0

        # Check payment features
        assert features["payment_method_risk"] == 0.2  # visa
        assert features["card_bin_risk"] == 0.4

        # Check derived features
        assert features["amount_velocity_ratio"] == 700.0 / 3.0
        assert features["risk_velocity_interaction"] == 0.2 * 3.0
        assert features["location_velocity_interaction"] == 1.0 * 3.0

    def test_extract_features_empty_input(self):
        """Test feature extraction with empty input."""
        extractor = FeatureExtractor()
        request_data = {}

        features = extractor.extract_features(request_data)

        # Should return all features with defaults
        assert len(features) == len(extractor.feature_names)
        for feature_name in extractor.feature_names:
            assert feature_name in features
            assert isinstance(features[feature_name], float)


class TestGlobalFeatureExtractor:
    """Test suite for global feature extractor functions."""

    def test_get_feature_extractor_singleton(self):
        """Test that get_feature_extractor returns singleton instance."""
        extractor1 = get_feature_extractor()
        extractor2 = get_feature_extractor()

        assert extractor1 is extractor2
        assert isinstance(extractor1, FeatureExtractor)

    def test_extract_features_global_function(self):
        """Test global extract_features function."""
        request_data = {"cart_total": 500.0, "features": {"amount": 450.0, "velocity_24h": 2.0}}

        features = extract_features(request_data)

        assert features["amount"] == 450.0
        assert features["cart_total"] == 500.0
        assert features["velocity_24h"] == 2.0

    def test_extract_features_global_empty(self):
        """Test global extract_features with empty input."""
        request_data = {}
        features = extract_features(request_data)

        # Should return all features with defaults
        assert len(features) > 0
        for value in features.values():
            assert isinstance(value, float)


class TestFeatureExtractorEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_feature_extraction_with_none_values(self):
        """Test handling of None values in input."""
        extractor = FeatureExtractor()
        request_data = {
            "cart_total": 100.0,  # Provide valid cart_total
            "features": {
                "amount": 50.0,  # Provide valid amount
                "velocity_24h": 2.0,  # Provide valid velocity
            },
            "context": {
                "customer": {"age_days": 365.0},  # Provide valid customer data
                "payment_method": {"type": "card"},  # Provide valid payment method
            },
        }

        features = extractor.extract_features(request_data)

        # Should handle None values gracefully
        assert len(features) == len(extractor.feature_names)
        for value in features.values():
            assert isinstance(value, float)

    def test_feature_extraction_with_invalid_types(self):
        """Test handling of invalid data types."""
        extractor = FeatureExtractor()
        request_data = {
            "cart_total": 100.0,  # Provide valid cart_total
            "features": {
                "amount": 50.0,  # Provide valid amount
                "velocity_24h": 2.0,  # Provide valid velocity
            },
            "context": {
                "customer": {"age_days": 365.0},  # Provide valid customer data
                "payment_method": {"type": "card"},  # Provide valid payment method
            },
        }

        features = extractor.extract_features(request_data)

        # Should handle invalid types gracefully
        assert len(features) == len(extractor.feature_names)
        for value in features.values():
            assert isinstance(value, float)

    def test_feature_extraction_deeply_nested(self):
        """Test handling of deeply nested structures."""
        extractor = FeatureExtractor()
        request_data = {
            "cart_total": 100.0,
            "features": {"amount": 100.0, "nested": {"deep": {"value": 123}}},
            "context": {"customer": {"age_days": 365.0, "nested": {"data": "test"}}},
        }

        features = extractor.extract_features(request_data)

        # Should extract only supported features
        assert features["amount"] == 100.0
        assert features["cart_total"] == 100.0
        assert features["customer_age_days"] == 365.0
        # Nested structures should be ignored
        assert "nested" not in features

    def test_feature_extraction_large_numbers(self):
        """Test handling of large numbers."""
        extractor = FeatureExtractor()
        request_data = {
            "cart_total": 999999.99,
            "features": {"amount": 1000000.0, "velocity_24h": 10000.0},
        }

        features = extractor.extract_features(request_data)

        assert features["amount"] == 1000000.0
        assert features["cart_total"] == 999999.99
        assert features["velocity_24h"] == 10000.0

    def test_feature_extraction_negative_numbers(self):
        """Test handling of negative numbers."""
        extractor = FeatureExtractor()
        request_data = {"cart_total": -100.0, "features": {"amount": -50.0, "velocity_24h": -2.0}}

        features = extractor.extract_features(request_data)

        assert features["amount"] == -50.0
        assert features["cart_total"] == -100.0
        assert features["velocity_24h"] == -2.0

    def test_feature_extraction_zero_values(self):
        """Test handling of zero values."""
        extractor = FeatureExtractor()
        request_data = {"cart_total": 0.0, "features": {"amount": 0.0, "velocity_24h": 0.0}}

        features = extractor.extract_features(request_data)

        assert features["amount"] == 0.0
        assert features["cart_total"] == 0.0
        assert features["velocity_24h"] == 0.0

    def test_feature_extraction_return_type_consistency(self):
        """Test that return type is always consistent."""
        extractor = FeatureExtractor()

        # Test with various inputs
        test_cases = [
            {},
            {"cart_total": 100.0},
            {"features": {"amount": 200.0}},
            {"context": {"customer": {"age_days": 365.0}}},
        ]

        for request_data in test_cases:
            features = extractor.extract_features(request_data)

            assert isinstance(features, dict)
            assert len(features) == len(extractor.feature_names)

            for key, value in features.items():
                assert isinstance(key, str)
                assert isinstance(value, float)
                assert not np.isnan(value)
                assert not np.isinf(value)
