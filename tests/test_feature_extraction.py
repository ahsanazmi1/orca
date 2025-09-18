"""Tests for feature extraction module."""

from src.orca_core.core.feature_extraction import extract_features


class TestFeatureExtraction:
    """Test cases for extract_features function."""

    def test_extract_features_basic_numeric_features(self) -> None:
        """Test copying of basic numeric features."""
        raw = {"features": {"velocity_24h": 3.5, "customer_age": 25, "transaction_count": 10.0}}

        features = extract_features(raw)

        assert features["velocity_24h"] == 3.5
        assert features["customer_age"] == 25.0
        assert features["transaction_count"] == 10.0

    def test_extract_features_boolean_features(self) -> None:
        """Test conversion of boolean features to 0/1."""
        raw = {
            "features": {"high_ip_distance": True, "is_mobile": False, "has_previous_orders": True}
        }

        features = extract_features(raw)

        assert features["high_ip_distance"] == 1.0
        assert features["is_mobile"] == 0.0
        assert features["has_previous_orders"] == 1.0

    def test_extract_features_mixed_types(self) -> None:
        """Test handling of mixed feature types."""
        raw = {
            "features": {
                "velocity_24h": 2.5,  # float
                "is_weekend": True,  # boolean
                "invalid_feature": "string",  # string (should be ignored)
                "null_feature": None,  # null (should be ignored)
                "list_feature": [1, 2, 3],  # list (should be ignored)
            }
        }

        features = extract_features(raw)

        assert features["velocity_24h"] == 2.5
        assert features["is_weekend"] == 1.0
        assert "invalid_feature" not in features
        assert "null_feature" not in features
        assert "list_feature" not in features

    def test_is_high_ticket_derivation(self) -> None:
        """Test derivation of is_high_ticket feature."""
        # High ticket case
        raw_high = {"cart_total": 750.0}
        features_high = extract_features(raw_high)
        assert features_high["is_high_ticket"] == 1.0

        # Low ticket case
        raw_low = {"cart_total": 250.0}
        features_low = extract_features(raw_low)
        assert features_low["is_high_ticket"] == 0.0

        # Exact threshold case
        raw_exact = {"cart_total": 500.0}
        features_exact = extract_features(raw_exact)
        assert features_exact["is_high_ticket"] == 0.0

        # Just above threshold
        raw_above = {"cart_total": 500.01}
        features_above = extract_features(raw_above)
        assert features_above["is_high_ticket"] == 1.0

    def test_is_high_ticket_invalid_cart_total(self) -> None:
        """Test is_high_ticket with invalid cart_total values."""
        # String cart_total
        raw_string = {"cart_total": "invalid"}
        features_string = extract_features(raw_string)
        assert features_string["is_high_ticket"] == 0.0

        # Missing cart_total
        raw_missing: dict[str, str] = {}
        features_missing = extract_features(raw_missing)
        assert features_missing["is_high_ticket"] == 0.0

        # None cart_total
        raw_none = {"cart_total": None}
        features_none = extract_features(raw_none)
        assert features_none["is_high_ticket"] == 0.0

    def test_ip_country_mismatch_derivation(self) -> None:
        """Test derivation of ip_country_mismatch feature."""
        # Mismatch case
        raw_mismatch = {"context": {"location_ip_country": "GB", "billing_country": "US"}}
        features_mismatch = extract_features(raw_mismatch)
        assert features_mismatch["ip_country_mismatch"] == 1.0

        # Match case
        raw_match = {"context": {"location_ip_country": "US", "billing_country": "US"}}
        features_match = extract_features(raw_match)
        assert features_match["ip_country_mismatch"] == 0.0

        # Empty strings
        raw_empty = {"context": {"location_ip_country": "", "billing_country": ""}}
        features_empty = extract_features(raw_empty)
        assert features_empty["ip_country_mismatch"] == 0.0

    def test_ip_country_mismatch_invalid_context(self) -> None:
        """Test ip_country_mismatch with invalid context values."""
        # Missing context
        raw_no_context: dict[str, str] = {}
        features_no_context = extract_features(raw_no_context)
        assert features_no_context["ip_country_mismatch"] == 0.0

        # Invalid context type
        raw_invalid_context = {"context": "not_a_dict"}
        features_invalid_context = extract_features(raw_invalid_context)
        assert features_invalid_context["ip_country_mismatch"] == 0.0

        # Missing location fields
        raw_missing_fields: dict[str, dict[str, str]] = {"context": {}}
        features_missing_fields = extract_features(raw_missing_fields)
        assert features_missing_fields["ip_country_mismatch"] == 0.0

        # Non-string country values
        raw_non_string = {"context": {"location_ip_country": 123, "billing_country": "US"}}
        features_non_string = extract_features(raw_non_string)
        assert features_non_string["ip_country_mismatch"] == 0.0

    def test_has_chargebacks_derivation(self) -> None:
        """Test derivation of has_chargebacks feature."""
        # Has chargebacks
        raw_with_chargebacks = {"context": {"customer": {"chargebacks_12m": 2}}}
        features_with = extract_features(raw_with_chargebacks)
        assert features_with["has_chargebacks"] == 1.0

        # No chargebacks
        raw_no_chargebacks = {"context": {"customer": {"chargebacks_12m": 0}}}
        features_no = extract_features(raw_no_chargebacks)
        assert features_no["has_chargebacks"] == 0.0

        # Float chargebacks
        raw_float_chargebacks = {"context": {"customer": {"chargebacks_12m": 1.5}}}
        features_float = extract_features(raw_float_chargebacks)
        assert features_float["has_chargebacks"] == 1.0

    def test_has_chargebacks_invalid_customer(self) -> None:
        """Test has_chargebacks with invalid customer data."""
        # Missing context
        raw_no_context: dict[str, str] = {}
        features_no_context = extract_features(raw_no_context)
        assert features_no_context["has_chargebacks"] == 0.0

        # Missing customer
        raw_no_customer: dict[str, dict[str, str]] = {"context": {}}
        features_no_customer = extract_features(raw_no_customer)
        assert features_no_customer["has_chargebacks"] == 0.0

        # Invalid customer type
        raw_invalid_customer = {"context": {"customer": "not_a_dict"}}
        features_invalid_customer = extract_features(raw_invalid_customer)
        assert features_invalid_customer["has_chargebacks"] == 0.0

        # Missing chargebacks field
        raw_missing_chargebacks: dict[str, dict[str, dict[str, str]]] = {
            "context": {"customer": {}}
        }
        features_missing_chargebacks = extract_features(raw_missing_chargebacks)
        assert features_missing_chargebacks["has_chargebacks"] == 0.0

        # Non-numeric chargebacks
        raw_string_chargebacks = {"context": {"customer": {"chargebacks_12m": "invalid"}}}
        features_string_chargebacks = extract_features(raw_string_chargebacks)
        assert features_string_chargebacks["has_chargebacks"] == 0.0

    def test_complete_example(self) -> None:
        """Test complete feature extraction with all derivations."""
        raw = {
            "cart_total": 750.0,
            "features": {"velocity_24h": 3.5, "high_ip_distance": True, "customer_age": 25},
            "context": {
                "location_ip_country": "GB",
                "billing_country": "US",
                "customer": {"loyalty_tier": "GOLD", "chargebacks_12m": 2},
            },
        }

        features = extract_features(raw)

        # Original features
        assert features["velocity_24h"] == 3.5
        assert features["high_ip_distance"] == 1.0
        assert features["customer_age"] == 25.0

        # Derived features
        assert features["is_high_ticket"] == 1.0
        assert features["ip_country_mismatch"] == 1.0
        assert features["has_chargebacks"] == 1.0

    def test_empty_input(self) -> None:
        """Test feature extraction with empty input."""
        raw: dict[str, str] = {}
        features = extract_features(raw)

        # Should have derived features with default values
        assert features["is_high_ticket"] == 0.0
        assert features["ip_country_mismatch"] == 0.0
        assert features["has_chargebacks"] == 0.0

        # Should not have any copied features
        assert len(features) == 3

    def test_missing_features_section(self) -> None:
        """Test feature extraction when features section is missing."""
        raw = {
            "cart_total": 300.0,
            "context": {
                "location_ip_country": "US",
                "billing_country": "US",
                "customer": {"chargebacks_12m": 0},
            },
        }

        features = extract_features(raw)

        # Should only have derived features
        assert features["is_high_ticket"] == 0.0
        assert features["ip_country_mismatch"] == 0.0
        assert features["has_chargebacks"] == 0.0
        assert len(features) == 3

    def test_invalid_features_section(self) -> None:
        """Test feature extraction when features section is not a dict."""
        raw = {"features": "not_a_dict", "cart_total": 100.0}

        features = extract_features(raw)

        # Should only have derived features
        assert features["is_high_ticket"] == 0.0
        assert features["ip_country_mismatch"] == 0.0
        assert features["has_chargebacks"] == 0.0
        assert len(features) == 3

    def test_edge_case_zero_values(self) -> None:
        """Test edge cases with zero values."""
        raw = {
            "cart_total": 0.0,
            "features": {"velocity_24h": 0.0, "high_ip_distance": False},
            "context": {
                "location_ip_country": "US",
                "billing_country": "US",
                "customer": {"chargebacks_12m": 0},
            },
        }

        features = extract_features(raw)

        assert features["velocity_24h"] == 0.0
        assert features["high_ip_distance"] == 0.0
        assert features["is_high_ticket"] == 0.0
        assert features["ip_country_mismatch"] == 0.0
        assert features["has_chargebacks"] == 0.0

    def test_negative_values(self) -> None:
        """Test handling of negative values."""
        raw = {
            "cart_total": -100.0,  # Negative cart total
            "features": {"velocity_24h": -1.0},  # Negative velocity
            "context": {
                "location_ip_country": "US",
                "billing_country": "US",
                "customer": {"chargebacks_12m": -1},  # Negative chargebacks
            },
        }

        features = extract_features(raw)

        assert features["velocity_24h"] == -1.0
        assert features["is_high_ticket"] == 0.0  # Negative < 500
        assert features["ip_country_mismatch"] == 0.0
        assert features["has_chargebacks"] == 0.0  # Negative = 0 chargebacks
