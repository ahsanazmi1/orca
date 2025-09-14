"""Tests for engine coverage - error handling and edge cases."""

from orca_core.engine import determine_routing_hint, generate_explanation
from orca_core.models import DecisionRequest


class TestEngineCoverage:
    """Test engine coverage for missing paths."""

    def test_determine_routing_hint_payment_method_dict(self):
        """Test determine_routing_hint when payment_method is a dict."""
        request = DecisionRequest(
            cart_total=100.0, context={"payment_method": {"type": "visa", "last4": "1234"}}
        )

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_VISA_NETWORK"

    def test_determine_routing_hint_route_decision(self):
        """Test determine_routing_hint with ROUTE decision."""
        request = DecisionRequest(cart_total=100.0)

        result = determine_routing_hint("ROUTE", request, {})
        assert result == "ROUTE_TO_MANUAL_REVIEW"

    def test_determine_routing_hint_visa_payment_method(self):
        """Test determine_routing_hint with visa payment method."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "visa"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_VISA_NETWORK"

    def test_determine_routing_hint_mastercard_payment_method(self):
        """Test determine_routing_hint with mastercard payment method."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "mastercard"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_VISA_NETWORK"

    def test_determine_routing_hint_amex_payment_method(self):
        """Test determine_routing_hint with amex payment method."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "amex"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_VISA_NETWORK"

    def test_determine_routing_hint_ach_payment_method(self):
        """Test determine_routing_hint with ach payment method."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "ach"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_ACH_NETWORK"

    def test_determine_routing_hint_bank_transfer_payment_method(self):
        """Test determine_routing_hint with bank_transfer payment method."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "bank_transfer"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_ACH_NETWORK"

    def test_generate_explanation_decline_with_reasons(self):
        """Test generate_explanation for DECLINE with reasons (not high risk)."""
        request = DecisionRequest(cart_total=100.0)
        reasons = [
            "HIGH_TICKET: Cart total exceeds threshold",
            "VELOCITY_FLAG: High velocity detected",
        ]
        meta = {"risk_score": 0.5}  # Not high risk

        result = generate_explanation("DECLINE", reasons, request, meta)
        assert "Transaction declined due to:" in result
        assert "HIGH_TICKET" in result
        assert "VELOCITY_FLAG" in result

    def test_generate_explanation_route_decision(self):
        """Test generate_explanation for ROUTE decision."""
        request = DecisionRequest(cart_total=100.0)
        reasons = [
            "HIGH_TICKET: Cart total exceeds threshold",
            "VELOCITY_FLAG: High velocity detected",
        ]
        meta = {}

        result = generate_explanation("ROUTE", reasons, request, meta)
        assert "Transaction flagged for manual review due to:" in result
        assert "HIGH_TICKET" in result
        assert "VELOCITY_FLAG" in result

    def test_generate_explanation_unknown_decision(self):
        """Test generate_explanation for unknown decision type."""
        request = DecisionRequest(cart_total=100.0)
        reasons = []
        meta = {}

        result = generate_explanation("UNKNOWN", reasons, request, meta)
        assert "Transaction decision: UNKNOWN" in result

    def test_determine_routing_hint_case_insensitive_payment_methods(self):
        """Test that payment method matching is case insensitive."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "VISA"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_VISA_NETWORK"

    def test_determine_routing_hint_ach_case_insensitive(self):
        """Test that ACH payment method matching is case insensitive."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "ACH"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "ROUTE_TO_ACH_NETWORK"

    def test_determine_routing_hint_unknown_payment_method(self):
        """Test determine_routing_hint with unknown payment method."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": "unknown_method"})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "PROCESS_NORMALLY"

    def test_determine_routing_hint_no_payment_method(self):
        """Test determine_routing_hint with no payment method in context."""
        request = DecisionRequest(cart_total=100.0)

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "PROCESS_NORMALLY"

    def test_determine_routing_hint_decline_decision(self):
        """Test determine_routing_hint with DECLINE decision."""
        request = DecisionRequest(cart_total=100.0)

        result = determine_routing_hint("DECLINE", request, {})
        assert result == "BLOCK_TRANSACTION"

    def test_generate_explanation_decline_high_risk(self):
        """Test generate_explanation for DECLINE with high risk score."""
        request = DecisionRequest(cart_total=100.0)
        reasons = ["Some reason"]
        meta = {"risk_score": 0.95}  # High risk

        result = generate_explanation("DECLINE", reasons, request, meta)
        assert "Transaction declined due to high ML risk score of 0.950" in result

    def test_generate_explanation_approve_decision(self):
        """Test generate_explanation for APPROVE decision."""
        request = DecisionRequest(cart_total=100.0)
        reasons = []
        meta = {}

        result = generate_explanation("APPROVE", reasons, request, meta)
        assert "Transaction approved for $100.00" in result
        assert "within approved limits" in result

    def test_determine_routing_hint_payment_method_dict_no_type(self):
        """Test determine_routing_hint when payment_method is a dict without type."""
        request = DecisionRequest(
            cart_total=100.0,
            context={"payment_method": {"last4": "1234"}},  # No type field
        )

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "PROCESS_NORMALLY"

    def test_generate_explanation_with_many_reasons(self):
        """Test generate_explanation with many reasons (should only use first 2)."""
        request = DecisionRequest(cart_total=100.0)
        reasons = [
            "REASON_1: First reason",
            "REASON_2: Second reason",
            "REASON_3: Third reason",
            "REASON_4: Fourth reason",
        ]
        meta = {}

        result = generate_explanation("ROUTE", reasons, request, meta)
        assert "REASON_1" in result
        assert "REASON_2" in result
        assert "REASON_3" not in result
        assert "REASON_4" not in result

    def test_determine_routing_hint_payment_method_none(self):
        """Test determine_routing_hint when payment_method is None."""
        request = DecisionRequest(cart_total=100.0, context={"payment_method": None})

        result = determine_routing_hint("APPROVE", request, {})
        assert result == "PROCESS_NORMALLY"
