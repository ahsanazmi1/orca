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


class DecisionRequest(BaseModel):
    """Request model for decision evaluation."""

    cart_total: float = Field(..., description="Total cart value", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    rail: RailType = Field(..., description="Payment rail type (Card or ACH)")
    channel: ChannelType = Field(..., description="Transaction channel (online or pos)")
    features: dict[str, float] = Field(default_factory=dict, description="Feature values")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class DecisionResponse(BaseModel):
    """Response model for decision results."""

    # Legacy fields for backward compatibility (required)
    decision: str = Field(..., description="Decision result (APPROVE/REVIEW/DECLINE)")
    reasons: list[str] = Field(default_factory=list, description="Reasoning for decision")
    actions: list[str] = Field(default_factory=list, description="Recommended actions")
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # New enhanced fields (optional for backward compatibility)
    status: DecisionStatus | None = Field(
        None, description="Decision result (APPROVE/DECLINE/ROUTE)"
    )
    signals_triggered: list[str] = Field(
        default_factory=list, description="List of triggered signals/rules"
    )
    explanation: str | None = Field(None, description="Human-readable explanation of the decision")
    explanation_human: str | None = Field(
        None, description="Enhanced human-readable explanation with templates"
    )
    routing_hint: str | None = Field(None, description="Routing instruction for the transaction")

    # Week 2 enhanced metadata fields
    transaction_id: str | None = Field(None, description="Unique transaction identifier")
    cart_total: float | None = Field(None, description="Total cart value for this transaction")
    timestamp: datetime | None = Field(None, description="Decision timestamp")
    rail: RailType | None = Field(None, description="Payment rail type used for this transaction")
