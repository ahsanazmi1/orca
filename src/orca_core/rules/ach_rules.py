"""ACH-specific rules for Orca Core decision engine."""

from ..models import DecisionRequest
from .base import Rule, RuleResult


class ACHLimitRule(Rule):
    """Rule that enforces ACH per-transaction limits."""

    def __init__(self, limit: float = 2000.0):
        """
        Initialize the ACH limit rule.

        Args:
            limit: The maximum allowed per-transaction amount for ACH
        """
        self.limit = limit

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the ACH limit rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if cart_total > limit for ACH rail, None otherwise
        """
        if request.rail != "ACH":
            return None

        if request.cart_total > self.limit:
            return RuleResult(
                decision_hint="DECLINE", reasons=["ach_limit_exceeded"], actions=["fallback_card"]
            )

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "ACH_LIMIT"


class ACHLocationMismatchRule(Rule):
    """Rule that handles ACH location mismatches."""

    def __init__(self) -> None:
        """Initialize the ACH location mismatch rule."""
        pass

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the ACH location mismatch rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if location mismatch detected for ACH rail, None otherwise
        """
        if request.rail != "ACH":
            return None

        # Check for location mismatch in context
        location_mismatch = request.context.get("location_mismatch", False)
        ip_country = request.context.get("location_ip_country", "")
        billing_country = request.context.get("billing_country", "")

        if location_mismatch or (ip_country and billing_country and ip_country != billing_country):
            return RuleResult(
                decision_hint="DECLINE", reasons=["location_mismatch"], actions=["fallback_card"]
            )

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "ACH_LOCATION_MISMATCH"


class ACHChannelRule(Rule):
    """Rule that applies different processing based on ACH channel."""

    def __init__(self) -> None:
        """Initialize the ACH channel rule."""
        pass

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the ACH channel rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult with channel-specific actions if applicable
        """
        if request.rail != "ACH":
            return None

        if request.channel == "online":
            # Online ACH transactions require additional verification
            if request.cart_total > 500.0:
                return RuleResult(
                    decision_hint="REVIEW",
                    reasons=["ach_online_verification"],
                    actions=["micro_deposit_verification"],
                )
        elif request.channel == "pos":
            # POS ACH transactions are generally more trusted
            return RuleResult(decision_hint=None, reasons=[], actions=["ach_pos_processing"])

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "ACH_CHANNEL"
