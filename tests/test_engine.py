"""Tests for the decision engine."""

from unittest.mock import patch

from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest


class TestDecisionEngine:
    """Test cases for decision engine evaluation."""

    def test_approve_low_amount(self) -> None:
        """Test approval for amounts <= $500."""
        request = DecisionRequest(cart_total=250.0)
        response = evaluate_rules(request)

        assert response.decision == "APPROVE"
        assert "within approved threshold" in response.reasons[0]
        assert "Process payment" in response.actions
        assert "Send confirmation" in response.actions
        assert "approved_amount" in response.meta

    def test_approve_exact_threshold(self) -> None:
        """Test approval for exactly $500."""
        request = DecisionRequest(cart_total=500.0)
        response = evaluate_rules(request)

        assert response.decision == "APPROVE"
        assert "within approved threshold" in response.reasons[0]

    def test_review_high_amount(self) -> None:
        """Test review for amounts > $500."""
        request = DecisionRequest(cart_total=750.0)
        response = evaluate_rules(request)

        assert response.decision == "REVIEW"
        assert "HIGH_TICKET" in response.reasons[0]
        assert "exceeds $500.00 threshold" in response.reasons[0]
        assert "ROUTE_TO_REVIEW" in response.actions
        assert "HIGH_TICKET" in response.meta["rules_evaluated"]

    def test_review_with_features(self) -> None:
        """Test review with additional features."""
        request = DecisionRequest(
            cart_total=600.0,
            currency="EUR",
            features={"risk_score": 0.8, "customer_age": 25},
            context={"ip_country": "US", "device_type": "mobile"},
        )
        response = evaluate_rules(request)

        assert response.decision == "REVIEW"
        assert "HIGH_TICKET" in response.reasons[0]
        assert "HIGH_TICKET" in response.meta["rules_evaluated"]

    def test_approve_with_context(self) -> None:
        """Test approval with additional context."""
        request = DecisionRequest(
            cart_total=300.0,
            currency="GBP",
            features={"loyalty_score": 0.9},
            context={"previous_orders": 5},
        )
        response = evaluate_rules(request)

        assert response.decision == "APPROVE"
        assert "within approved threshold" in response.reasons[0]

    def test_edge_case_very_high_amount(self) -> None:
        """Test review for very high amounts."""
        request = DecisionRequest(cart_total=10000.0)
        response = evaluate_rules(request)

        assert response.decision == "REVIEW"
        assert "high_ticket" in response.reasons[0]
        assert "HIGH_TICKET" in response.meta["rules_evaluated"]

    def test_currency_handling(self) -> None:
        """Test that currency is preserved in request."""
        request = DecisionRequest(cart_total=400.0, currency="CAD")
        response = evaluate_rules(request)

        assert response.decision == "APPROVE"
        # Currency should be preserved in the original request
        assert request.currency == "CAD"

    def test_velocity_rule_triggered(self) -> None:
        """Test velocity rule when velocity exceeds threshold."""
        request = DecisionRequest(cart_total=100.0, features={"velocity_24h": 5.0})
        response = evaluate_rules(request)

        assert response.decision == "REVIEW"
        assert "velocity_flag" in response.reasons[0]
        assert "block_transaction" in response.actions  # CARD_VELOCITY rule
        assert "ROUTE_TO_REVIEW" in response.actions  # VELOCITY rule
        assert "VELOCITY" in response.meta["rules_evaluated"]
        assert "CARD_VELOCITY" in response.meta["rules_evaluated"]

    def test_multiple_rules_triggered(self) -> None:
        """Test when both high ticket and velocity rules trigger."""
        request = DecisionRequest(cart_total=750.0, features={"velocity_24h": 5.0})
        response = evaluate_rules(request)

        assert response.decision == "REVIEW"
        # With new schema, we get canonical codes + human explanations
        assert len(response.reasons) >= 2  # At least canonical codes
        assert any(
            "HIGH_TICKET" in reason for reason in response.reasons
        )  # Human explanation from HIGH_TICKET rule
        assert any("velocity_flag" in reason for reason in response.reasons)
        assert len(response.actions) >= 2  # Multiple rules trigger multiple actions
        assert "block_transaction" in response.actions  # CARD_VELOCITY rule
        assert "ROUTE_TO_REVIEW" in response.actions  # VELOCITY rule
        assert len(response.meta["rules_evaluated"]) >= 2  # Multiple rules evaluated

    def test_high_risk_rule_triggered(self) -> None:
        """Test when high risk rule triggers with monkeypatched prediction."""
        with (
            patch("orca_core.engine.predict_risk", return_value=0.95),
            patch("orca_core.rules.high_risk.predict_risk", return_value=0.95),
        ):
            request = DecisionRequest(
                cart_total=100.0, features={"velocity_24h": 2.0, "customer_age": 30}
            )
            response = evaluate_rules(request)

            assert response.decision == "DECLINE"
            assert "HIGH_RISK" in response.reasons[0]
            assert "BLOCK" in response.actions
            assert "HIGH_RISK" in response.meta["rules_evaluated"]
            assert response.meta["risk_score"] == 0.95

    def test_risk_score_always_in_meta(self) -> None:
        """Test that risk_score is always added to response meta."""
        request = DecisionRequest(
            cart_total=250.0, features={"velocity_24h": 1.0, "customer_age": 25}
        )
        response = evaluate_rules(request)

        assert "risk_score" in response.meta
        assert response.meta["risk_score"] == 0.15  # Default value
