"""Tests for ML model stub implementation."""

from orca_core.ml.model import get_model_info, predict_risk


class TestPredictRisk:
    """Test predict_risk function."""

    def test_base_score(self):
        """Test base score with minimal features."""
        features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0.0}
        result = predict_risk(features)

        assert result["risk_score"] == 0.35
        assert result["reason_codes"] == ["BASELINE"]
        assert result["version"] == "stub-0.1.0"

    def test_high_amount_trigger(self):
        """Test high amount triggers DUMMY_MCC reason code."""
        features = {"amount": 600.0, "velocity_24h": 1.0, "cross_border": 0.0}
        result = predict_risk(features)

        assert result["risk_score"] == 0.55  # 0.35 + 0.2
        assert "DUMMY_MCC" in result["reason_codes"]
        assert "BASELINE" not in result["reason_codes"]

    def test_high_velocity_trigger(self):
        """Test high velocity triggers VELOCITY reason code."""
        features = {"amount": 100.0, "velocity_24h": 3.0, "cross_border": 0.0}
        result = predict_risk(features)

        assert abs(result["risk_score"] - 0.45) < 1e-10  # 0.35 + 0.1
        assert "VELOCITY" in result["reason_codes"]
        assert "BASELINE" not in result["reason_codes"]

    def test_cross_border_trigger(self):
        """Test cross border triggers CROSS_BORDER reason code."""
        features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 1.0}
        result = predict_risk(features)

        assert abs(result["risk_score"] - 0.45) < 1e-10  # 0.35 + 0.1
        assert "CROSS_BORDER" in result["reason_codes"]
        assert "BASELINE" not in result["reason_codes"]

    def test_multiple_triggers(self):
        """Test multiple risk factors combine correctly."""
        features = {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 1.0}
        result = predict_risk(features)

        assert result["risk_score"] == 0.75  # 0.35 + 0.2 + 0.1 + 0.1
        assert "DUMMY_MCC" in result["reason_codes"]
        assert "VELOCITY" in result["reason_codes"]
        assert "CROSS_BORDER" in result["reason_codes"]
        assert len(result["reason_codes"]) == 3

    def test_score_clamping_upper(self):
        """Test score is clamped to maximum of 1.0."""
        # Create scenario that would exceed 1.0
        # Base 0.35 + amount 0.2 + velocity 0.1 + cross_border 0.1 = 0.75
        features = {"amount": 1000.0, "velocity_24h": 10.0, "cross_border": 1.0}
        result = predict_risk(features)

        assert result["risk_score"] == 0.75  # Should not exceed 1.0, but also not be clamped
        assert result["risk_score"] <= 1.0

    def test_score_clamping_upper_extreme(self):
        """Test score clamping with extreme values that would exceed 1.0."""
        # This test is theoretical since our current scoring maxes out at 0.75
        # But we can test the clamping logic by modifying the model temporarily
        # For now, just verify the current max doesn't exceed 1.0
        features = {"amount": 10000.0, "velocity_24h": 100.0, "cross_border": 1.0}
        result = predict_risk(features)

        assert result["risk_score"] <= 1.0
        assert result["risk_score"] >= 0.0

    def test_score_clamping_lower(self):
        """Test score is clamped to minimum of 0.0."""
        # This test is theoretical since our base score is 0.35
        # But we can test with negative values to ensure clamping works
        features = {"amount": -100.0, "velocity_24h": -1.0, "cross_border": -1.0}
        result = predict_risk(features)

        assert result["risk_score"] == 0.35  # Base score, no penalties
        assert result["risk_score"] >= 0.0

    def test_boundary_values(self):
        """Test boundary values for each trigger."""
        # Test amount boundary (exactly 500)
        features = {"amount": 500.0, "velocity_24h": 1.0, "cross_border": 0.0}
        result = predict_risk(features)
        assert result["risk_score"] == 0.35  # Should not trigger

        # Test amount boundary (just over 500)
        features = {"amount": 500.01, "velocity_24h": 1.0, "cross_border": 0.0}
        result = predict_risk(features)
        assert result["risk_score"] == 0.55  # Should trigger

        # Test velocity boundary (exactly 2)
        features = {"amount": 100.0, "velocity_24h": 2.0, "cross_border": 0.0}
        result = predict_risk(features)
        assert result["risk_score"] == 0.35  # Should not trigger

        # Test velocity boundary (just over 2)
        features = {"amount": 100.0, "velocity_24h": 2.01, "cross_border": 0.0}
        result = predict_risk(features)
        assert abs(result["risk_score"] - 0.45) < 1e-10  # Should trigger

    def test_missing_features(self):
        """Test behavior with missing features."""
        features = {}  # Empty features
        result = predict_risk(features)

        assert result["risk_score"] == 0.35  # Base score
        assert result["reason_codes"] == ["BASELINE"]

    def test_partial_features(self):
        """Test behavior with only some features present."""
        features = {"amount": 600.0}  # Only amount, missing others
        result = predict_risk(features)

        assert result["risk_score"] == 0.55  # 0.35 + 0.2 for amount
        assert "DUMMY_MCC" in result["reason_codes"]

    def test_extra_features(self):
        """Test behavior with extra features not used by the model."""
        features = {
            "amount": 100.0,
            "velocity_24h": 1.0,
            "cross_border": 0.0,
            "extra_feature": 999.0,
            "unused_field": "ignored",
        }
        result = predict_risk(features)

        assert result["risk_score"] == 0.35  # Should ignore extra features
        assert result["reason_codes"] == ["BASELINE"]

    def test_determinism(self):
        """Test that the function is deterministic."""
        features = {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 1.0}

        # Run multiple times
        results = [predict_risk(features) for _ in range(10)]

        # All results should be identical
        for result in results:
            assert result["risk_score"] == 0.75
            assert result["reason_codes"] == ["DUMMY_MCC", "VELOCITY", "CROSS_BORDER"]
            assert result["version"] == "stub-0.1.0"

    def test_cross_border_boolean_handling(self):
        """Test cross_border feature with different boolean-like values."""
        # Test with 1.0 (true)
        features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 1.0}
        result = predict_risk(features)
        assert abs(result["risk_score"] - 0.45) < 1e-10
        assert "CROSS_BORDER" in result["reason_codes"]

        # Test with 0.0 (false)
        features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0.0}
        result = predict_risk(features)
        assert result["risk_score"] == 0.35
        assert "CROSS_BORDER" not in result["reason_codes"]

        # Test with 0.5 (should trigger since > 0)
        features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0.5}
        result = predict_risk(features)
        assert abs(result["risk_score"] - 0.45) < 1e-10
        assert "CROSS_BORDER" in result["reason_codes"]

    def test_reason_codes_ordering(self):
        """Test that reason codes are in expected order."""
        features = {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 1.0}
        result = predict_risk(features)

        # Should be in the order they are checked
        expected_order = ["DUMMY_MCC", "VELOCITY", "CROSS_BORDER"]
        assert result["reason_codes"] == expected_order

    def test_version_consistency(self):
        """Test that version is consistent across all calls."""
        test_cases = [
            {"amount": 100.0},
            {"amount": 600.0, "velocity_24h": 3.0},
            {"cross_border": 1.0},
            {},
        ]

        for features in test_cases:
            result = predict_risk(features)
            assert result["version"] == "stub-0.1.0"


class TestGetModelInfo:
    """Test get_model_info function."""

    def test_model_info_structure(self):
        """Test that model info has expected structure."""
        info = get_model_info()

        assert "name" in info
        assert "version" in info
        assert "type" in info
        assert "description" in info
        assert "features" in info

    def test_model_info_values(self):
        """Test that model info has expected values."""
        info = get_model_info()

        assert info["name"] == "Orca Risk Prediction Stub"
        assert info["version"] == "stub-0.1.0"
        assert info["type"] == "deterministic"
        assert "Phase 2 stub" in info["description"]
        assert info["features"] == ["amount", "velocity_24h", "cross_border"]

    def test_model_info_consistency(self):
        """Test that model info is consistent across calls."""
        info1 = get_model_info()
        info2 = get_model_info()

        assert info1 == info2
