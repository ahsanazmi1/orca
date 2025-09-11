"""Velocity rule for Orca Core decision engine."""


from ..models import DecisionRequest
from .base import Rule, RuleResult


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
