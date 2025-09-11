"""High risk rule for Orca Core decision engine."""


from ..core.ml_hooks import predict_risk
from ..models import DecisionRequest
from .base import Rule, RuleResult


class HighRiskRule(Rule):
    """Rule that uses ML prediction to flag high-risk transactions."""

    def __init__(self, threshold: float = 0.80):
        """
        Initialize the high risk rule.

        Args:
            threshold: The risk score threshold above which to decline
        """
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the high risk rule using ML prediction.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if risk > threshold, None otherwise
        """
        # Get risk prediction from ML model
        risk_score = predict_risk(request.features)

        if risk_score > self.threshold:
            reasons = [
                f"HIGH_RISK: ML risk score {risk_score:.3f} exceeds {self.threshold:.3f} threshold"
            ]
            actions = ["BLOCK"]
            return RuleResult(decision_hint="DECLINE", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "HIGH_RISK"
