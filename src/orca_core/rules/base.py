"""Base rule class for Orca Core decision engine."""

from abc import ABC, abstractmethod

from ..models import DecisionRequest


class BaseRule(ABC):
    """Abstract base class for decision rules."""

    @abstractmethod
    def apply(self, request: DecisionRequest) -> tuple[str, list[str], list[str]] | None:
        """
        Apply the rule to a decision request.

        Args:
            request: The decision request to evaluate

        Returns:
            Optional tuple of (decision_hint, reasons, actions) if rule applies,
            None if rule doesn't apply. Decision hints: "APPROVE", "REVIEW", "DECLINE"
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this rule."""
        pass
