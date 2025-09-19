"""Tests for HighRiskRule."""

from unittest.mock import patch

from src.orca_core.models import DecisionRequest
from src.orca_core.rules import HighRiskRule


class TestHighRiskRule:
    """Test cases for HighRiskRule."""

    def test_high_risk_rule_triggered(self) -> None:
        """Test high risk rule when risk score exceeds threshold."""
        with patch("src.orca_core.rules.high_risk.predict_risk", return_value=0.95):
            rule = HighRiskRule(threshold=0.80)
            request = DecisionRequest(
                cart_total=100.0, features={"velocity_24h": 2.0, "customer_age": 30}
            )

            result = rule.apply(request)

            assert result is not None
            assert result.decision_hint == "DECLINE"
            assert "HIGH_RISK" in result.reasons[0]
            assert "BLOCK" in result.actions

    def test_high_risk_rule_not_triggered(self) -> None:
        """Test high risk rule when risk score is below threshold."""
        with patch("src.orca_core.rules.high_risk.predict_risk", return_value=0.50):
            rule = HighRiskRule(threshold=0.80)
            request = DecisionRequest(
                cart_total=100.0, features={"velocity_24h": 2.0, "customer_age": 30}
            )

            result = rule.apply(request)

            assert result is None

    def test_high_risk_rule_custom_threshold(self) -> None:
        """Test high risk rule with custom threshold."""
        with patch("src.orca_core.rules.high_risk.predict_risk", return_value=0.70):
            rule = HighRiskRule(threshold=0.60)
            request = DecisionRequest(
                cart_total=100.0, features={"velocity_24h": 2.0, "customer_age": 30}
            )

            result = rule.apply(request)

            assert result is not None
            assert result.decision_hint == "DECLINE"
            assert "HIGH_RISK" in result.reasons[0]

    def test_high_risk_rule_name(self) -> None:
        """Test high risk rule name property."""
        rule = HighRiskRule()
        assert rule.name == "HIGH_RISK"

    def test_high_risk_rule_calls_predict_risk(self) -> None:
        """Test that high risk rule calls predict_risk with correct features."""
        with patch("src.orca_core.rules.high_risk.predict_risk", return_value=0.15) as mock_predict:
            rule = HighRiskRule(threshold=0.80)
            features = {"velocity_24h": 2.0, "customer_age": 30}
            request = DecisionRequest(cart_total=100.0, features=features)

            rule.apply(request)

            mock_predict.assert_called_once_with(features)
