"""Pydantic models for Orca Core decision engine."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Define valid decision statuses
DecisionStatus = Literal["APPROVE", "DECLINE", "ROUTE"]

# Define valid rail types
RailType = Literal["Card", "ACH"]

# Define valid channel types
ChannelType = Literal["online", "pos"]

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


class DecisionRequest(BaseModel):
    """Request model for decision evaluation."""

    cart_total: float = Field(..., description="Total cart value", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    rail: RailType = Field(default="Card", description="Payment rail type (Card or ACH)")
    channel: ChannelType = Field(
        default="online", description="Transaction channel (online or pos)"
    )
    features: dict[str, float] = Field(default_factory=dict, description="Feature values")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class DecisionMeta(BaseModel):
    """Metadata for decision responses."""

    model_config = {"protected_namespaces": ()}

    timestamp: datetime = Field(..., description="Decision timestamp")
    transaction_id: str = Field(..., description="Unique transaction identifier")
    rail: RailType = Field(..., description="Payment rail type used for this transaction")
    channel: ChannelType = Field(..., description="Transaction channel")
    cart_total: float = Field(..., description="Total cart value for this transaction")
    risk_score: float = Field(default=0.0, description="ML risk score (0.0-1.0)")
    model_version: str = Field(default="none", description="ML model version used for risk scoring")
    features_used: list[str] = Field(
        default_factory=list, description="Features used in ML scoring"
    )
    rules_evaluated: list[str] = Field(
        default_factory=list, description="List of rules that were evaluated"
    )
    approved_amount: float | None = Field(None, description="Amount approved (if applicable)")


class DecisionResponse(BaseModel):
    """Response model for decision results."""

    # Legacy fields for backward compatibility (required)
    decision: str = Field(..., description="Legacy decision result (APPROVE/REVIEW/DECLINE)")
    reasons: list[str] = Field(default_factory=list, description="Machine-readable reason codes")
    actions: list[str] = Field(default_factory=list, description="Recommended action codes")
    meta: dict[str, Any] = Field(default_factory=dict, description="Decision metadata")

    # New Week 4 fields (optional for backward compatibility)
    status: DecisionStatus | None = Field(
        None, description="Decision result (APPROVE/DECLINE/ROUTE)"
    )
    meta_structured: DecisionMeta | None = Field(None, description="Structured decision metadata")

    # Enhanced fields
    signals_triggered: list[str] = Field(
        default_factory=list, description="List of triggered signals/rules"
    )
    explanation: str | None = Field(None, description="Human-readable explanation of the decision")
    explanation_human: str | None = Field(
        None, description="Enhanced human-readable explanation with templates"
    )
    routing_hint: str | None = Field(None, description="Routing instruction for the transaction")

    # Backward compatibility fields (deprecated)
    transaction_id: str | None = Field(
        None, description="[DEPRECATED] Use meta_structured.transaction_id"
    )
    cart_total: float | None = Field(
        None, description="[DEPRECATED] Use meta_structured.cart_total"
    )
    timestamp: datetime | None = Field(
        None, description="[DEPRECATED] Use meta_structured.timestamp"
    )
    rail: RailType | None = Field(None, description="[DEPRECATED] Use meta_structured.rail")
