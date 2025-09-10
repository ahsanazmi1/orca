"""Tests for ML hooks functionality."""

from orca_core.core.ml_hooks import predict_risk


class TestMLHooks:
    """Test cases for ML hooks."""

    def test_predict_risk_default(self) -> None:
        """Test predict_risk returns default value."""
        features = {"velocity_24h": 2.0, "customer_age": 30}
        risk_score = predict_risk(features)

        assert risk_score == 0.15

    def test_predict_risk_empty_features(self) -> None:
        """Test predict_risk with empty features."""
        features = {}
        risk_score = predict_risk(features)

        assert risk_score == 0.15

    def test_predict_risk_various_features(self) -> None:
        """Test predict_risk with various feature combinations."""
        test_cases = [
            {"velocity_24h": 1.0},
            {"customer_age": 25, "loyalty_score": 0.8},
            {"risk_score": 0.5, "velocity_24h": 3.0, "customer_age": 40},
        ]

        for features in test_cases:
            risk_score = predict_risk(features)
            assert risk_score == 0.15
