"""Parametrized tests for fixture files validation."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest


class TestFixturesParametrized:
    """Parametrized tests for fixture file validation."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return the fixtures directory path."""
        return Path("fixtures/requests")

    @pytest.fixture
    def fixture_files(self, fixtures_dir: Path) -> list[Path]:
        """Return list of fixture file paths."""
        if not fixtures_dir.exists():
            pytest.skip("Fixtures directory not found")

        fixture_files = list(fixtures_dir.glob("*.json"))
        if not fixture_files:
            pytest.skip("No fixture files found")

        return fixture_files

    @pytest.mark.parametrize("fixture_name,expected_decision,expected_reasons,expected_actions,use_ml", [
        (
            "low_ticket_ok.json",
            "APPROVE",
            [],  # No specific reasons expected for approve
            ["LOYALTY_BOOST"],  # Should have loyalty boost action
            True
        ),
        (
            "high_ticket_review.json",
            "REVIEW",
            ["HIGH_TICKET"],
            ["ROUTE_TO_REVIEW"],
            True
        ),
        (
            "velocity_review.json",
            "REVIEW",
            ["VELOCITY_FLAG"],
            ["ROUTE_TO_REVIEW"],
            True
        ),
        (
            "location_mismatch_review.json",
            "REVIEW",
            ["LOCATION_MISMATCH", "HIGH_IP_DISTANCE"],  # Should have both
            ["ROUTE_TO_REVIEW"],
            True
        ),
        (
            "high_risk_decline.json",
            "DECLINE",
            ["CHARGEBACK_HISTORY", "HIGH_RISK"],  # Chargeback + high risk
            ["BLOCK"],
            True
        ),
    ])
    def test_fixture_decision_outcomes(
        self,
        fixture_name: str,
        expected_decision: str,
        expected_reasons: list[str],
        expected_actions: list[str],
        use_ml: bool,
        fixtures_dir: Path
    ) -> None:
        """Test that fixture files produce expected decision outcomes."""
        fixture_path = fixtures_dir / fixture_name

        if not fixture_path.exists():
            pytest.skip(f"Fixture file {fixture_name} not found")

        # Load fixture data
        with open(fixture_path) as f:
            raw_data = json.load(f)

        # Create DecisionRequest
        request = DecisionRequest(**raw_data)

        # For high_risk_decline, monkeypatch predict_risk to return 0.95
        if fixture_name == "high_risk_decline.json":
            with patch("orca_core.engine.predict_risk", return_value=0.95):
                response = evaluate_rules(request)
        else:
            # For other fixtures, use normal ML evaluation
            if use_ml:
                response = evaluate_rules(request)
            else:
                # Rules only mode
                with patch("orca_core.engine.predict_risk", return_value=0.0):
                    response = evaluate_rules(request)

        # Assert decision
        assert response.decision == expected_decision, (
            f"Expected decision {expected_decision}, got {response.decision} "
            f"for fixture {fixture_name}"
        )

        # Assert expected reasons are present (check for reason codes in full reason strings)
        for expected_reason in expected_reasons:
            reason_found = any(expected_reason in reason for reason in response.reasons)
            assert reason_found, (
                f"Expected reason code '{expected_reason}' not found in {response.reasons} "
                f"for fixture {fixture_name}"
            )

        # Assert expected actions are present
        for expected_action in expected_actions:
            assert expected_action in response.actions, (
                f"Expected action '{expected_action}' not found in {response.actions} "
                f"for fixture {fixture_name}"
            )

        # Additional assertions for specific fixtures
        if fixture_name == "low_ticket_ok.json":
            # Should be approved with loyalty boost
            assert response.decision == "APPROVE"
            assert "LOYALTY_BOOST" in response.actions
            # Should not have any review reasons
            review_reasons = ["HIGH_TICKET", "VELOCITY_FLAG", "LOCATION_MISMATCH", "HIGH_IP_DISTANCE", "CHARGEBACK_HISTORY"]
            for reason in review_reasons:
                assert not any(reason in r for r in response.reasons), f"Unexpected review reason {reason} in approve case"

        elif fixture_name == "high_ticket_review.json":
            # Should be reviewed due to high ticket
            assert response.decision == "REVIEW"
            assert any("HIGH_TICKET" in reason for reason in response.reasons)
            assert "ROUTE_TO_REVIEW" in response.actions

        elif fixture_name == "velocity_review.json":
            # Should be reviewed due to velocity
            assert response.decision == "REVIEW"
            assert any("VELOCITY_FLAG" in reason for reason in response.reasons)
            assert "ROUTE_TO_REVIEW" in response.actions

        elif fixture_name == "location_mismatch_review.json":
            # Should be reviewed due to location mismatch and/or high IP distance
            assert response.decision == "REVIEW"
            assert "ROUTE_TO_REVIEW" in response.actions
            # Should have at least one of these reasons
            location_reasons = ["LOCATION_MISMATCH", "HIGH_IP_DISTANCE"]
            has_location_reason = any(
                any(loc_reason in reason for reason in response.reasons)
                for loc_reason in location_reasons
            )
            assert has_location_reason, f"Expected at least one location reason in {response.reasons}"

        elif fixture_name == "high_risk_decline.json":
            # Should be declined due to high risk (with monkeypatched risk score)
            assert response.decision == "DECLINE"
            assert any("HIGH_RISK" in reason for reason in response.reasons)
            assert "BLOCK" in response.actions
            # Should also have chargeback history reason
            assert any("CHARGEBACK_HISTORY" in reason for reason in response.reasons)

    def test_fixture_files_exist(self, fixtures_dir: Path) -> None:
        """Test that all expected fixture files exist."""
        expected_files = [
            "low_ticket_ok.json",
            "high_ticket_review.json",
            "velocity_review.json",
            "location_mismatch_review.json",
            "high_risk_decline.json"
        ]

        for filename in expected_files:
            file_path = fixtures_dir / filename
            assert file_path.exists(), f"Expected fixture file {filename} not found"

    def test_fixture_files_valid_json(self, fixture_files: list[Path]) -> None:
        """Test that all fixture files contain valid JSON."""
        for fixture_path in fixture_files:
            with open(fixture_path) as f:
                try:
                    data = json.load(f)
                    # Basic validation that it can be converted to DecisionRequest
                    DecisionRequest(**data)
                except (json.JSONDecodeError, Exception) as e:
                    pytest.fail(f"Invalid JSON or DecisionRequest data in {fixture_path.name}: {e}")

    def test_fixture_files_decision_consistency(self, fixtures_dir: Path) -> None:
        """Test that fixture files produce consistent decisions across multiple runs."""
        fixture_files = [
            "low_ticket_ok.json",
            "high_ticket_review.json",
            "velocity_review.json",
            "location_mismatch_review.json"
        ]

        for filename in fixture_files:
            fixture_path = fixtures_dir / filename
            if not fixture_path.exists():
                continue

            with open(fixture_path) as f:
                raw_data = json.load(f)

            request = DecisionRequest(**raw_data)

            # Run multiple times to ensure consistency
            decisions = []
            for _ in range(3):
                response = evaluate_rules(request)
                decisions.append(response.decision)

            # All decisions should be the same
            assert len(set(decisions)) == 1, (
                f"Inconsistent decisions for {filename}: {decisions}"
            )

    def test_high_risk_fixture_without_monkeypatch(self, fixtures_dir: Path) -> None:
        """Test high_risk_decline.json without monkeypatch to see natural behavior."""
        fixture_path = fixtures_dir / "high_risk_decline.json"
        if not fixture_path.exists():
            pytest.skip("high_risk_decline.json not found")

        with open(fixture_path) as f:
            raw_data = json.load(f)

        request = DecisionRequest(**raw_data)
        response = evaluate_rules(request)

        # Without monkeypatch, it should likely be REVIEW due to chargeback history
        # (unless the natural ML risk score is > 0.8)
        assert response.decision in ["REVIEW", "DECLINE"], (
            f"Expected REVIEW or DECLINE, got {response.decision}"
        )
        assert any("CHARGEBACK_HISTORY" in reason for reason in response.reasons)

        # If it's DECLINE, it should have HIGH_RISK reason
        if response.decision == "DECLINE":
            assert any("HIGH_RISK" in reason for reason in response.reasons)
            assert "BLOCK" in response.actions
        else:
            # If REVIEW, should have ROUTE_TO_REVIEW action
            assert "ROUTE_TO_REVIEW" in response.actions

    @pytest.mark.parametrize("fixture_name", [
        "low_ticket_ok.json",
        "high_ticket_review.json",
        "velocity_review.json",
        "location_mismatch_review.json",
        "high_risk_decline.json"
    ])
    def test_fixture_metadata_completeness(self, fixture_name: str, fixtures_dir: Path) -> None:
        """Test that fixture responses have complete metadata."""
        fixture_path = fixtures_dir / fixture_name
        if not fixture_path.exists():
            pytest.skip(f"Fixture file {fixture_name} not found")

        with open(fixture_path) as f:
            raw_data = json.load(f)

        request = DecisionRequest(**raw_data)

        # Use monkeypatch for high_risk_decline to ensure DECLINE
        if fixture_name == "high_risk_decline.json":
            with patch("orca_core.engine.predict_risk", return_value=0.95):
                response = evaluate_rules(request)
        else:
            response = evaluate_rules(request)

        # Check that metadata is present and complete
        assert "risk_score" in response.meta, "Missing risk_score in metadata"
        assert "rules_evaluated" in response.meta, "Missing rules_evaluated in metadata"

        # Risk score should be a float between 0 and 1
        risk_score = response.meta["risk_score"]
        assert isinstance(risk_score, int | float), "Risk score should be numeric"
        assert 0.0 <= risk_score <= 1.0, f"Risk score {risk_score} should be between 0 and 1"

        # Rules evaluated should be a list
        rules_evaluated = response.meta["rules_evaluated"]
        assert isinstance(rules_evaluated, list), "Rules evaluated should be a list"
