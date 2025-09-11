"""Tests for the rules system."""

from orca_core.models import DecisionRequest
from orca_core.rules import HighTicketRule, RuleRegistry, VelocityRule


class TestHighTicketRule:
    """Test cases for HighTicketRule."""

    def test_high_ticket_rule_triggered(self) -> None:
        """Test high ticket rule when cart total exceeds threshold."""
        rule = HighTicketRule(threshold=500.0)
        request = DecisionRequest(cart_total=750.0)

        result = rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert "HIGH_TICKET" in result.reasons[0]
        assert "ROUTE_TO_REVIEW" in result.actions

    def test_high_ticket_rule_not_triggered(self) -> None:
        """Test high ticket rule when cart total is below threshold."""
        rule = HighTicketRule(threshold=500.0)
        request = DecisionRequest(cart_total=250.0)

        result = rule.apply(request)

        assert result is None

    def test_high_ticket_rule_custom_threshold(self) -> None:
        """Test high ticket rule with custom threshold."""
        rule = HighTicketRule(threshold=1000.0)
        request = DecisionRequest(cart_total=750.0)

        result = rule.apply(request)

        assert result is None

    def test_high_ticket_rule_name(self) -> None:
        """Test high ticket rule name property."""
        rule = HighTicketRule()
        assert rule.name == "HIGH_TICKET"


class TestVelocityRule:
    """Test cases for VelocityRule."""

    def test_velocity_rule_triggered(self) -> None:
        """Test velocity rule when velocity exceeds threshold."""
        rule = VelocityRule(threshold=3.0)
        request = DecisionRequest(cart_total=100.0, features={"velocity_24h": 5.0})

        result = rule.apply(request)

        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert "VELOCITY_FLAG" in result.reasons[0]
        assert "ROUTE_TO_REVIEW" in result.actions

    def test_velocity_rule_not_triggered(self) -> None:
        """Test velocity rule when velocity is below threshold."""
        rule = VelocityRule(threshold=3.0)
        request = DecisionRequest(cart_total=100.0, features={"velocity_24h": 2.0})

        result = rule.apply(request)

        assert result is None

    def test_velocity_rule_missing_feature(self) -> None:
        """Test velocity rule when velocity feature is missing."""
        rule = VelocityRule(threshold=3.0)
        request = DecisionRequest(cart_total=100.0)

        result = rule.apply(request)

        assert result is None

    def test_velocity_rule_custom_threshold(self) -> None:
        """Test velocity rule with custom threshold."""
        rule = VelocityRule(threshold=10.0)
        request = DecisionRequest(cart_total=100.0, features={"velocity_24h": 5.0})

        result = rule.apply(request)

        assert result is None

    def test_velocity_rule_name(self) -> None:
        """Test velocity rule name property."""
        rule = VelocityRule()
        assert rule.name == "VELOCITY"


class TestRuleRegistry:
    """Test cases for RuleRegistry."""

    def test_empty_registry(self) -> None:
        """Test registry with no rules."""
        registry = RuleRegistry()
        request = DecisionRequest(cart_total=100.0)

        response = registry.evaluate(request)

        assert response.decision == "APPROVE"
        assert "within approved threshold" in response.reasons[0]
        assert "Process payment" in response.actions

    def test_single_rule_registry(self) -> None:
        """Test registry with single rule."""
        registry = RuleRegistry()
        registry.register(HighTicketRule(threshold=500.0))

        # Test approval case
        request = DecisionRequest(cart_total=250.0)
        response = registry.evaluate(request)

        assert response.decision == "APPROVE"
        assert "within approved threshold" in response.reasons[0]

        # Test review case
        request = DecisionRequest(cart_total=750.0)
        response = registry.evaluate(request)

        assert response.decision == "REVIEW"
        assert "HIGH_TICKET" in response.reasons[0]

    def test_multiple_rules_registry(self) -> None:
        """Test registry with multiple rules."""
        registry = RuleRegistry()
        registry.register(HighTicketRule(threshold=500.0))
        registry.register(VelocityRule(threshold=3.0))

        # Test case where both rules trigger
        request = DecisionRequest(cart_total=750.0, features={"velocity_24h": 5.0})
        response = registry.evaluate(request)

        assert response.decision == "REVIEW"
        assert len(response.reasons) == 2
        assert any("HIGH_TICKET" in reason for reason in response.reasons)
        assert any("VELOCITY_FLAG" in reason for reason in response.reasons)
        assert len(response.actions) == 2
        assert all(action == "ROUTE_TO_REVIEW" for action in response.actions)
        assert len(response.meta["rules_evaluated"]) == 2

    def test_registry_clear(self) -> None:
        """Test clearing the registry."""
        registry = RuleRegistry()
        registry.register(HighTicketRule(threshold=500.0))

        assert registry.get_rule_count() == 1

        registry.clear()

        assert registry.get_rule_count() == 0

    def test_registry_rule_count(self) -> None:
        """Test getting rule count."""
        registry = RuleRegistry()

        assert registry.get_rule_count() == 0

        registry.register(HighTicketRule(threshold=500.0))
        assert registry.get_rule_count() == 1

        registry.register(VelocityRule(threshold=3.0))
        assert registry.get_rule_count() == 2
