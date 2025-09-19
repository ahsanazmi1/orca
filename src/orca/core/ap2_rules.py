"""AP2-specific rules for Orca Core decision engine.

This module contains rules that operate on AP2 mandates and produce
structured decision outcomes with canonical reason and action codes.
"""

from ..mandates.ap2_types import PaymentModality
from .decision_contract import (
    AP2DecisionContract,
    create_decision_action,
    create_decision_reason,
)
from .rules_engine import AP2Rule, AP2RuleResult


class AP2HighTicketRule(AP2Rule):
    """Rule that flags high-value transactions for review."""

    def __init__(self, threshold: float = 500.0, rail_specific: str | None = None):
        """
        Initialize the AP2 high ticket rule.

        Args:
            threshold: The cart total threshold above which to flag for review
            rail_specific: Specific rail to apply rule to (e.g., "Card", "ACH")
        """
        self.threshold = threshold
        self.rail_specific = rail_specific

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the high ticket rule to AP2 contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult if cart_total > threshold, None otherwise
        """
        # Check rail-specific condition
        if self.rail_specific:
            # Map AP2 payment modality to rail
            rail = self._get_rail_from_modality(ap2_contract.payment.modality)
            if rail != self.rail_specific:
                return None

        # Check amount threshold
        if ap2_contract.cart.amount > self.threshold:
            reasons = [
                create_decision_reason(
                    "high_ticket",
                    f"Transaction amount ${ap2_contract.cart.amount} exceeds ${self.threshold} threshold",
                )
            ]

            # Different actions based on threshold
            if self.threshold >= 5000.0:
                actions = [
                    create_decision_action(
                        "manual_review", detail="High-value transaction requires manual review"
                    )
                ]
            else:
                actions = [
                    create_decision_action("manual_review", detail="Transaction requires review")
                ]

            return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    def _get_rail_from_modality(self, modality: PaymentModality) -> str:
        """Map AP2 payment modality to rail type."""
        modality_to_rail = {
            PaymentModality.IMMEDIATE: "Card",
            PaymentModality.DEFERRED: "ACH",
            PaymentModality.RECURRING: "ACH",
            PaymentModality.INSTALLMENT: "ACH",
        }
        return modality_to_rail.get(modality, "Card")

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        if self.rail_specific:
            return f"HIGH_TICKET_{self.rail_specific.upper()}"
        return "HIGH_TICKET"


class AP2VelocityRule(AP2Rule):
    """Rule that flags high-velocity transactions for review."""

    def __init__(self, threshold: float = 3.0, rail_specific: str | None = None):
        """
        Initialize the AP2 velocity rule.

        Args:
            threshold: The velocity threshold above which to flag for review
            rail_specific: Specific rail to apply rule to
        """
        self.threshold = threshold
        self.rail_specific = rail_specific

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the velocity rule to AP2 contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult if velocity > threshold, None otherwise
        """
        # Check rail-specific condition
        if self.rail_specific:
            rail = self._get_rail_from_modality(ap2_contract.payment.modality)
            if rail != self.rail_specific:
                return None

        # Extract velocity from metadata or use default
        velocity_24h = self._extract_velocity(ap2_contract)

        if velocity_24h > self.threshold:
            reasons = [
                create_decision_reason(
                    "velocity_flag",
                    f"24h velocity {velocity_24h} exceeds {self.threshold} threshold",
                )
            ]

            # Different actions based on threshold
            if self.threshold >= 4.0:
                actions = [
                    create_decision_action("block_transaction", detail="High velocity detected")
                ]
            else:
                actions = [
                    create_decision_action("manual_review", detail="Velocity review required")
                ]

            return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    def _extract_velocity(self, ap2_contract: AP2DecisionContract) -> float:
        """Extract velocity from AP2 contract metadata."""
        # Try to get velocity from metadata
        metadata = ap2_contract.metadata or {}
        velocity = metadata.get("velocity_24h", 1.0)

        # If not in metadata, try to extract from features
        if velocity == 1.0:
            features = metadata.get("features", {})
            velocity = features.get("velocity_24h", 1.0)

        # Handle invalid velocity data gracefully
        try:
            return float(velocity)
        except (ValueError, TypeError):
            return 1.0  # Default velocity

    def _get_rail_from_modality(self, modality: PaymentModality) -> str:
        """Map AP2 payment modality to rail type."""
        modality_to_rail = {
            PaymentModality.IMMEDIATE: "Card",
            PaymentModality.DEFERRED: "ACH",
            PaymentModality.RECURRING: "ACH",
            PaymentModality.INSTALLMENT: "ACH",
        }
        return modality_to_rail.get(modality, "Card")

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        if self.rail_specific:
            return f"VELOCITY_{self.rail_specific.upper()}"
        return "VELOCITY"


class AP2LocationMismatchRule(AP2Rule):
    """Rule that flags transactions with location mismatches for review."""

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the location mismatch rule to AP2 contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult if location mismatch detected, None otherwise
        """
        # Check for location mismatch in metadata
        metadata = ap2_contract.metadata or {}
        location_mismatch = metadata.get("location_mismatch", False)

        # Also check for IP vs billing country mismatch
        ip_country = metadata.get("ip_country")
        billing_country = metadata.get("billing_country")

        if location_mismatch or (ip_country and billing_country and ip_country != billing_country):
            reasons = [
                create_decision_reason(
                    "location_mismatch",
                    f"IP country '{ip_country}' differs from billing country '{billing_country}'",
                )
            ]

            # Different actions based on payment modality
            if ap2_contract.payment.modality == PaymentModality.DEFERRED:
                actions = [
                    create_decision_action(
                        "fallback_card", detail="ACH not available for location mismatch"
                    )
                ]
            else:
                actions = [
                    create_decision_action("manual_review", detail="Location verification required")
                ]

            return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "LOCATION_MISMATCH"


class AP2PaymentModalityRule(AP2Rule):
    """Rule that applies different processing based on payment modality."""

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the payment modality rule to AP2 contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult with modality-specific actions if applicable
        """
        modality = ap2_contract.payment.modality
        amount = ap2_contract.cart.amount

        if modality == PaymentModality.DEFERRED:
            # ACH-specific rules
            if amount > 2000.0:
                reasons = [
                    create_decision_reason(
                        "ach_limit_exceeded",
                        f"ACH transaction amount ${amount} exceeds $2000 limit",
                    )
                ]
                actions = [create_decision_action("fallback_card", detail="ACH limit exceeded")]
                return AP2RuleResult(decision_hint="DECLINE", reasons=reasons, actions=actions)

            # ACH online verification
            if ap2_contract.intent.channel.value == "web" and amount > 500.0:
                reasons = [
                    create_decision_reason(
                        "ach_online_verification",
                        "ACH online transaction requires additional verification",
                    )
                ]
                actions = [
                    create_decision_action(
                        "micro_deposit_verification", detail="ACH verification required"
                    )
                ]
                return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        elif modality == PaymentModality.IMMEDIATE:
            # Card-specific rules
            if ap2_contract.intent.channel.value == "web" and amount > 1000.0:
                reasons = [
                    create_decision_reason(
                        "online_verification",
                        "Online card transaction requires additional verification",
                    )
                ]
                actions = [
                    create_decision_action("step_up_auth", detail="Card verification required")
                ]
                return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "PAYMENT_MODALITY"


class AP2ChannelRiskRule(AP2Rule):
    """Rule that applies different risk levels based on channel."""

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the channel risk rule to AP2 contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult with channel-specific actions if applicable
        """
        channel = ap2_contract.intent.channel.value
        amount = ap2_contract.cart.amount

        if channel == "pos":
            # POS transactions are generally more trusted
            actions = [
                create_decision_action("process_payment", detail="POS transaction processing")
            ]
            return AP2RuleResult(decision_hint=None, reasons=[], actions=actions)

        elif channel == "voice":
            # Voice transactions require additional verification
            if amount > 500.0:
                reasons = [
                    create_decision_reason(
                        "online_verification", "Voice transaction requires additional verification"
                    )
                ]
                actions = [
                    create_decision_action("step_up_auth", detail="Voice verification required")
                ]
                return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "CHANNEL_RISK"


class AP2GeoRiskRule(AP2Rule):
    """Rule that flags transactions from high-risk geographic locations."""

    def __init__(self, threshold: float = 0.6):
        """
        Initialize the AP2 geo risk rule.

        Args:
            threshold: The geo risk threshold above which to flag for review
        """
        self.threshold = threshold

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the geo risk rule to AP2 contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult if geo risk > threshold, None otherwise
        """
        if not ap2_contract.cart.geo:
            return None

        # Extract geo risk from metadata or calculate from country
        metadata = ap2_contract.metadata or {}
        geo_risk = metadata.get("geo_risk_score", 0.3)

        # If not in metadata, use country-based risk
        if geo_risk == 0.3:
            country = ap2_contract.cart.geo.country
            geo_risk = self._get_country_risk(country)

        if geo_risk > self.threshold:
            reasons = [
                create_decision_reason(
                    "high_risk", f"Transaction from high-risk location (risk score: {geo_risk:.2f})"
                )
            ]
            actions = [
                create_decision_action("manual_review", detail="High-risk location review required")
            ]
            return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        return None

    def _get_country_risk(self, country: str) -> float:
        """Get risk score for a country."""
        country_risk_map = {
            "US": 0.1,
            "CA": 0.1,
            "GB": 0.1,
            "DE": 0.1,
            "FR": 0.1,
            "AU": 0.1,
            "JP": 0.2,
            "CN": 0.3,
            "IN": 0.4,
            "BR": 0.3,
            "MX": 0.3,
            "RU": 0.5,
            "NG": 0.6,
            "VE": 0.6,
        }
        return country_risk_map.get(country, 0.4)

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "GEO_RISK"


class AP2AuthRequirementRule(AP2Rule):
    """Rule that applies different processing based on authentication requirements."""

    def apply(self, ap2_contract: AP2DecisionContract) -> AP2RuleResult | None:
        """
        Apply the auth requirement rule to AP2 contract.

        Args:
            ap2_contract: AP2 decision contract to evaluate

        Returns:
            AP2RuleResult with auth-specific actions if applicable
        """
        auth_requirements = ap2_contract.payment.auth_requirements
        amount = ap2_contract.cart.amount

        # High-value transactions require stronger authentication
        if amount > 1000.0:
            if not auth_requirements or "none" in auth_requirements:
                reasons = [
                    create_decision_reason(
                        "online_verification",
                        "High-value transaction requires additional authentication",
                    )
                ]
                actions = [
                    create_decision_action("step_up_auth", detail="Strong authentication required")
                ]
                return AP2RuleResult(decision_hint="REVIEW", reasons=reasons, actions=actions)

        # Biometric authentication gets preference
        if "biometric" in auth_requirements:
            actions = [
                create_decision_action(
                    "process_payment", detail="Biometric authentication verified"
                )
            ]
            return AP2RuleResult(decision_hint=None, reasons=[], actions=actions)

        return None

    @property
    def name(self) -> str:
        """Return the name of this rule."""
        return "AUTH_REQUIREMENT"
