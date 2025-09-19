"""
Comprehensive tests for feature extraction module.

This module tests the core feature extraction functionality that processes
raw request data into standardized features for ML models and rule evaluation.
"""

from src.orca_core.core.feature_extraction import extract_features


class TestFeatureExtraction:
    """Test suite for feature extraction functionality."""

    def test_extract_features_basic_numeric(self):
        """Test extraction of basic numeric features."""
        raw = {"features": {"velocity_24h": 3.5, "velocity_7d": 12.0, "amount": 150.0}}

        result = extract_features(raw)

        assert result["velocity_24h"] == 3.5
        assert result["velocity_7d"] == 12.0
        assert result["amount"] == 150.0

    def test_extract_features_boolean_conversion(self):
        """Test conversion of boolean features to 0/1 values."""
        raw = {
            "features": {"high_ip_distance": True, "cross_border": False, "location_mismatch": True}
        }

        result = extract_features(raw)

        assert result["high_ip_distance"] == 1.0
        assert result["cross_border"] == 0.0
        assert result["location_mismatch"] == 1.0

    def test_extract_features_mixed_types(self):
        """Test extraction with mixed numeric and boolean features."""
        raw = {
            "features": {
                "velocity_24h": 2.5,
                "high_risk": True,
                "amount": 750,
                "safe_transaction": False,
            }
        }

        result = extract_features(raw)

        assert result["velocity_24h"] == 2.5
        assert result["high_risk"] == 1.0
        assert result["amount"] == 750.0
        assert result["safe_transaction"] == 0.0

    def test_extract_features_no_features_key(self):
        """Test handling when features key is missing."""
        raw = {"cart_total": 100.0}

        result = extract_features(raw)

        # Should still derive is_high_ticket
        assert result["is_high_ticket"] == 0.0

    def test_extract_features_empty_features(self):
        """Test handling of empty features dictionary."""
        raw = {"features": {}, "cart_total": 600.0}

        result = extract_features(raw)

        assert result["is_high_ticket"] == 1.0

    def test_extract_features_non_dict_features(self):
        """Test handling when features is not a dictionary."""
        raw = {"features": "not_a_dict", "cart_total": 300.0}

        result = extract_features(raw)

        assert result["is_high_ticket"] == 0.0

    def test_is_high_ticket_derivation(self):
        """Test derivation of is_high_ticket feature from cart_total."""
        # Test high ticket
        raw_high = {"cart_total": 750.0}
        result_high = extract_features(raw_high)
        assert result_high["is_high_ticket"] == 1.0

        # Test low ticket
        raw_low = {"cart_total": 300.0}
        result_low = extract_features(raw_low)
        assert result_low["is_high_ticket"] == 0.0

        # Test boundary case
        raw_boundary = {"cart_total": 500.0}
        result_boundary = extract_features(raw_boundary)
        assert result_boundary["is_high_ticket"] == 0.0

    def test_is_high_ticket_non_numeric_cart_total(self):
        """Test handling of non-numeric cart_total values."""
        raw = {"cart_total": "invalid"}
        result = extract_features(raw)
        assert result["is_high_ticket"] == 0.0

    def test_is_high_ticket_missing_cart_total(self):
        """Test handling when cart_total is missing."""
        raw = {}
        result = extract_features(raw)
        assert result["is_high_ticket"] == 0.0

    def test_ip_country_mismatch_derivation(self):
        """Test derivation of ip_country_mismatch feature."""
        # Test mismatch
        raw_mismatch = {"context": {"location_ip_country": "GB", "billing_country": "US"}}
        result_mismatch = extract_features(raw_mismatch)
        assert result_mismatch["ip_country_mismatch"] == 1.0

        # Test match
        raw_match = {"context": {"location_ip_country": "US", "billing_country": "US"}}
        result_match = extract_features(raw_match)
        assert result_match["ip_country_mismatch"] == 0.0

    def test_ip_country_mismatch_missing_context(self):
        """Test handling when context is missing."""
        raw = {}
        result = extract_features(raw)
        assert result["ip_country_mismatch"] == 0.0

    def test_ip_country_mismatch_non_dict_context(self):
        """Test handling when context is not a dictionary."""
        raw = {"context": "not_a_dict"}
        result = extract_features(raw)
        assert result["ip_country_mismatch"] == 0.0

    def test_ip_country_mismatch_missing_countries(self):
        """Test handling when country fields are missing."""
        raw = {"context": {}}
        result = extract_features(raw)
        assert result["ip_country_mismatch"] == 0.0

    def test_ip_country_mismatch_non_string_countries(self):
        """Test handling when country values are not strings."""
        raw = {"context": {"location_ip_country": 123, "billing_country": "US"}}
        result = extract_features(raw)
        assert result["ip_country_mismatch"] == 0.0

    def test_has_chargebacks_derivation(self):
        """Test derivation of has_chargebacks feature."""
        # Test with chargebacks
        raw_with_chargebacks = {"context": {"customer": {"chargebacks_12m": 2}}}
        result_with = extract_features(raw_with_chargebacks)
        assert result_with["has_chargebacks"] == 1.0

        # Test without chargebacks
        raw_without_chargebacks = {"context": {"customer": {"chargebacks_12m": 0}}}
        result_without = extract_features(raw_without_chargebacks)
        assert result_without["has_chargebacks"] == 0.0

    def test_has_chargebacks_missing_customer(self):
        """Test handling when customer is missing."""
        raw = {"context": {}}
        result = extract_features(raw)
        assert result["has_chargebacks"] == 0.0

    def test_has_chargebacks_non_dict_customer(self):
        """Test handling when customer is not a dictionary."""
        raw = {"context": {"customer": "not_a_dict"}}
        result = extract_features(raw)
        assert result["has_chargebacks"] == 0.0

    def test_has_chargebacks_missing_chargebacks_field(self):
        """Test handling when chargebacks_12m field is missing."""
        raw = {"context": {"customer": {}}}
        result = extract_features(raw)
        assert result["has_chargebacks"] == 0.0

    def test_has_chargebacks_non_numeric_chargebacks(self):
        """Test handling when chargebacks_12m is not numeric."""
        raw = {"context": {"customer": {"chargebacks_12m": "invalid"}}}
        result = extract_features(raw)
        assert result["has_chargebacks"] == 0.0

    def test_has_chargebacks_float_chargebacks(self):
        """Test handling of float chargeback values."""
        raw = {"context": {"customer": {"chargebacks_12m": 1.5}}}
        result = extract_features(raw)
        assert result["has_chargebacks"] == 1.0

    def test_comprehensive_feature_extraction(self):
        """Test comprehensive feature extraction with all features."""
        raw = {
            "cart_total": 750.0,
            "features": {
                "velocity_24h": 3.5,
                "high_ip_distance": True,
                "amount": 150.0,
                "cross_border": False,
            },
            "context": {
                "location_ip_country": "GB",
                "billing_country": "US",
                "customer": {"chargebacks_12m": 2},
            },
        }

        result = extract_features(raw)

        # Check all derived features
        assert result["velocity_24h"] == 3.5
        assert result["high_ip_distance"] == 1.0
        assert result["amount"] == 150.0
        assert result["cross_border"] == 0.0
        assert result["is_high_ticket"] == 1.0
        assert result["ip_country_mismatch"] == 1.0
        assert result["has_chargebacks"] == 1.0

    def test_feature_extraction_with_none_values(self):
        """Test handling of None values in input data."""
        raw = {
            "cart_total": None,
            "features": {"velocity_24h": None, "high_ip_distance": None},
            "context": {"location_ip_country": None, "billing_country": None, "customer": None},
        }

        result = extract_features(raw)

        # Should handle None values gracefully
        assert result["is_high_ticket"] == 0.0
        assert result["ip_country_mismatch"] == 0.0
        assert result["has_chargebacks"] == 0.0

    def test_feature_extraction_empty_input(self):
        """Test handling of completely empty input."""
        raw = {}
        result = extract_features(raw)

        # Should return empty dict with derived features
        assert result["is_high_ticket"] == 0.0
        assert result["ip_country_mismatch"] == 0.0
        assert result["has_chargebacks"] == 0.0

    def test_feature_extraction_nested_structure(self):
        """Test handling of deeply nested structures."""
        raw = {
            "cart_total": 1000.0,
            "features": {"velocity_24h": 5.0, "nested": {"value": 123}},
            "context": {
                "location_ip_country": "CA",
                "billing_country": "US",
                "customer": {"chargebacks_12m": 1, "nested": {"data": "test"}},
            },
        }

        result = extract_features(raw)

        # Should extract only the supported features
        assert result["velocity_24h"] == 5.0
        assert result["is_high_ticket"] == 1.0
        assert result["ip_country_mismatch"] == 1.0
        assert result["has_chargebacks"] == 1.0
        # Nested structures should be ignored
        assert "nested" not in result

    def test_feature_extraction_type_coercion(self):
        """Test type coercion for different input types."""
        raw = {
            "cart_total": "600",  # String that can be converted
            "features": {
                "velocity_24h": "3.5",  # String float
                "amount": 150,  # Integer
                "high_risk": "true",  # String boolean (should be ignored)
            },
        }

        result = extract_features(raw)

        # String numbers should be ignored (not converted)
        assert result["is_high_ticket"] == 0.0  # "600" is not > 500
        # Only numeric types should be extracted
        assert "velocity_24h" not in result  # String ignored
        assert result["amount"] == 150.0  # Integer converted to float

    def test_feature_extraction_large_numbers(self):
        """Test handling of large numbers."""
        raw = {"cart_total": 999999.99, "features": {"velocity_24h": 1000.0, "amount": 50000.0}}

        result = extract_features(raw)

        assert result["is_high_ticket"] == 1.0
        assert result["velocity_24h"] == 1000.0
        assert result["amount"] == 50000.0

    def test_feature_extraction_negative_numbers(self):
        """Test handling of negative numbers."""
        raw = {"cart_total": -100.0, "features": {"velocity_24h": -5.0, "amount": -50.0}}

        result = extract_features(raw)

        assert result["is_high_ticket"] == 0.0  # -100 <= 500
        assert result["velocity_24h"] == -5.0
        assert result["amount"] == -50.0

    def test_feature_extraction_zero_values(self):
        """Test handling of zero values."""
        raw = {
            "cart_total": 0.0,
            "features": {"velocity_24h": 0.0, "amount": 0.0, "high_risk": False},
            "context": {
                "location_ip_country": "",
                "billing_country": "",
                "customer": {"chargebacks_12m": 0},
            },
        }

        result = extract_features(raw)

        assert result["is_high_ticket"] == 0.0
        assert result["velocity_24h"] == 0.0
        assert result["amount"] == 0.0
        assert result["high_risk"] == 0.0
        assert result["ip_country_mismatch"] == 0.0  # "" == ""
        assert result["has_chargebacks"] == 0.0

    def test_feature_extraction_return_type(self):
        """Test that return value is always a dictionary with float values."""
        raw = {"cart_total": 600.0, "features": {"velocity_24h": 3, "high_risk": True}}

        result = extract_features(raw)

        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, float)

    def test_feature_extraction_immutability(self):
        """Test that input data is not modified."""
        raw = {"cart_total": 600.0, "features": {"velocity_24h": 3.5, "high_risk": True}}

        original_raw = raw.copy()
        result = extract_features(raw)

        # Input should be unchanged
        assert raw == original_raw
        # Result should be a new dictionary
        assert result is not raw
        assert result is not raw["features"]
