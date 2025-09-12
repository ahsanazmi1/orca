"""Built-in deterministic rules for Orca Core decision engine."""


from ..models import DecisionRequest
from .base import Rule, RuleResult


class HighTicketRule(Rule):
    """Rule that flags high-value transactions for review."""

    def __init__(self, threshold: float = 500.0):
        """
        Initialize the high ticket rule.

        Args:
            threshold: The cart total threshold above which to flag for review
        """
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the high ticket rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if cart_total > threshold, None otherwise
        """
        if request.cart_total > self.threshold:
            reasons = [
                f"HIGH_TICKET: Cart total ${request.cart_total:.2f} exceeds ${self.threshold:.2f} threshold"
            ]
            actions = ["ROUTE_TO_REVIEW"]
            return RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "HIGH_TICKET"


class VelocityRule(Rule):
    """Rule that flags high-velocity transactions for review."""

    def __init__(self, threshold: float = 3.0):
        """
        Initialize the velocity rule.

        Args:
            threshold: The velocity threshold above which to flag for review
        """
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the velocity rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if velocity > threshold, None otherwise
        """
        velocity_24h = request.features.get("velocity_24h", 0.0)

        if velocity_24h > self.threshold:
            reasons = [
                f"VELOCITY_FLAG: 24h velocity {velocity_24h} exceeds {self.threshold} threshold"
            ]
            actions = ["ROUTE_TO_REVIEW"]
            return RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "VELOCITY"


class LocationMismatchRule(Rule):
    """Rule that flags transactions with location mismatches for review."""

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the location mismatch rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if location mismatch detected, None otherwise
        """
        context = request.context
        location_ip_country = context.get("location_ip_country")
        billing_country = context.get("billing_country")

        if location_ip_country and billing_country and location_ip_country != billing_country:
            reasons = [
                f"LOCATION_MISMATCH: IP country '{location_ip_country}' differs from billing country '{billing_country}'"
            ]
            actions = ["ROUTE_TO_REVIEW"]
            return RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "LOCATION_MISMATCH"


class HighIpDistanceRule(Rule):
    """Rule that flags transactions with high IP distance for review."""

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the high IP distance rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if high IP distance detected, None otherwise
        """
        high_ip_distance = request.features.get("high_ip_distance", False)

        if high_ip_distance:
            reasons = ["HIGH_IP_DISTANCE: Transaction originates from high-risk IP distance"]
            actions = ["ROUTE_TO_REVIEW"]
            return RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "HIGH_IP_DISTANCE"


class ChargebackHistoryRule(Rule):
    """Rule that flags transactions from customers with chargeback history for review."""

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the chargeback history rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if chargeback history detected, None otherwise
        """
        context = request.context
        customer = context.get("customer", {})
        chargebacks_12m = customer.get("chargebacks_12m", 0)

        if chargebacks_12m > 0:
            reasons = [
                f"CHARGEBACK_HISTORY: Customer has {chargebacks_12m} chargeback(s) in last 12 months"
            ]
            actions = ["ROUTE_TO_REVIEW"]
            return RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "CHARGEBACK_HISTORY"


class LoyaltyBoostRule(Rule):
    """Rule that provides loyalty boost actions for premium customers."""

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the loyalty boost rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult with loyalty boost actions if customer is premium, None otherwise
        """
        context = request.context
        customer = context.get("customer", {})
        loyalty_tier = customer.get("loyalty_tier")

        if loyalty_tier in {"GOLD", "PLATINUM"}:
            reasons = [f"LOYALTY_BOOST: Customer has {loyalty_tier} loyalty tier"]
            actions = ["LOYALTY_BOOST"]
            # Note: This rule doesn't change decision_hint, only adds actions
            return RuleResult(decision_hint=None, reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "LOYALTY_BOOST"


class ItemCountRule(Rule):
    """Rule that flags transactions with high item counts for review."""

    def __init__(self, threshold: int = 10):
        """
        Initialize the item count rule.

        Args:
            threshold: The item count threshold above which to flag for review
        """
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the item count rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if item count > threshold, None otherwise
        """
        item_count = request.context.get("item_count", 1)

        if item_count > self.threshold:
            return RuleResult(
                decision_hint="REVIEW",
                reasons=[
                    f"ITEM_COUNT: Cart has {item_count} items, exceeds {self.threshold} threshold"
                ],
                actions=["ROUTE_TO_REVIEW"],
            )

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "ITEM_COUNT"
