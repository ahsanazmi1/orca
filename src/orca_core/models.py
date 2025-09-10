"""Pydantic models for Orca Core decision engine."""

from typing import Any

from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    """Request model for decision evaluation."""

    cart_total: float = Field(..., description="Total cart value", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    features: dict[str, float] = Field(default_factory=dict, description="Feature values")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class DecisionResponse(BaseModel):
    """Response model for decision results."""

    decision: str = Field(..., description="Decision result (APPROVE/REVIEW/DECLINE)")
    reasons: list[str] = Field(default_factory=list, description="Reasoning for decision")
    actions: list[str] = Field(default_factory=list, description="Recommended actions")
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
