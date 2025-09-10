"""Decision engine for Orca Core."""

from .core.ml_hooks import predict_risk
from .models import DecisionRequest, DecisionResponse
from .rules import HighRiskRule, HighTicketRule, RuleRegistry, VelocityRule

# Global rules registry instance
_rules_registry = RuleRegistry()

# Register default rules
_rules_registry.register(HighTicketRule(threshold=500.0))
_rules_registry.register(VelocityRule(threshold=3.0))
_rules_registry.register(HighRiskRule(threshold=0.80))


def evaluate_rules(request: DecisionRequest) -> DecisionResponse:
    """
    Evaluate decision rules against the request using the rules registry.

    Args:
        request: The decision request to evaluate

    Returns:
        Decision response with decision, reasons, and actions
    """
    # Get risk prediction and add to response
    risk_score = predict_risk(request.features)
    response = _rules_registry.evaluate(request)

    # Always add risk_score to response meta
    response.meta["risk_score"] = risk_score

    return response


def get_rules_registry() -> RuleRegistry:
    """
    Get the global rules registry instance.

    Returns:
        The global rules registry
    """
    return _rules_registry
