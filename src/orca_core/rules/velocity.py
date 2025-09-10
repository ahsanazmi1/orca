"""Velocity rule for Orca Core decision engine."""

from ..models import DecisionRequest
from .base import BaseRule


class VelocityRule(BaseRule):
    """Rule that flags high-velocity transactions for review."""

    def __init__(self, threshold: float = 3.0):
        """
        Initialize the velocity rule.

        Args:
            threshold: The velocity threshold above which to flag for review
        """
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> tuple[str, list[str], list[str]] | None:
        """
        Apply the velocity rule.

        Args:
            request: The decision request to evaluate

        Returns:
            Tuple of (decision_hint, reasons, actions) if velocity > threshold,
            None otherwise
        """
        velocity_24h = request.features.get("velocity_24h", 0.0)

        if velocity_24h > self.threshold:
            reasons = [
                f"VELOCITY_FLAG: 24h velocity {velocity_24h} exceeds {self.threshold} threshold"
            ]
            actions = ["ROUTE_TO_REVIEW"]
            return ("REVIEW", reasons, actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "VELOCITY"
