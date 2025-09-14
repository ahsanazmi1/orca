"""High ticket rule for Orca Core decision engine."""

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
