"""AP2-wrapped decision contract for Orca Core.

This module defines the AP2-compliant decision contract that wraps Orca's
decision engine with AP2 intent, cart, and payment mandates.
"""

import os
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ..mandates.ap2_types import CartMandate, IntentMandate, PaymentMandate

# Define valid decision results
DecisionResult = Literal["APPROVE", "REVIEW", "DECLINE"]

# Define canonical reason codes
ReasonCode = Literal[
    "high_ticket",
    "velocity_flag",
    "ach_limit_exceeded",
    "location_mismatch",
    "online_verification",
    "ach_online_verification",
    "chargeback_history",
    "high_risk",
]

# Define canonical action codes
ActionCode = Literal[
    "manual_review",
    "step_up_auth",
    "fallback_card",
    "block_transaction",
    "micro_deposit_verification",
    "process_payment",
    "send_confirmation",
]

# Define model types
ModelType = Literal["xgb_stub", "rules_only", "ml_ensemble"]


class DecisionReason(BaseModel):
    """Structured decision reason with code and detail."""

    code: ReasonCode = Field(..., description="Canonical reason code")
    detail: str = Field(..., description="Human-readable detail")


class DecisionAction(BaseModel):
    """Structured decision action with type and target."""

    type: ActionCode = Field(..., description="Canonical action code")
    to: str | None = Field(None, description="Target for routing actions")
    detail: str | None = Field(None, description="Additional action detail")


class DecisionMeta(BaseModel):
    """Decision metadata and trace information."""

    model: ModelType = Field(..., description="Model used for decision")
    trace_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique trace identifier"
    )
    processing_time_ms: float | None = Field(None, description="Processing time in milliseconds")
    version: str = Field(default="0.1.0", description="Decision engine version")
    model_version: str | None = Field(None, description="ML model version used for decision")
    model_sha256: str | None = Field(None, description="ML model SHA256 hash")
    model_trained_on: str | None = Field(None, description="ML model training date")


class DecisionOutcome(BaseModel):
    """Core decision outcome with structured reasons and actions."""

    result: DecisionResult = Field(..., description="Decision result")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0.0-1.0)")
    reasons: list[DecisionReason] = Field(default_factory=list, description="Decision reasons")
    actions: list[DecisionAction] = Field(default_factory=list, description="Recommended actions")
    meta: DecisionMeta = Field(..., description="Decision metadata")


class SigningInfo(BaseModel):
    """Signing and receipt information for AP2 compliance."""

    vc_proof: dict[str, Any] | None = Field(None, description="Verifiable credential proof")
    receipt_hash: str | None = Field(None, description="Receipt hash for audit trail")


class AP2DecisionContract(BaseModel):
    """AP2-wrapped decision contract - the complete decision structure."""

    # AP2 version and mandates
    ap2_version: str = Field(default="0.1.0", description="AP2 protocol version")
    intent: IntentMandate = Field(..., description="AP2 intent mandate")
    cart: CartMandate = Field(..., description="AP2 cart mandate")
    payment: PaymentMandate = Field(..., description="AP2 payment mandate")

    # Decision outcome
    decision: DecisionOutcome = Field(..., description="Decision outcome and metadata")

    # Signing and compliance
    signing: SigningInfo = Field(
        default_factory=lambda: SigningInfo(vc_proof=None, receipt_hash=None),
        description="Signing and receipt info",
    )

    # Additional metadata
    metadata: dict[str, Any] | None = Field(None, description="Additional contract metadata")


# Legacy decision models for backward compatibility
class LegacyDecisionRequest(BaseModel):
    """Legacy decision request format for backward compatibility."""

    cart_total: float = Field(..., description="Total cart value", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    rail: Literal["Card", "ACH"] = Field(default="Card", description="Payment rail type")
    channel: Literal["online", "pos"] = Field(default="online", description="Transaction channel")
    features: dict[str, float] = Field(default_factory=dict, description="Feature values")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class LegacyDecisionResponse(BaseModel):
    """Legacy decision response format for backward compatibility."""

    decision: str = Field(..., description="Legacy decision result (APPROVE/REVIEW/DECLINE)")
    reasons: list[str] = Field(default_factory=list, description="Machine-readable reason codes")
    actions: list[str] = Field(default_factory=list, description="Recommended action codes")
    meta: dict[str, Any] = Field(default_factory=dict, description="Decision metadata")

    # Enhanced fields
    signals_triggered: list[str] = Field(
        default_factory=list, description="List of triggered signals/rules"
    )
    explanation: str | None = Field(None, description="Human-readable explanation")
    explanation_human: str | None = Field(
        None, description="Enhanced human-readable explanation"
    )
    routing_hint: str | None = Field(None, description="Routing instruction")


# Helper functions for creating AP2 decision contracts
def create_ap2_decision_contract(
    intent: IntentMandate,
    cart: CartMandate,
    payment: PaymentMandate,
    result: DecisionResult,
    risk_score: float,
    reasons: list[DecisionReason],
    actions: list[DecisionAction],
    model: ModelType = "rules_only",
    trace_id: str | None = None,
    processing_time_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> AP2DecisionContract:
    """Create an AP2 decision contract with the given parameters."""

    decision_meta = DecisionMeta(
        model=model,
        trace_id=trace_id or str(uuid4()),
        processing_time_ms=processing_time_ms,
        model_version=None,
        model_sha256=None,
        model_trained_on=None,
    )

    decision_outcome = DecisionOutcome(
        result=result,
        risk_score=risk_score,
        reasons=reasons,
        actions=actions,
        meta=decision_meta,
    )

    return AP2DecisionContract(
        ap2_version="0.1.0",
        intent=intent,
        cart=cart,
        payment=payment,
        decision=decision_outcome,
        signing=SigningInfo(vc_proof=None, receipt_hash=None),
        metadata=metadata,
    )


def create_decision_reason(code: ReasonCode, detail: str) -> DecisionReason:
    """Create a decision reason with code and detail."""
    return DecisionReason(code=code, detail=detail)


def create_decision_action(
    action_type: ActionCode, to: str | None = None, detail: str | None = None
) -> DecisionAction:
    """Create a decision action with type and optional target/detail."""
    return DecisionAction(type=action_type, to=to, detail=detail)


# JSON serialization helpers
def ap2_contract_to_json(contract: AP2DecisionContract) -> str:
    """Convert AP2 decision contract to JSON string."""
    return contract.model_dump_json()


def ap2_contract_from_json(json_str: str) -> AP2DecisionContract:
    """Create AP2 decision contract from JSON string."""
    return AP2DecisionContract.model_validate_json(json_str)


# Validation helpers
def validate_ap2_contract(data: dict[str, Any] | str) -> AP2DecisionContract:
    """Validate and create an AP2 decision contract from data."""
    if isinstance(data, str):
        import json

        data_dict: dict[str, Any] = json.loads(data)
    else:
        data_dict = data

    return AP2DecisionContract(**data_dict)


def sign_and_hash_decision(contract: AP2DecisionContract) -> AP2DecisionContract:
    """
    Sign and hash a decision contract if enabled by configuration.

    Args:
        contract: AP2 decision contract to sign and hash

    Returns:
        Updated contract with signing and receipt information
    """
    # Check if signing is enabled
    sign_decisions = os.getenv("ORCA_SIGN_DECISIONS", "false").lower() == "true"
    receipt_hash_only = os.getenv("ORCA_RECEIPT_HASH_ONLY", "false").lower() == "true"

    # Create a copy of the contract
    contract_dict = contract.model_dump()

    # Initialize signing info
    if not contract_dict.get("signing"):
        contract_dict["signing"] = {}

    # Add receipt hash if enabled
    if sign_decisions or receipt_hash_only:
        try:
            from ..crypto.receipts import make_receipt

            receipt_hash = make_receipt(contract_dict)
            contract_dict["signing"]["receipt_hash"] = receipt_hash
        except Exception as e:
            print(f"Warning: Failed to create receipt hash: {e}")

    # Add VC proof if signing is enabled
    if sign_decisions:
        try:
            from ..crypto.signing import sign_decision

            vc_proof = sign_decision(contract_dict)
            if vc_proof:
                contract_dict["signing"]["vc_proof"] = vc_proof
        except Exception as e:
            print(f"Warning: Failed to sign decision: {e}")

    # Return updated contract
    return AP2DecisionContract(**contract_dict)


def is_signing_enabled() -> bool:
    """
    Check if decision signing is enabled.

    Returns:
        True if signing is enabled, False otherwise
    """
    return os.getenv("ORCA_SIGN_DECISIONS", "false").lower() == "true"


def is_receipt_hash_only() -> bool:
    """
    Check if only receipt hashing is enabled (no signing).

    Returns:
        True if only receipt hashing is enabled, False otherwise
    """
    return os.getenv("ORCA_RECEIPT_HASH_ONLY", "false").lower() == "true"
