"""Rules registry and orchestrator for Orca Core decision engine."""


from ..models import DecisionRequest, DecisionResponse
from .base import Rule


def rules() -> list[Rule]:
    """
    Return an ordered list of rule instances.

    Returns:
        Ordered list of rule instances for deterministic evaluation
    """
    from .builtins import (
        ChargebackHistoryRule,
        HighIpDistanceRule,
        HighTicketRule,
        LocationMismatchRule,
        LoyaltyBoostRule,
        VelocityRule,
    )

    return [
        HighTicketRule(threshold=500.0),
        VelocityRule(threshold=3.0),
        LocationMismatchRule(),
        HighIpDistanceRule(),
        ChargebackHistoryRule(),
        LoyaltyBoostRule(),
    ]


def run_rules(request: DecisionRequest) -> tuple[str, list[str], list[str], list[str]]:
    """
    Run all rules against a request and aggregate results.

    Args:
        request: The decision request to evaluate

    Returns:
        Tuple of (decision_hint, reasons, actions, rules_evaluated)
        - decision_hint: "REVIEW" if any rule hints REVIEW, None otherwise
        - reasons: List of all reason strings from triggered rules
        - actions: List of all action strings from triggered rules
        - rules_evaluated: List of rule names that were triggered
    """
    all_reasons: list[str] = []
    all_actions: list[str] = []
    rules_evaluated: list[str] = []
    decision_hint: str | None = None

    # Apply all rules in order
    for rule in rules():
        result = rule.apply(request)
        if result:
            all_reasons.extend(result.reasons)
            all_actions.extend(result.actions)
            rules_evaluated.append(rule.name)

            # If any rule hints REVIEW, set decision_hint to REVIEW
            if result.decision_hint == "REVIEW":
                decision_hint = "REVIEW"

    return decision_hint or "APPROVE", all_reasons, all_actions, rules_evaluated


class RuleRegistry:
    """Registry and orchestrator for decision rules."""

    def __init__(self) -> None:
        """Initialize the rules registry."""
        self.rules: list[Rule] = []

    def register(self, rule: Rule) -> None:
        """
        Register a rule with the registry.

        Args:
            rule: The rule to register
        """
        self.rules.append(rule)

    def evaluate(self, request: DecisionRequest) -> DecisionResponse:
        """
        Evaluate all registered rules against a request.

        Args:
            request: The decision request to evaluate

        Returns:
            Decision response with aggregated results
        """
        all_reasons: list[str] = []
        all_actions: list[str] = []
        meta: dict[str, list[str] | float] = {"rules_evaluated": []}

        # Track the highest decision level
        decision_level = 0  # 0=APPROVE, 1=REVIEW, 2=DECLINE
        final_decision = "APPROVE"

        # Apply all rules
        for rule in self.rules:
            result = rule.apply(request)
            if result:
                all_reasons.extend(result.reasons)
                all_actions.extend(result.actions)
                if isinstance(meta["rules_evaluated"], list):
                    meta["rules_evaluated"].append(rule.name)

                # Update decision level based on hint
                if result.decision_hint == "REVIEW" and decision_level < 1:
                    decision_level = 1
                    final_decision = "REVIEW"
                elif result.decision_hint == "DECLINE" and decision_level < 2:
                    decision_level = 2
                    final_decision = "DECLINE"

        # If no rules triggered, provide default approval reasoning
        if not all_reasons:
            all_reasons.append(f"Cart total ${request.cart_total:.2f} within approved threshold")
            all_actions.append("Process payment")
            all_actions.append("Send confirmation")
            meta["approved_amount"] = request.cart_total

        return DecisionResponse(
            decision=final_decision, reasons=all_reasons, actions=all_actions, meta=meta
        )

    def clear(self) -> None:
        """Clear all registered rules."""
        self.rules.clear()

    def get_rule_count(self) -> int:
        """Get the number of registered rules."""
        return len(self.rules)
