"""Tests for individual rule modules."""

from src.orca_core.models import DecisionRequest
from src.orca_core.rules.high_ticket import HighTicketRule
from src.orca_core.rules.velocity import VelocityRule


class TestHighTicketRule:
    """Test the HighTicketRule class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rule = HighTicketRule(threshold=500.0)

    def test_high_ticket_rule_triggered(self):
        """Test that high ticket rule triggers for amounts above threshold."""
        request = DecisionRequest(cart_total=750.0, currency="USD")
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert "HIGH_TICKET" in result.reasons[0]
        assert "750.00" in result.reasons[0]
        assert "500.00" in result.reasons[0]
        assert result.actions == ["ROUTE_TO_REVIEW"]

    def test_high_ticket_rule_not_triggered(self):
        """Test that high ticket rule doesn't trigger for amounts below threshold."""
        request = DecisionRequest(cart_total=250.0, currency="USD")
        result = self.rule.apply(request)

        assert result is None

    def test_high_ticket_rule_exact_threshold(self):
        """Test that high ticket rule doesn't trigger for exact threshold amount."""
        request = DecisionRequest(cart_total=500.0, currency="USD")
        result = self.rule.apply(request)

        assert result is None

    def test_high_ticket_rule_custom_threshold(self):
        """Test high ticket rule with custom threshold."""
        custom_rule = HighTicketRule(threshold=1000.0)

        # Should not trigger at 750
        request = DecisionRequest(cart_total=750.0, currency="USD")
        result = custom_rule.apply(request)
        assert result is None

        # Should trigger at 1200
        request = DecisionRequest(cart_total=1200.0, currency="USD")
        result = custom_rule.apply(request)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert "1200.00" in result.reasons[0]
        assert "1000.00" in result.reasons[0]

    def test_high_ticket_rule_name(self):
        """Test that the rule has the correct name."""
        assert self.rule.name == "HIGH_TICKET"

    def test_high_ticket_rule_with_different_currencies(self):
        """Test that high ticket rule works with different currencies."""
        request = DecisionRequest(cart_total=750.0, currency="EUR")
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"

    def test_high_ticket_rule_with_features(self):
        """Test that high ticket rule works with additional features."""
        request = DecisionRequest(
            cart_total=750.0, currency="USD", features={"velocity_24h": 2.0, "user_age": 25}
        )
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"

    def test_high_ticket_rule_with_context(self):
        """Test that high ticket rule works with additional context."""
        request = DecisionRequest(
            cart_total=750.0,
            currency="USD",
            context={"user_id": "test_user", "ip_address": "192.168.1.1"},
        )
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"


class TestVelocityRule:
    """Test the VelocityRule class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rule = VelocityRule(threshold=3.0)

    def test_velocity_rule_triggered(self):
        """Test that velocity rule triggers for velocity above threshold."""
        request = DecisionRequest(cart_total=100.0, currency="USD", features={"velocity_24h": 5.0})
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert "VELOCITY_FLAG" in result.reasons[0]
        assert "5.0" in result.reasons[0]
        assert "3.0" in result.reasons[0]
        assert result.actions == ["ROUTE_TO_REVIEW"]

    def test_velocity_rule_not_triggered(self):
        """Test that velocity rule doesn't trigger for velocity below threshold."""
        request = DecisionRequest(cart_total=100.0, currency="USD", features={"velocity_24h": 2.0})
        result = self.rule.apply(request)

        assert result is None

    def test_velocity_rule_exact_threshold(self):
        """Test that velocity rule doesn't trigger for exact threshold velocity."""
        request = DecisionRequest(cart_total=100.0, currency="USD", features={"velocity_24h": 3.0})
        result = self.rule.apply(request)

        assert result is None

    def test_velocity_rule_no_velocity_feature(self):
        """Test that velocity rule doesn't trigger when velocity feature is missing."""
        request = DecisionRequest(cart_total=100.0, currency="USD")
        result = self.rule.apply(request)

        assert result is None

    def test_velocity_rule_zero_velocity(self):
        """Test that velocity rule doesn't trigger for zero velocity."""
        request = DecisionRequest(cart_total=100.0, currency="USD", features={"velocity_24h": 0.0})
        result = self.rule.apply(request)

        assert result is None

    def test_velocity_rule_custom_threshold(self):
        """Test velocity rule with custom threshold."""
        custom_rule = VelocityRule(threshold=5.0)

        # Should not trigger at 4.0
        request = DecisionRequest(cart_total=100.0, currency="USD", features={"velocity_24h": 4.0})
        result = custom_rule.apply(request)
        assert result is None

        # Should trigger at 6.0
        request = DecisionRequest(cart_total=100.0, currency="USD", features={"velocity_24h": 6.0})
        result = custom_rule.apply(request)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert "6.0" in result.reasons[0]
        assert "5.0" in result.reasons[0]

    def test_velocity_rule_name(self):
        """Test that the rule has the correct name."""
        assert self.rule.name == "VELOCITY"

    def test_velocity_rule_with_multiple_features(self):
        """Test that velocity rule works with multiple features."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            features={"velocity_24h": 5.0, "velocity_7d": 15.0, "user_age": 25},
        )
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"

    def test_velocity_rule_with_context(self):
        """Test that velocity rule works with additional context."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            features={"velocity_24h": 5.0},
            context={"user_id": "test_user", "ip_address": "192.168.1.1"},
        )
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"

    def test_velocity_rule_negative_velocity(self):
        """Test that velocity rule handles negative velocity gracefully."""
        request = DecisionRequest(cart_total=100.0, currency="USD", features={"velocity_24h": -1.0})
        result = self.rule.apply(request)

        assert result is None

    def test_velocity_rule_very_high_velocity(self):
        """Test that velocity rule handles very high velocity values."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", features={"velocity_24h": 100.0}
        )
        result = self.rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert "100.0" in result.reasons[0]

    def test_velocity_rule_different_rail_types(self):
        """Test that velocity rule works with different rail types."""
        # Test with Card rail
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", features={"velocity_24h": 5.0}
        )
        result = self.rule.apply(request)
        assert result is not None

        # Test with ACH rail
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="ACH", features={"velocity_24h": 5.0}
        )
        result = self.rule.apply(request)
        assert result is not None

    def test_velocity_rule_different_channels(self):
        """Test that velocity rule works with different channels."""
        # Test with online channel
        request = DecisionRequest(
            cart_total=100.0, currency="USD", channel="online", features={"velocity_24h": 5.0}
        )
        result = self.rule.apply(request)
        assert result is not None

        # Test with pos channel
        request = DecisionRequest(
            cart_total=100.0, currency="USD", channel="pos", features={"velocity_24h": 5.0}
        )
        result = self.rule.apply(request)
        assert result is not None
