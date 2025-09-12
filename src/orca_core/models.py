"""Pydantic models for Orca Core decision engine."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    """Request model for decision evaluation."""

    cart_total: float = Field(..., description="Total cart value", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    features: dict[str, float] = Field(default_factory=dict, description="Feature values")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


# Define valid decision statuses
DecisionStatus = Literal["APPROVE", "DECLINE", "ROUTE"]


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
    routing_hint: str | None = Field(None, description="Routing instruction for the transaction")
