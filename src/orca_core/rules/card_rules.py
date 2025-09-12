"""Card-specific rules for Orca Core decision engine."""

from ..models import DecisionRequest
from .base import Rule, RuleResult


class CardHighTicketRule(Rule):
    """Rule that flags high-value Card transactions."""

    def __init__(self, threshold: float = 5000.0):
        """
        Initialize the card high ticket rule.

        Args:
            threshold: The cart total threshold above which to flag Card transactions
        """
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the card high ticket rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if cart_total > threshold for Card rail, None otherwise
        """
        if request.rail != "Card":
            return None

        if request.cart_total > self.threshold:
            return RuleResult(
                decision_hint="DECLINE", reasons=["high_ticket"], actions=["manual_review"]
            )

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "CARD_HIGH_TICKET"


class CardVelocityRule(Rule):
    """Rule that flags high-velocity Card transactions."""

    def __init__(self, threshold: float = 4.0):
        """
        Initialize the card velocity rule.

        Args:
            threshold: The velocity threshold above which to flag Card transactions
        """
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the card velocity rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult if velocity > threshold for Card rail, None otherwise
        """
        if request.rail != "Card":
            return None

        velocity_24h = request.features.get("velocity_24h", 0.0)

        if velocity_24h > self.threshold:
            return RuleResult(
                decision_hint="DECLINE", reasons=["velocity_flag"], actions=["block_transaction"]
            )

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "CARD_VELOCITY"


class CardChannelRule(Rule):
    """Rule that applies different thresholds based on Card channel."""

    def __init__(self) -> None:
        """Initialize the card channel rule."""
        pass

    def apply(self, request: DecisionRequest) -> RuleResult | None:
        """
        Apply the card channel rule.

        Args:
            request: The decision request to evaluate

        Returns:
            RuleResult with channel-specific actions if applicable
        """
        if request.rail != "Card":
            return None

        if request.channel == "online":
            # Online transactions get additional verification
            if request.cart_total > 1000.0:
                return RuleResult(
                    decision_hint="REVIEW",
                    reasons=["online_verification"],
                    actions=["step_up_auth"],
                )
        elif request.channel == "pos":
            # POS transactions are generally more trusted
            return RuleResult(decision_hint=None, reasons=[], actions=["pos_processing"])

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "CARD_CHANNEL"
