"""Legacy decision adapter for backward compatibility.

This module provides adapters to convert between AP2-wrapped decision contracts
and legacy decision request/response formats for backward compatibility.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from ..mandates.ap2_types import (
    ActorType,
    AgentPresence,
    AuthRequirement,
    CartItem,
    CartMandate,
    IntentMandate,
    IntentType,
    PaymentMandate,
    PaymentModality,
)
from ..mandates.ap2_types import (
    ChannelType as AP2ChannelType,
)
from .decision_contract import (
    AP2DecisionContract,
    DecisionAction,
    DecisionMeta,
    DecisionOutcome,
    DecisionReason,
    LegacyDecisionRequest,
    LegacyDecisionResponse,
)


class DecisionLegacyAdapter:
    """Adapter for converting between AP2 and legacy decision formats."""

    @staticmethod
    def legacy_request_to_ap2_contract(
        legacy_request: LegacyDecisionRequest | dict[str, Any],
    ) -> AP2DecisionContract:
        """Convert legacy decision request to AP2 decision contract."""

        if isinstance(legacy_request, dict):
            legacy_request = LegacyDecisionRequest(**legacy_request)

        # Create intent mandate from legacy request
        intent = IntentMandate(
            actor=ActorType.HUMAN,  # Default assumption
            intent_type=IntentType.PURCHASE,  # Default assumption
            channel=_map_legacy_channel_to_ap2(legacy_request.channel),
            agent_presence=AgentPresence.NONE,  # Default assumption
            timestamps={
                "created": datetime.now(UTC),
                "expires": datetime.now(UTC).replace(hour=23, minute=59, second=59),
            },
            metadata={},  # Default empty metadata
        )

        # Create cart mandate from legacy request
        cart_items = [
            CartItem(
                id="legacy_item_1",
                name="Legacy Cart Item",
                quantity=1,
                unit_price=Decimal(str(legacy_request.cart_total)),
                total_price=Decimal(str(legacy_request.cart_total)),
                description="Legacy item from legacy request",
                category="general",
                sku="legacy_001",
            )
        ]

        cart = CartMandate(
            items=cart_items,
            amount=Decimal(str(legacy_request.cart_total)),
            currency=legacy_request.currency,
            mcc="0000",  # Default MCC
            geo=None,  # No geo information in legacy
            metadata={},  # Default empty metadata
        )

        # Create payment mandate from legacy request
        payment = PaymentMandate(
            instrument_ref=f"legacy_{uuid4().hex[:8]}",
            modality=_map_legacy_rail_to_modality(legacy_request.rail),
            auth_requirements=[AuthRequirement.NONE],  # Default assumption
            instrument_token=None,  # No token in legacy
            constraints={},  # Default empty constraints
            metadata={},  # Default empty metadata
        )

        # Create default decision outcome (will be filled by decision engine)
        decision_outcome = DecisionOutcome(
            result="APPROVE",  # Default, will be overridden
            risk_score=0.0,  # Default, will be calculated
            reasons=[],
            actions=[],
            meta=DecisionMeta(
                model="rules_only",  # Use valid model type
                trace_id=str(uuid4()),
                version="0.1.0",
                processing_time_ms=0,  # Default processing time
                model_version="0.1.0",  # Default model version
                model_sha256="",  # Default empty hash
                model_trained_on="",  # Default empty training date
            ),
        )

        return AP2DecisionContract(
            ap2_version="0.1.0",
            intent=intent,
            cart=cart,
            payment=payment,
            decision=decision_outcome,
            metadata={
                "legacy_request": legacy_request.model_dump(),
                "conversion_timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @staticmethod
    def ap2_contract_to_legacy_response(
        ap2_contract: AP2DecisionContract,
        include_enhanced_fields: bool = True,
    ) -> LegacyDecisionResponse:
        """Convert AP2 decision contract to legacy decision response."""

        # Map AP2 decision result to legacy decision string
        legacy_decision = _map_ap2_result_to_legacy(ap2_contract.decision.result)

        # Extract reasons as strings
        legacy_reasons = [str(reason.code) for reason in ap2_contract.decision.reasons]

        # Extract actions as strings
        legacy_actions = [str(action.type) for action in ap2_contract.decision.actions]

        # Build legacy metadata
        legacy_meta = {
            "timestamp": datetime.now(UTC).isoformat(),
            "transaction_id": ap2_contract.decision.meta.trace_id,
            "rail": _map_ap2_modality_to_legacy_rail(ap2_contract.payment.modality),
            "channel": _map_ap2_channel_to_legacy(ap2_contract.intent.channel),
            "cart_total": float(ap2_contract.cart.amount),
            "risk_score": ap2_contract.decision.risk_score,
            "rules_evaluated": [reason.code for reason in ap2_contract.decision.reasons],
            "ap2_version": ap2_contract.ap2_version,
        }

        # Add approved amount if decision is APPROVE
        if ap2_contract.decision.result == "APPROVE":
            legacy_meta["approved_amount"] = float(ap2_contract.cart.amount)

        response = LegacyDecisionResponse(
            decision=legacy_decision,
            reasons=legacy_reasons,
            actions=legacy_actions,
            meta=legacy_meta,
            explanation="",  # Default empty explanation
            explanation_human="",  # Default empty human explanation
            routing_hint="",  # Default empty routing hint
        )

        # Add enhanced fields if requested
        if include_enhanced_fields:
            response.signals_triggered = [reason.code for reason in ap2_contract.decision.reasons]
            response.explanation = _generate_legacy_explanation(ap2_contract)
            response.explanation_human = _generate_human_explanation(ap2_contract)
            response.routing_hint = _generate_routing_hint(ap2_contract)

        return response

    @staticmethod
    def update_ap2_contract_with_legacy_response(
        ap2_contract: AP2DecisionContract,
        legacy_response: LegacyDecisionResponse | dict[str, Any],
    ) -> AP2DecisionContract:
        """Update AP2 contract with decision results from legacy response."""

        if isinstance(legacy_response, dict):
            legacy_response = LegacyDecisionResponse(**legacy_response)

        # Map legacy decision to AP2 result
        ap2_result = _map_legacy_to_ap2_result(legacy_response.decision)

        # Convert legacy reasons to AP2 reasons
        ap2_reasons = [
            DecisionReason(code=reason, detail=f"Legacy reason: {reason}")  # type: ignore[arg-type]
            for reason in legacy_response.reasons
        ]

        # Convert legacy actions to AP2 actions
        ap2_actions = [
            DecisionAction(type=action, detail=f"Legacy action: {action}", to="")  # type: ignore[arg-type]
            for action in legacy_response.actions
        ]

        # Extract risk score from legacy metadata
        risk_score = legacy_response.meta.get("risk_score", 0.0)

        # Update the decision outcome
        ap2_contract.decision.result = ap2_result  # type: ignore[assignment]
        ap2_contract.decision.risk_score = risk_score
        ap2_contract.decision.reasons = ap2_reasons
        ap2_contract.decision.actions = ap2_actions

        # Update metadata
        if ap2_contract.metadata is None:
            ap2_contract.metadata = {}
        ap2_contract.metadata["legacy_response"] = legacy_response.model_dump()
        ap2_contract.metadata["updated_timestamp"] = datetime.now(UTC).isoformat()

        return ap2_contract


# Helper functions for mapping between formats
def _map_legacy_channel_to_ap2(legacy_channel: str) -> AP2ChannelType:
    """Map legacy channel to AP2 channel type."""
    mapping = {
        "online": AP2ChannelType.WEB,
        "pos": AP2ChannelType.POS,
    }
    return mapping.get(legacy_channel, AP2ChannelType.WEB)


def _map_ap2_channel_to_legacy(ap2_channel: AP2ChannelType) -> str:
    """Map AP2 channel type to legacy channel."""
    mapping = {
        AP2ChannelType.WEB: "online",
        AP2ChannelType.MOBILE: "online",
        AP2ChannelType.API: "online",
        AP2ChannelType.VOICE: "online",
        AP2ChannelType.CHAT: "online",
        AP2ChannelType.POS: "pos",
    }
    return mapping.get(ap2_channel, "online")


def _map_legacy_rail_to_modality(legacy_rail: str) -> PaymentModality:
    """Map legacy rail to AP2 payment modality."""
    mapping = {
        "Card": PaymentModality.IMMEDIATE,
        "ACH": PaymentModality.DEFERRED,
    }
    return mapping.get(legacy_rail, PaymentModality.IMMEDIATE)


def _map_ap2_modality_to_legacy_rail(ap2_modality: PaymentModality) -> str:
    """Map AP2 payment modality to legacy rail."""
    mapping = {
        PaymentModality.IMMEDIATE: "Card",
        PaymentModality.DEFERRED: "ACH",
        PaymentModality.RECURRING: "ACH",
        PaymentModality.INSTALLMENT: "ACH",
    }
    return mapping.get(ap2_modality, "Card")


def _map_ap2_result_to_legacy(ap2_result: str) -> str:
    """Map AP2 decision result to legacy decision string."""
    mapping = {
        "APPROVE": "APPROVE",
        "REVIEW": "REVIEW",
        "DECLINE": "DECLINE",
    }
    return mapping.get(ap2_result, "REVIEW")


def _map_legacy_to_ap2_result(legacy_decision: str) -> str:
    """Map legacy decision string to AP2 decision result."""
    mapping = {
        "APPROVE": "APPROVE",
        "REVIEW": "REVIEW",
        "DECLINE": "DECLINE",
    }
    return mapping.get(legacy_decision, "REVIEW")


def _generate_legacy_explanation(ap2_contract: AP2DecisionContract) -> str:
    """Generate legacy-style explanation from AP2 contract."""
    result = ap2_contract.decision.result
    reasons = [reason.code for reason in ap2_contract.decision.reasons]

    if result == "APPROVE":
        return f"Transaction approved. Risk score: {ap2_contract.decision.risk_score:.3f}"
    elif result == "REVIEW":
        return f"Transaction requires review. Reasons: {', '.join(reasons)}"
    else:  # DECLINE
        return f"Transaction declined. Reasons: {', '.join(reasons)}"


def _generate_human_explanation(ap2_contract: AP2DecisionContract) -> str:
    """Generate human-readable explanation from AP2 contract."""
    result = ap2_contract.decision.result
    amount = ap2_contract.cart.amount
    currency = ap2_contract.cart.currency

    if result == "APPROVE":
        return f"Your {currency} {amount} transaction has been approved and will be processed."
    elif result == "REVIEW":
        return f"Your {currency} {amount} transaction requires additional review before processing."
    else:  # DECLINE
        return f"Your {currency} {amount} transaction could not be processed at this time."


def _generate_routing_hint(ap2_contract: AP2DecisionContract) -> str | None:
    """Generate routing hint from AP2 contract."""
    actions = [action.type for action in ap2_contract.decision.actions]

    if "manual_review" in actions:
        return "ROUTE_TO_REVIEW"
    elif "fallback_card" in actions:
        return "ROUTE_TO_CARD"
    elif "process_payment" in actions:
        return "PROCESS_NORMALLY"
    else:
        return None


# Convenience functions for JSON conversion
def legacy_request_json_to_ap2_contract(json_str: str) -> AP2DecisionContract:
    """Convert legacy request JSON to AP2 contract."""
    legacy_data = json.loads(json_str)
    return DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_data)


def ap2_contract_to_legacy_response_json(
    ap2_contract: AP2DecisionContract,
    include_enhanced_fields: bool = True,
) -> str:
    """Convert AP2 contract to legacy response JSON."""
    legacy_response = DecisionLegacyAdapter.ap2_contract_to_legacy_response(
        ap2_contract, include_enhanced_fields
    )
    return legacy_response.model_dump_json()


def roundtrip_legacy_to_ap2_to_legacy(
    legacy_request_json: str,
    legacy_response_json: str,
) -> str:
    """Round-trip conversion: legacy request -> AP2 -> legacy response."""
    # Convert legacy request to AP2
    ap2_contract = legacy_request_json_to_ap2_contract(legacy_request_json)

    # Update AP2 with legacy response
    legacy_response = json.loads(legacy_response_json)
    updated_ap2 = DecisionLegacyAdapter.update_ap2_contract_with_legacy_response(
        ap2_contract, legacy_response
    )

    # Convert back to legacy response
    return ap2_contract_to_legacy_response_json(updated_ap2)
