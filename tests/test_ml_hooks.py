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
        features: dict[str, float] = {}
        risk_score = predict_risk(features)

        assert risk_score == 0.15

    def test_predict_risk_various_features(self) -> None:
        """Test predict_risk with various feature combinations."""
        # Test case 1: No risk_score in features, should return default
        features1 = {"velocity_24h": 1.0}
        risk_score = predict_risk(features1)
        assert risk_score == 0.15

        # Test case 2: No risk_score in features, should return default
        features2 = {"customer_age": 25, "loyalty_score": 0.8}
        risk_score = predict_risk(features2)
        assert risk_score == 0.15

        # Test case 3: risk_score provided, should return that value
        features3 = {"risk_score": 0.5, "velocity_24h": 3.0, "customer_age": 40}
        risk_score = predict_risk(features3)
        assert risk_score == 0.5
