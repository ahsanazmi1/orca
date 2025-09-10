"""Rules registry and orchestrator for Orca Core decision engine."""

from ..models import DecisionRequest, DecisionResponse
from .base import BaseRule


class RuleRegistry:
    """Registry and orchestrator for decision rules."""

    def __init__(self):
        """Initialize the rules registry."""
        self.rules: list[BaseRule] = []

    def register(self, rule: BaseRule) -> None:
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
        meta = {"rules_evaluated": []}

        # Track the highest decision level
        decision_level = 0  # 0=APPROVE, 1=REVIEW, 2=DECLINE
        final_decision = "APPROVE"

        # Apply all rules
        for rule in self.rules:
            result = rule.apply(request)
            if result:
                decision_hint, reasons, actions = result
                all_reasons.extend(reasons)
                all_actions.extend(actions)
                meta["rules_evaluated"].append(rule.name)

                # Update decision level based on hint
                if decision_hint == "REVIEW" and decision_level < 1:
                    decision_level = 1
                    final_decision = "REVIEW"
                elif decision_hint == "DECLINE" and decision_level < 2:
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
