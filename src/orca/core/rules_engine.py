"""AP2-compatible rules engine for Orca Core decision engine.

This module provides the rules engine that consumes AP2 mandates and produces
structured decision outcomes with reasons and actions.
"""

from .decision_contract import (
    AP2DecisionContract,
    DecisionAction,
    DecisionOutcome,
    DecisionReason,
    create_decision_action,
    create_decision_reason,
    sign_and_hash_decision,
)
from .feature_extractor import extract_features_from_ap2


class AP2RuleResult:
    """Result of applying a rule to an AP2 decision contract."""

    def __init__(
        self,
        decision_hint: str | None = None,
        reasons: list[DecisionReason] | None = None,
        actions: list[DecisionAction] | None = None,
    ):
        """
        Initialize AP2 rule result.

        Args:
            decision_hint: "REVIEW", "DECLINE", or None for no change
            reasons: List of structured decision reasons
            actions: List of structured decision actions
        """
        self.decision_hint = decision_hint
        self.reasons = reasons or []
        self.actions = actions or []


class AP2Rule:
    """Abstract base class for AP2-compatible decision rules."""

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the rule to an AP2 decision contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult if rule applies, None if rule doesn't apply
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        raise NotImplementedError


class AP2RulesEngine:
    """AP2-compatible rules engine."""

    def __init__(self) -> None:
        """Initialize the AP2 rules engine."""
        self.rules: list[AP2Rule] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register default AP2 rules."""
        from .ap2_rules import (
            AP2AuthRequirementRule,
            AP2ChannelRiskRule,
            AP2GeoRiskRule,
            AP2HighTicketRule,
            AP2LocationMismatchRule,
            AP2PaymentModalityRule,
            AP2VelocityRule,
        )

        self.rules = [
            # High-value transaction rules
            AP2HighTicketRule(threshold=500.0),
            AP2HighTicketRule(threshold=5000.0, rail_specific="Card"),
            # Velocity rules
            AP2VelocityRule(threshold=3.0),
            AP2VelocityRule(threshold=4.0, rail_specific="Card"),
            # Location and geo rules
            AP2LocationMismatchRule(),
            AP2GeoRiskRule(threshold=0.6),
            # Payment-specific rules
            AP2PaymentModalityRule(),
            AP2AuthRequirementRule(),
            # Channel rules
            AP2ChannelRiskRule(),
        ]

    def evaluate(self, ap2_contract: AP2DecisionContract) -> DecisionOutcome:
        """
        Evaluate all rules against an AP2 decision contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            Decision outcome with structured reasons and actions

        Raises:
            ValueError: If AP2 contract is invalid
        """
        # Validate AP2 contract
        self._validate_ap2_contract(ap2_contract)

        # Extract features for rule evaluation
        features = extract_features_from_ap2(ap2_contract)

        # Start with APPROVE decision
        final_decision = "APPROVE"
        all_reasons: list[DecisionReason] = []
        all_actions: list[DecisionAction] = []
        rules_evaluated: list[str] = []

        # Apply all rules
        for rule in self.rules:
            try:
                result = rule.apply(ap2_contract)
                if result:
                    all_reasons.extend(result.reasons)
                    all_actions.extend(result.actions)
                    rules_evaluated.append(rule.name)

                    # Update decision based on rule result
                    if result.decision_hint == "REVIEW" and final_decision == "APPROVE":
                        final_decision = "REVIEW"
                    elif result.decision_hint == "DECLINE":
                        final_decision = "DECLINE"
                        break  # DECLINE is final

            except Exception as e:
                # Log rule evaluation error but continue
                print(f"Warning: Rule {rule.name} failed: {e}")
                continue

        # Calculate risk score from features
        risk_score = self._calculate_risk_score(features, all_reasons)

        # If no rules triggered, provide default approval
        if not all_reasons:
            all_reasons.append(
                create_decision_reason(
                    "high_ticket",  # Using canonical reason code
                    f"Transaction amount ${ap2_contract.cart.amount} within approved threshold",
                )
            )
            all_actions.append(
                create_decision_action("process_payment", detail="Process payment normally")
            )

        # Create decision outcome
        from .decision_contract import DecisionMeta
        from .versioning import get_ml_model_version

        decision_meta = DecisionMeta(
            model="rules_only",
            trace_id=ap2_contract.decision.meta.trace_id,
            version="0.1.0",
            model_version=get_ml_model_version(),
            processing_time_ms=0,  # Default processing time
            model_sha256="",  # Default empty hash
            model_trained_on="",  # Default empty training date
        )

        decision_outcome = DecisionOutcome(
            result=final_decision,
            risk_score=risk_score,
            reasons=all_reasons,
            actions=all_actions,
            meta=decision_meta,
        )

        # Update the contract with the decision outcome
        ap2_contract.decision = decision_outcome

        # Sign and hash the decision if enabled
        signed_contract = sign_and_hash_decision(ap2_contract)

        return signed_contract.decision

    def _validate_ap2_contract(self, ap2_contract: AP2DecisionContract) -> None:
        """
        Validate AP2 contract for rule evaluation.

        Args:
            ap2_contract: AP2 contract to validate

        Raises:
            ValueError: If contract is invalid
        """
        if ap2_contract is None:
            raise ValueError("AP2 contract is required")

        if not ap2_contract.cart:
            raise ValueError("Cart mandate is required")

        if not ap2_contract.payment:
            raise ValueError("Payment mandate is required")

        if not ap2_contract.intent:
            raise ValueError("Intent mandate is required")

        if not ap2_contract.cart.items:
            raise ValueError("Cart must contain at least one item")

        if ap2_contract.cart.amount <= 0:
            raise ValueError("Cart amount must be greater than 0")

    def _calculate_risk_score(
        self, features: dict[str, float], reasons: list[DecisionReason]
    ) -> float:
        """
        Calculate risk score from features and triggered reasons.

        Args:
            features: Extracted features
            reasons: Triggered decision reasons

        Returns:
            Risk score between 0.0 and 1.0
        """
        # Base risk from features
        base_risk = features.get("composite_risk_score", 0.3)

        # Increase risk based on triggered reasons
        risk_multiplier = 1.0
        for reason in reasons:
            if reason.code == "high_ticket":
                risk_multiplier += 0.2
            elif reason.code == "velocity_flag":
                risk_multiplier += 0.3
            elif reason.code == "location_mismatch":
                risk_multiplier += 0.4
            elif reason.code == "high_risk":
                risk_multiplier += 0.5

        # Calculate final risk score
        final_risk = min(base_risk * risk_multiplier, 1.0)
        return final_risk

    def add_rule(self, rule: AP2Rule) -> None:
        """
        Add a custom rule to the engine.

        Args:
            rule: AP2 rule to add
        """
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> None:
        """
        Remove a rule by name.

        Args:
            rule_name: Name of rule to remove
        """
        self.rules = [rule for rule in self.rules if rule.name != rule_name]

    def get_rule_names(self) -> list[str]:
        """
        Get list of registered rule names.

        Returns:
            List of rule names
        """
        return [rule.name for rule in self.rules]


# Global rules engine instance
_rules_engine: AP2RulesEngine | None = None


def get_ap2_rules_engine() -> AP2RulesEngine:
    """Get the global AP2 rules engine instance."""
    global _rules_engine
    if _rules_engine is None:
        _rules_engine = AP2RulesEngine()
    return _rules_engine


def evaluate_ap2_rules(ap2_contract: AP2DecisionContract) -> DecisionOutcome:
    """Evaluate AP2 rules using global rules engine."""
    engine = get_ap2_rules_engine()
    return engine.evaluate(ap2_contract)
