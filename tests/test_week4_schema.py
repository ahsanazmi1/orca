"""Tests for Week 4 schema refinements and meta population."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.orca_core.engine import evaluate_rules
from src.orca_core.models import DecisionMeta, DecisionRequest, DecisionResponse


class TestWeek4Schema:
    """Test Week 4 schema refinements."""

    def test_decision_meta_structure(self):
        """Test that DecisionMeta has all required fields."""
        meta = DecisionMeta(
            timestamp=datetime.now(),
            transaction_id="txn_test123",
            rail="Card",
            channel="online",
            cart_total=150.0,
            risk_score=0.15,
            rules_evaluated=["TEST_RULE"],
            approved_amount=150.0,
        )

        assert meta.timestamp is not None
        assert meta.transaction_id == "txn_test123"
        assert meta.rail == "Card"
        assert meta.channel == "online"
        assert meta.cart_total == 150.0
        assert meta.risk_score == 0.15
        assert meta.rules_evaluated == ["TEST_RULE"]
        assert meta.approved_amount == 150.0

    def test_decision_response_new_schema(self):
        """Test DecisionResponse with new schema structure."""
        meta_structured = DecisionMeta(
            timestamp=datetime.now(),
            transaction_id="txn_test123",
            rail="Card",
            channel="online",
            cart_total=150.0,
            risk_score=0.15,
            rules_evaluated=[],
            approved_amount=150.0,
        )

        meta_legacy = {
            "risk_score": 0.15,
            "rules_evaluated": [],
            "timestamp": meta_structured.timestamp,
            "transaction_id": "txn_test123",
            "rail": "Card",
            "channel": "online",
            "cart_total": 150.0,
            "approved_amount": 150.0,
        }

        response = DecisionResponse(
            decision="APPROVE",  # Legacy field
            reasons=["test_reason"],
            actions=["test_action"],
            meta=meta_legacy,
            status="APPROVE",
            meta_structured=meta_structured,
            signals_triggered=[],
            explanation="Test explanation",
            explanation_human="Test human explanation",
            routing_hint="PROCESS_NORMALLY",
        )

        assert response.status == "APPROVE"
        assert response.reasons == ["test_reason"]
        assert response.actions == ["test_action"]
        assert isinstance(response.meta_structured, DecisionMeta)
        assert response.decision == "APPROVE"  # Legacy compatibility
        assert response.explanation_human == "Test human explanation"

    def test_meta_population_consistency(self):
        """Test that meta is consistently populated by engine."""
        request = DecisionRequest(
            cart_total=150.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 1.0},
            context={"test": "value"},
        )

        response = evaluate_rules(request)

        # Test meta structure
        assert isinstance(response.meta_structured, DecisionMeta)
        assert response.meta_structured.timestamp is not None
        assert response.meta_structured.transaction_id is not None
        assert response.meta_structured.rail == "Card"
        assert response.meta_structured.channel == "online"
        assert response.meta_structured.cart_total == 150.0
        assert isinstance(response.meta_structured.risk_score, float)
        assert isinstance(response.meta_structured.rules_evaluated, list)

        # Test backward compatibility
        assert response.transaction_id == response.meta["transaction_id"]
        assert response.cart_total == response.meta["cart_total"]
        assert response.timestamp == response.meta["timestamp"]
        assert response.rail == response.meta["rail"]

    def test_status_mapping(self):
        """Test that REVIEW maps to ROUTE in new schema."""
        request = DecisionRequest(
            cart_total=2200.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 1.0},
            context={},
        )

        response = evaluate_rules(request)

        # Should be ROUTE in new schema, REVIEW in legacy
        assert response.status == "ROUTE"
        assert response.decision == "REVIEW"

    def test_week4_fixtures_validation(self):
        """Test that all Week 4 fixtures are valid."""
        fixture_dir = Path("fixtures/week4/requests")
        if not fixture_dir.exists():
            pytest.skip("Week 4 fixtures not found")

        for fixture_file in fixture_dir.glob("*.json"):
            with open(fixture_file) as f:
                data = json.load(f)

            # Validate request schema
            request = DecisionRequest(**data)
            assert request.rail in ["Card", "ACH"]
            assert request.channel in ["online", "pos"]
            assert request.cart_total > 0

            # Validate response generation
            response = evaluate_rules(request)
            assert response.status in ["APPROVE", "DECLINE", "ROUTE"]
            assert isinstance(response.meta_structured, DecisionMeta)
            assert response.meta_structured.rail == request.rail
            assert response.meta_structured.channel == request.channel
            assert response.meta_structured.cart_total == request.cart_total

    def test_canonical_reason_codes(self):
        """Test that reasons use canonical codes where possible."""
        # Test high ticket scenario
        request = DecisionRequest(
            cart_total=6000.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 1.0},
            context={},
        )

        response = evaluate_rules(request)

        # Should include canonical reason codes
        assert any("high_ticket" in reason for reason in response.reasons)
        assert any("online_verification" in reason for reason in response.reasons)

    def test_canonical_action_codes(self):
        """Test that actions use canonical codes where possible."""
        # Test high ticket scenario
        request = DecisionRequest(
            cart_total=6000.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 1.0},
            context={},
        )

        response = evaluate_rules(request)

        # Should include canonical action codes
        assert any("manual_review" in action for action in response.actions)
        assert any("step_up_auth" in action for action in response.actions)

    def test_rail_channel_toggles(self):
        """Test that rail and channel toggles work correctly."""
        base_data = {
            "cart_total": 150.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
            "features": {"velocity_24h": 1.0},
            "context": {},
        }

        # Test Card + online
        request1 = DecisionRequest(**base_data)
        response1 = evaluate_rules(request1)
        assert response1.meta_structured.rail == "Card"
        assert response1.meta_structured.channel == "online"

        # Test ACH + pos
        base_data["rail"] = "ACH"
        base_data["channel"] = "pos"
        request2 = DecisionRequest(**base_data)
        response2 = evaluate_rules(request2)
        assert response2.meta_structured.rail == "ACH"
        assert response2.meta_structured.channel == "pos"

    def test_human_explanations_present(self):
        """Test that human explanations are always present."""
        request = DecisionRequest(
            cart_total=150.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 1.0},
            context={},
        )

        response = evaluate_rules(request)

        assert response.explanation_human is not None
        assert len(response.explanation_human) > 0
        assert isinstance(response.explanation_human, str)

    def test_backward_compatibility(self):
        """Test that legacy fields are still populated for backward compatibility."""
        request = DecisionRequest(
            cart_total=150.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 1.0},
            context={},
        )

        response = evaluate_rules(request)

        # Legacy fields should still be present
        assert response.decision is not None
        assert response.transaction_id is not None
        assert response.cart_total is not None
        assert response.timestamp is not None
        assert response.rail is not None

        # Should match new meta fields
        assert response.transaction_id == response.meta["transaction_id"]
        assert response.cart_total == response.meta["cart_total"]
        assert response.timestamp == response.meta["timestamp"]
        assert response.rail == response.meta["rail"]
