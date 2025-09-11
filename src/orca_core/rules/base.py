"""Base rule class for Orca Core decision engine."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..models import DecisionRequest


@dataclass
class RuleResult:
    """Result of applying a rule to a decision request."""

    decision_hint: str | None  # "REVIEW", "DECLINE", or None for no change
    reasons: list[str]  # List of reason strings
    actions: list[str]  # List of action strings


class Rule(ABC):
    """Abstract base class for decision rules."""

    @abstractmethod
    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the rule to a decision request.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if rule applies, None if rule doesn't apply.
            Decision hints: "REVIEW", "DECLINE", or None for no change
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this rule."""
        pass


# Backward compatibility alias
BaseRule = Rule
