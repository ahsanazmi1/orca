"""Golden tests for Orca Core decision engine."""

import json

from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest


class TestGolden:
    """Golden tests for regression testing."""

    def test_golden_high_risk_scenario(self) -> None:
        """Test golden scenario with high cart total and velocity."""
        # Input data
        request = DecisionRequest(
            cart_total=750.0, features={"velocity_24h": 4.0}, context={"channel": "ecom"}
        )

        # Evaluate decision
        response = evaluate_rules(request)

        # Convert to dict and normalize ordering (use json mode for datetime serialization)
        response_dict = response.model_dump(mode="json")

        # Serialize to JSON with consistent ordering
        serialized_json = json.dumps(response_dict, sort_keys=True)

        # Parse back to dict for comparison (normalizes ordering)
        normalized_response = json.loads(serialized_json)

        # Expected golden snapshot (updated for actual rule behavior)
        expected_snapshot = {
            "decision": "REVIEW",
            "reasons": [
                "HIGH_TICKET: Cart total $750.00 exceeds $500.00 threshold",
                "VELOCITY_FLAG: 24h velocity 4.0 exceeds 3.0 threshold",
            ],
            "actions": ["ROUTE_TO_REVIEW", "ROUTE_TO_REVIEW"],
            "meta": {"rules_evaluated": ["HIGH_TICKET", "VELOCITY"], "risk_score": 0.595},
        }

        # Assert the response matches the golden snapshot (check only relevant fields)
        assert normalized_response["decision"] == expected_snapshot["decision"]
        assert normalized_response["reasons"] == expected_snapshot["reasons"]
        assert normalized_response["actions"] == expected_snapshot["actions"]
        assert (
            normalized_response["meta"]["rules_evaluated"]
            == expected_snapshot["meta"]["rules_evaluated"]
        )
        assert normalized_response["meta"]["risk_score"] == expected_snapshot["meta"]["risk_score"]

        # Also assert individual fields for better error messages
        assert response.decision == "REVIEW"
        assert len(response.reasons) == 2
        assert "HIGH_TICKET" in response.reasons[0]
        assert "VELOCITY_FLAG" in response.reasons[1]
        assert len(response.actions) == 2
        assert all(action == "ROUTE_TO_REVIEW" for action in response.actions)
        assert 0.0 <= response.meta["risk_score"] <= 1.0  # Valid risk score range
        assert set(response.meta["rules_evaluated"]) == {"HIGH_TICKET", "VELOCITY"}

    def test_golden_approve_scenario(self) -> None:
        """Test golden scenario with low cart total and velocity."""
        # Input data
        request = DecisionRequest(
            cart_total=250.0, features={"velocity_24h": 1.0}, context={"channel": "ecom"}
        )

        # Evaluate decision
        response = evaluate_rules(request)

        # Convert to dict and normalize ordering (use json mode for datetime serialization)
        response_dict = response.model_dump(mode="json")

        # Serialize to JSON with consistent ordering
        serialized_json = json.dumps(response_dict, sort_keys=True)

        # Parse back to dict for comparison (normalizes ordering)
        normalized_response = json.loads(serialized_json)

        # Expected golden snapshot (updated for actual rule behavior)
        expected_snapshot = {
            "decision": "APPROVE",
            "reasons": ["Cart total $250.00 within approved threshold"],
            "actions": ["Process payment", "Send confirmation"],
            "meta": {"approved_amount": 250.0, "risk_score": 0.23, "rules_evaluated": []},
        }

        # Assert the response matches the golden snapshot (check only relevant fields)
        assert normalized_response["decision"] == expected_snapshot["decision"]
        assert normalized_response["reasons"] == expected_snapshot["reasons"]
        assert normalized_response["actions"] == expected_snapshot["actions"]
        assert (
            normalized_response["meta"]["approved_amount"]
            == expected_snapshot["meta"]["approved_amount"]
        )
        assert normalized_response["meta"]["risk_score"] == expected_snapshot["meta"]["risk_score"]
        assert (
            normalized_response["meta"]["rules_evaluated"]
            == expected_snapshot["meta"]["rules_evaluated"]
        )

        # Also assert individual fields for better error messages
        assert response.decision == "APPROVE"
        assert len(response.reasons) == 1
        assert "within approved threshold" in response.reasons[0]
        assert len(response.actions) == 2
        assert "Process payment" in response.actions
        assert "Send confirmation" in response.actions
        assert 0.0 <= response.meta["risk_score"] <= 1.0  # Valid risk score range
        assert response.meta["approved_amount"] == 250.0

    def test_golden_decline_scenario(self) -> None:
        """Test golden scenario with high ML risk score."""
        from unittest.mock import patch

        # Input data
        request = DecisionRequest(
            cart_total=100.0, features={"velocity_24h": 1.0}, context={"channel": "ecom"}
        )

        # Mock high risk score
        with (
            patch("orca_core.engine.predict_risk", return_value=0.95),
            patch("orca_core.rules.high_risk.predict_risk", return_value=0.95),
        ):
            # Evaluate decision
            response = evaluate_rules(request)

            # Convert to dict and normalize ordering (use json mode for datetime serialization)
            response_dict = response.model_dump(mode="json")

            # Serialize to JSON with consistent ordering
            serialized_json = json.dumps(response_dict, sort_keys=True)

            # Parse back to dict for comparison (normalizes ordering)
            normalized_response = json.loads(serialized_json)

            # Expected golden snapshot (updated for actual rule behavior)
            expected_snapshot = {
                "decision": "DECLINE",
                "reasons": [
                    "HIGH_RISK: ML risk score 0.950 exceeds 0.800 threshold",
                    "ml_score_high",
                ],
                "actions": ["BLOCK"],
                "meta": {"risk_score": 0.95, "rules_evaluated": ["HIGH_RISK"]},
            }

            # Assert the response matches the golden snapshot (check only relevant fields)
            assert normalized_response["decision"] == expected_snapshot["decision"]
            assert normalized_response["reasons"] == expected_snapshot["reasons"]
            assert normalized_response["actions"] == expected_snapshot["actions"]
            assert (
                normalized_response["meta"]["risk_score"] == expected_snapshot["meta"]["risk_score"]
            )
            assert (
                normalized_response["meta"]["rules_evaluated"]
                == expected_snapshot["meta"]["rules_evaluated"]
            )

            # Also assert individual fields for better error messages
            assert response.decision == "DECLINE"
            assert len(response.reasons) == 2  # Now includes ml_score_high
            assert "HIGH_RISK" in response.reasons[0]
            assert len(response.actions) == 1
            assert response.actions[0] == "BLOCK"
            assert response.meta["risk_score"] == 0.95
            assert response.meta["rules_evaluated"] == ["HIGH_RISK"]
