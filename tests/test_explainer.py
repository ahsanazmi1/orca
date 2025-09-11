"""Tests for decision explainer module."""


from orca_core.core.explainer import explain_decision
from orca_core.models import DecisionResponse


class TestDecisionExplainer:
    """Test cases for explain_decision function."""

    def test_high_ticket_explanation(self) -> None:
        """Test explanation for high ticket decision."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["HIGH_TICKET: Cart total $750.00 exceeds $500.00 threshold"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "cart total was unusually high" in explanation
        assert "flagged for review" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_velocity_flag_explanation(self) -> None:
        """Test explanation for velocity flag decision."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["VELOCITY_FLAG: 24h velocity 4.0 exceeds 3.0 threshold"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "multiple purchases in a short time" in explanation
        assert "velocity check" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_location_mismatch_explanation(self) -> None:
        """Test explanation for location mismatch decision."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["LOCATION_MISMATCH: IP country 'GB' differs from billing country 'US'"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "billing country did not match the IP location" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_high_ip_distance_explanation(self) -> None:
        """Test explanation for high IP distance decision."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["HIGH_IP_DISTANCE: Transaction originates from high-risk IP distance"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "IP address was far from their billing address" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_chargeback_history_explanation(self) -> None:
        """Test explanation for chargeback history decision."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["CHARGEBACK_HISTORY: Customer has 1 chargeback(s) in last 12 months"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "history of chargebacks" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_loyalty_boost_explanation(self) -> None:
        """Test explanation for loyalty boost decision."""
        response = DecisionResponse(
            decision="APPROVE",
            reasons=["LOYALTY_BOOST: Customer has GOLD loyalty tier"],
            actions=["LOYALTY_BOOST"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "loyalty tier provided a benefit" in explanation
        assert "Final decision: APPROVE" in explanation

    def test_high_risk_explanation(self) -> None:
        """Test explanation for high risk decision."""
        response = DecisionResponse(
            decision="DECLINE",
            reasons=["HIGH_RISK: ML risk score 0.950 exceeds 0.800 threshold"],
            actions=["BLOCK"],
            meta={"risk_score": 0.95},
        )

        explanation = explain_decision(response)

        assert "ML model predicted this transaction as high risk" in explanation
        assert "Final decision: DECLINE" in explanation

    def test_multiple_reasons_explanation(self) -> None:
        """Test explanation for multiple reasons."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=[
                "LOCATION_MISMATCH: IP country 'GB' differs from billing country 'US'",
                "HIGH_IP_DISTANCE: Transaction originates from high-risk IP distance",
                "LOYALTY_BOOST: Customer has GOLD loyalty tier",
            ],
            actions=["ROUTE_TO_REVIEW", "LOYALTY_BOOST"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        # Should contain all three explanations
        assert "billing country did not match the IP location" in explanation
        assert "IP address was far from their billing address" in explanation
        assert "loyalty tier provided a benefit" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_no_reasons_default_explanation(self) -> None:
        """Test default explanation when no reasons are provided."""
        response = DecisionResponse(
            decision="APPROVE", reasons=[], actions=["Process payment"], meta={"risk_score": 0.15}
        )

        explanation = explain_decision(response)

        assert "no risk rules were triggered" in explanation
        assert "Final decision: APPROVE" in explanation

    def test_no_reasons_non_approve_explanation(self) -> None:
        """Test default explanation for non-approve decisions with no reasons."""
        response = DecisionResponse(
            decision="REVIEW", reasons=[], actions=["ROUTE_TO_REVIEW"], meta={"risk_score": 0.15}
        )

        explanation = explain_decision(response)

        assert "processed the transaction based on configured rules" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_unknown_reason_code_fallback(self) -> None:
        """Test fallback explanation for unknown reason codes."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["UNKNOWN_RULE: Some unknown rule was triggered"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "Rule 'UNKNOWN_RULE' was triggered" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_reason_code_extraction(self) -> None:
        """Test that reason codes are correctly extracted from full reason strings."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["HIGH_TICKET: Cart total $750.00 exceeds $500.00 threshold"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        # Should use the HIGH_TICKET explanation, not the raw reason text
        assert "cart total was unusually high" in explanation
        assert "Cart total $750.00 exceeds $500.00 threshold" not in explanation

    def test_decision_summary_always_present(self) -> None:
        """Test that decision summary is always present in explanations."""
        test_cases = [
            ("APPROVE", []),
            ("REVIEW", ["HIGH_TICKET: Test reason"]),
            ("DECLINE", ["HIGH_RISK: Test reason"]),
        ]

        for decision, reasons in test_cases:
            response = DecisionResponse(
                decision=decision,
                reasons=reasons,
                actions=["Test action"],
                meta={"risk_score": 0.15},
            )

            explanation = explain_decision(response)
            assert f"Final decision: {decision}" in explanation

    def test_explanation_format(self) -> None:
        """Test that explanation follows expected format."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["HIGH_TICKET: Cart total $750.00 exceeds $500.00 threshold"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        # Should be a single string
        assert isinstance(explanation, str)

        # Should not be empty
        assert len(explanation.strip()) > 0

        # Should end with decision summary
        assert explanation.endswith("Final decision: REVIEW.")

    def test_multiple_sentences_concatenation(self) -> None:
        """Test that multiple explanation sentences are properly concatenated."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=[
                "HIGH_TICKET: Cart total $750.00 exceeds $500.00 threshold",
                "VELOCITY_FLAG: 24h velocity 4.0 exceeds 3.0 threshold",
            ],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        # Should contain both explanations
        assert "cart total was unusually high" in explanation
        assert "multiple purchases in a short time" in explanation

        # Should be properly concatenated (no double spaces, proper sentence structure)
        assert "  " not in explanation  # No double spaces
        assert explanation.count(".") >= 2  # At least two sentences (explanations + final decision)

    def test_high_ticket_velocity_combination(self) -> None:
        """Test explanation for HIGH_TICKET and VELOCITY_FLAG combination."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["HIGH_TICKET", "VELOCITY_FLAG"],
            actions=["ROUTE_TO_REVIEW"],
            meta={"risk_score": 0.15},
        )

        explanation = explain_decision(response)

        assert "unusually high" in explanation
        assert "multiple purchases" in explanation
        assert "Final decision: REVIEW" in explanation

    def test_high_risk_decline_explanation(self) -> None:
        """Test explanation for HIGH_RISK DECLINE decision."""
        response = DecisionResponse(
            decision="DECLINE", reasons=["HIGH_RISK"], actions=["BLOCK"], meta={"risk_score": 0.95}
        )

        explanation = explain_decision(response)

        assert "predicted this transaction as high risk" in explanation
        assert "Final decision: DECLINE" in explanation

    def test_empty_reasons_approve_explanation(self) -> None:
        """Test explanation for APPROVE decision with empty reasons."""
        response = DecisionResponse(
            decision="APPROVE", reasons=[], actions=["Process payment"], meta={"risk_score": 0.15}
        )

        explanation = explain_decision(response)

        assert "no risk rules were triggered" in explanation
        assert "Final decision: APPROVE" in explanation
