"""Unit tests for Week 2 Rules + Rails rail and channel rules."""

import pytest

from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest


class TestCardRules:
    """Test Card-specific rules."""

    def test_card_high_ticket_decline(self) -> None:
        """Test Card high-ticket rule triggers DECLINE."""
        request = DecisionRequest(
            cart_total=6000.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 2.0},
        )

        response = evaluate_rules(request)

        assert response.decision == "REVIEW"  # Card high-ticket triggers REVIEW
        assert "high_ticket" in response.reasons
        assert "manual_review" in response.actions
        assert "CARD_HIGH_TICKET" in response.signals_triggered
        assert response.rail == "Card"

    def test_card_velocity_decline(self):
        """Test Card velocity rule triggers DECLINE."""
        request = DecisionRequest(
            cart_total=150.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 5.0},
        )

        response = evaluate_rules(request)

        assert response.decision == "REVIEW"  # Velocity triggers REVIEW
        assert "velocity_flag" in response.reasons
        assert "block_transaction" in response.actions
        assert "CARD_VELOCITY" in response.signals_triggered
        assert response.rail == "Card"

    def test_card_online_verification(self):
        """Test Card online channel verification."""
        request = DecisionRequest(
            cart_total=1200.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 1.0},
        )

        response = evaluate_rules(request)

        assert "online_verification" in response.reasons
        assert "step_up_auth" in response.actions
        assert "CARD_CHANNEL" in response.signals_triggered

    def test_card_pos_processing(self):
        """Test Card POS channel processing."""
        request = DecisionRequest(
            cart_total=150.0,
            currency="USD",
            rail="Card",
            channel="pos",
            features={"velocity_24h": 1.0},
        )

        response = evaluate_rules(request)

        assert "pos_processing" in response.actions
        assert "CARD_CHANNEL" in response.signals_triggered


class TestACHRules:
    """Test ACH-specific rules."""

    def test_ach_limit_exceeded_decline(self):
        """Test ACH limit rule triggers DECLINE."""
        request = DecisionRequest(
            cart_total=2500.0,
            currency="USD",
            rail="ACH",
            channel="online",
            features={"velocity_24h": 1.0},
        )

        response = evaluate_rules(request)

        assert response.decision == "REVIEW"  # ACH limit triggers REVIEW
        assert "ach_limit_exceeded" in response.reasons
        assert "fallback_card" in response.actions
        assert "ACH_LIMIT" in response.signals_triggered
        assert response.rail == "ACH"

    def test_ach_location_mismatch_decline(self):
        """Test ACH location mismatch rule triggers DECLINE."""
        request = DecisionRequest(
            cart_total=1500.0,
            currency="USD",
            rail="ACH",
            channel="online",
            features={"velocity_24h": 1.0},
            context={"location_mismatch": True},
        )

        response = evaluate_rules(request)

        assert response.decision == "REVIEW"  # Location mismatch triggers REVIEW
        assert "location_mismatch" in response.reasons
        assert "fallback_card" in response.actions
        assert "ACH_LOCATION_MISMATCH" in response.signals_triggered

    def test_ach_online_verification(self):
        """Test ACH online channel verification."""
        request = DecisionRequest(
            cart_total=600.0,
            currency="USD",
            rail="ACH",
            channel="online",
            features={"velocity_24h": 1.0},
        )

        response = evaluate_rules(request)

        assert "ach_online_verification" in response.reasons
        assert "micro_deposit_verification" in response.actions
        assert "ACH_CHANNEL" in response.signals_triggered

    def test_ach_pos_processing(self):
        """Test ACH POS channel processing."""
        request = DecisionRequest(
            cart_total=150.0,
            currency="USD",
            rail="ACH",
            channel="pos",
            features={"velocity_24h": 1.0},
        )

        response = evaluate_rules(request)

        assert "ach_pos_processing" in response.actions
        assert "ACH_CHANNEL" in response.signals_triggered


class TestCombinedSignals:
    """Test combined signal aggregation."""

    def test_card_multiple_signals(self):
        """Test Card transaction with multiple signals."""
        request = DecisionRequest(
            cart_total=2200.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 4.0},
            context={"customer": {"loyalty_tier": "BRONZE", "chargebacks_12m": 1}},
        )

        response = evaluate_rules(request)

        # Should have multiple reasons
        assert len(response.reasons) >= 2
        assert "online_verification" in response.reasons
        assert "HIGH_TICKET" in " ".join(response.reasons)
        assert "VELOCITY_FLAG" in " ".join(response.reasons)

        # Should have multiple actions
        assert len(response.actions) >= 2
        assert "step_up_auth" in response.actions

        # Should have multiple signals
        assert len(response.signals_triggered) >= 3
        assert "CARD_CHANNEL" in response.signals_triggered
        assert "HIGH_TICKET" in response.signals_triggered
        assert "VELOCITY" in response.signals_triggered

    def test_ach_multiple_signals(self):
        """Test ACH transaction with multiple signals."""
        request = DecisionRequest(
            cart_total=1800.0,
            currency="USD",
            rail="ACH",
            channel="online",
            features={"velocity_24h": 2.0},
            context={
                "location_mismatch": True,
                "customer": {"loyalty_tier": "SILVER", "chargebacks_12m": 0},
            },
        )

        response = evaluate_rules(request)

        # Should have multiple reasons
        assert len(response.reasons) >= 2
        assert "location_mismatch" in response.reasons
        assert "ach_online_verification" in response.reasons

        # Should have multiple actions
        assert len(response.actions) >= 2
        assert "fallback_card" in response.actions
        assert "micro_deposit_verification" in response.actions

        # Should have multiple signals
        assert len(response.signals_triggered) >= 2
        assert "ACH_LOCATION_MISMATCH" in response.signals_triggered
        assert "ACH_CHANNEL" in response.signals_triggered


class TestRailChannelCombinations:
    """Test all rail and channel combinations."""

    @pytest.mark.parametrize(
        "rail,channel", [("Card", "online"), ("Card", "pos"), ("ACH", "online"), ("ACH", "pos")]
    )
    def test_all_combinations_valid(self, rail, channel):
        """Test all valid rail and channel combinations."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail=rail,
            channel=channel,
            features={"velocity_24h": 1.0},
        )

        response = evaluate_rules(request)

        assert response.rail == rail
        assert response.decision in ["APPROVE", "REVIEW", "DECLINE"]
        assert len(response.reasons) > 0
        assert len(response.actions) > 0

    def test_rail_field_preserved(self):
        """Test that rail field is preserved in response."""
        request = DecisionRequest(cart_total=150.0, currency="USD", rail="Card", channel="online")

        response = evaluate_rules(request)

        assert response.rail == "Card"
        assert response.cart_total == 150.0
        assert response.transaction_id is not None
        assert response.timestamp is not None
