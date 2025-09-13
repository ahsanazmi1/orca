"""Tests for ML scoring functionality."""

from src.orca_core.ml.features import extract_features
from src.orca_core.ml.stub_model import get_features_used, get_model_version, predict_risk
from src.orca_core.models import DecisionRequest


class TestStubModel:
    """Test the ML stub model functionality."""

    def test_predict_risk_deterministic(self):
        """Test that predict_risk returns deterministic values."""
        features1 = {
            "cart_total": 100.0,
            "item_count": 2.0,
            "velocity_24h": 1.0,
            "location_mismatch": 0.0,
        }

        features2 = {
            "cart_total": 100.0,
            "item_count": 2.0,
            "velocity_24h": 1.0,
            "location_mismatch": 0.0,
        }

        score1 = predict_risk(features1)
        score2 = predict_risk(features2)

        assert score1 == score2
        assert 0.0 <= score1 <= 1.0

    def test_predict_risk_override(self):
        """Test that risk_score override works."""
        features = {"cart_total": 100.0, "risk_score": 0.75}

        score = predict_risk(features)
        assert score == 0.75

    def test_predict_risk_high_risk_scenario(self):
        """Test high risk scenario returns high score."""
        features = {
            "cart_total": 2000.0,  # High amount
            "item_count": 15.0,  # Many items
            "velocity_24h": 8.0,  # High velocity
            "location_mismatch": 1.0,  # Location mismatch
        }

        score = predict_risk(features)
        assert score > 0.8  # Should be high risk

    def test_predict_risk_low_risk_scenario(self):
        """Test low risk scenario returns low score."""
        features = {
            "cart_total": 50.0,  # Low amount
            "item_count": 1.0,  # Few items
            "velocity_24h": 1.0,  # Low velocity
            "location_mismatch": 0.0,  # No location mismatch
        }

        score = predict_risk(features)
        assert score < 0.5  # Should be low risk

    def test_get_model_version(self):
        """Test model version is returned correctly."""
        version = get_model_version()
        assert version == "stub-0.1"

    def test_get_features_used(self):
        """Test features used list is returned correctly."""
        features = get_features_used()
        expected_features = ["cart_total", "item_count", "velocity_24h", "location_mismatch"]

        assert features == expected_features


class TestFeatureExtraction:
    """Test feature extraction functionality."""

    def test_extract_features_basic(self):
        """Test basic feature extraction."""
        request = DecisionRequest(
            cart_total=100.0,
            rail="Card",
            channel="online",
            context={"velocity_24h": 2, "item_count": 3},
        )

        features = extract_features(request)

        assert features["cart_total"] == 100.0
        assert features["velocity_24h"] == 2.0
        assert features["item_count"] == 3.0
        assert features["rail_card"] == 1.0
        assert features["rail_ach"] == 0.0
        assert features["channel_online"] == 1.0
        assert features["channel_pos"] == 0.0

    def test_extract_features_ach_rail(self):
        """Test feature extraction for ACH rail."""
        request = DecisionRequest(cart_total=500.0, rail="ACH", channel="pos", context={})

        features = extract_features(request)

        assert features["cart_total"] == 500.0
        assert features["rail_card"] == 0.0
        assert features["rail_ach"] == 1.0
        assert features["channel_online"] == 0.0
        assert features["channel_pos"] == 1.0

    def test_extract_features_with_defaults(self):
        """Test feature extraction with default values."""
        request = DecisionRequest(cart_total=75.0, rail="Card", channel="online")

        features = extract_features(request)

        # Check defaults
        assert features["item_count"] == 1.0
        assert features["velocity_24h"] == 0.0
        assert features["location_mismatch"] == 0.0
        assert features["user_age_days"] == 0.0
        assert features["previous_chargebacks"] == 0.0
        assert features["account_verification_status"] == 0.0

    def test_extract_features_merge_request_features(self):
        """Test that request.features are merged correctly."""
        request = DecisionRequest(
            cart_total=100.0,
            rail="Card",
            channel="online",
            features={"custom_feature": 0.5, "another_feature": 1.0},
        )

        features = extract_features(request)

        assert features["custom_feature"] == 0.5
        assert features["another_feature"] == 1.0
        assert features["cart_total"] == 100.0  # Should still have basic features


class TestMLIntegration:
    """Test ML integration with the decision engine."""

    def test_ml_metadata_in_decision(self):
        """Test that ML metadata is included in decision response."""
        request = DecisionRequest(
            cart_total=100.0, rail="Card", channel="online", context={"velocity_24h": 1}
        )

        from src.orca_core.engine import evaluate_rules

        response = evaluate_rules(request, use_ml=True)

        assert response.meta_structured.model_version == "stub-0.1"
        assert "cart_total" in response.meta_structured.features_used
        assert response.meta_structured.risk_score > 0.0

    def test_ml_disabled_metadata(self):
        """Test that ML disabled returns appropriate metadata."""
        request = DecisionRequest(cart_total=100.0, rail="Card", channel="online")

        from src.orca_core.engine import evaluate_rules

        response = evaluate_rules(request, use_ml=False)

        assert response.meta_structured.model_version == "none"
        assert response.meta_structured.features_used == []
        assert response.meta_structured.risk_score == 0.0

    def test_high_risk_decision_override(self):
        """Test that high ML risk score overrides to DECLINE."""
        request = DecisionRequest(
            cart_total=2000.0,
            rail="Card",
            channel="online",
            context={"velocity_24h": 8, "item_count": 15, "location_mismatch": 1},
        )

        from src.orca_core.engine import evaluate_rules

        response = evaluate_rules(request, use_ml=True)

        assert response.decision == "DECLINE"
        assert "ml_score_high" in response.reasons
        assert "BLOCK" in response.actions
