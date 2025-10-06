"""Pydantic models for Orca Core decision engine."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Define valid decision statuses
DecisionStatus = Literal["APPROVE", "DECLINE", "ROUTE"]

# Define valid rail types - Extended for multi-rail support
RailType = Literal["Card", "ACH", "RTP", "FedNow", "SEPA", "Wire", "Crypto"]

# Define valid channel types
ChannelType = Literal["online", "pos"]

# Define valid instrument types - Extended for multi-instrument support
InstrumentType = Literal[
    "credit_card", "debit_card", "prepaid_card", "bank_transfer", 
    "stablecoin", "digital_wallet", "bnpl", "cash"
]

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
    rail: RailType = Field(default="Card", description="Payment rail type (Card, ACH, RTP, FedNow, SEPA, Wire, Crypto)")
    instrument: InstrumentType = Field(default="credit_card", description="Payment instrument type")
    channel: ChannelType = Field(
        default="online", description="Transaction channel (online or pos)"
    )
    features: dict[str, float] = Field(default_factory=dict, description="Feature values")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class DecisionMeta(BaseModel):
    """Metadata for decision responses."""

    timestamp: datetime = Field(..., description="Decision timestamp")
    transaction_id: str = Field(..., description="Unique transaction identifier")
    rail: RailType = Field(..., description="Payment rail type used for this transaction")
    channel: ChannelType = Field(..., description="Transaction channel")
    cart_total: float = Field(..., description="Total cart value for this transaction")
    risk_score: float = Field(default=0.0, description="ML risk score (0.0-1.0)")
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


# Phase 3 & 4 Models for Negotiation and Payment Instruction

class RailEvaluation(BaseModel):
    """Evaluation result for a payment rail."""
    
    rail_type: RailType = Field(..., description="Payment rail type")
    cost_score: float = Field(..., description="Cost score (0.0-1.0)")
    speed_score: float = Field(..., description="Speed score (0.0-1.0)")
    risk_score: float = Field(..., description="Risk score (0.0-1.0)")
    composite_score: float = Field(..., description="Composite weighted score (0.0-1.0)")
    base_cost: float = Field(..., description="Base cost in basis points")
    settlement_days: int = Field(..., description="Settlement time in days")
    ml_risk_score: float = Field(..., description="ML risk score (0.0-1.0)")
    cost_factors: list[str] = Field(default_factory=list, description="Cost-related factors")
    speed_factors: list[str] = Field(default_factory=list, description="Speed-related factors")
    risk_factors: list[str] = Field(default_factory=list, description="Risk-related factors")
    explanation: str = Field(..., description="Human-readable explanation of the evaluation")


class NegotiationRequest(BaseModel):
    """Request for rail negotiation evaluation."""
    
    amount: float = Field(..., description="Transaction amount", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    merchant_id: str = Field(..., description="Merchant identifier")
    channel: str = Field(default="online", description="Transaction channel")
    customer_context: dict[str, Any] = Field(default_factory=dict, description="Customer context")
    available_rails: list[RailType] = Field(default_factory=lambda: ["Card", "ACH", "Wire", "Crypto", "Instant"], description="Available payment rails")
    preferences: dict[str, Any] = Field(default_factory=dict, description="Merchant/customer preferences")
    trace_id: str = Field(..., description="Transaction trace ID")


class NegotiationResponse(BaseModel):
    """Response from rail negotiation evaluation."""
    
    optimal_rail: RailType = Field(..., description="Selected optimal rail")
    rail_evaluations: list[RailEvaluation] = Field(..., description="Evaluations for all available rails")
    explanation: str = Field(..., description="Human-readable explanation of the selection")
    confidence: float = Field(..., description="Overall confidence in the selection")
    trace_id: str = Field(..., description="Transaction trace ID")
    negotiation_metadata: dict[str, Any] = Field(default_factory=dict, description="Additional negotiation metadata")


class PolicyConstraint(BaseModel):
    """Policy constraint from Olive agent."""
    
    policy_type: str = Field(..., description="Type of policy constraint")
    constraint_value: float = Field(..., description="Constraint value")
    weight: float = Field(..., description="Weight of this constraint (0.0-1.0)")
    description: str = Field(..., description="Human-readable description")


class TrustSignal(BaseModel):
    """Trust signal from Onyx agent."""
    
    trust_score: float = Field(..., description="Trust score (0.0-1.0)")
    risk_level: str = Field(..., description="Risk level (low/medium/high/critical)")
    signals: list[dict[str, Any]] = Field(default_factory=list, description="Individual trust signals")
    confidence: float = Field(..., description="Confidence in trust assessment")


class TreasuryConstraint(BaseModel):
    """Treasury constraint from Oasis agent."""
    
    constraint_type: str = Field(..., description="Type of treasury constraint")
    status: str = Field(..., description="Constraint status (passed/failed/warning)")
    available_balance: float = Field(..., description="Available balance")
    constraint_value: float = Field(..., description="Constraint threshold value")


class PaymentInstruction(BaseModel):
    """Final payment instruction generated by Orca."""
    
    instruction_id: str = Field(..., description="Unique instruction identifier")
    trace_id: str = Field(..., description="Transaction trace ID")
    selected_rail: RailType = Field(..., description="Selected payment rail")
    selected_processor: str = Field(..., description="Selected payment processor")
    selected_instrument: str = Field(..., description="Selected payment instrument")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    effective_cost: float = Field(..., description="Total effective cost including risk")
    settlement_time_hours: int = Field(..., description="Expected settlement time")
    confidence: float = Field(..., description="Confidence in this instruction")
    explanation: str = Field(..., description="Explanation of why this instruction was chosen")
    alternatives: list[dict[str, Any]] = Field(default_factory=list, description="Top-k alternative options")
    constraints_applied: list[dict[str, Any]] = Field(default_factory=list, description="Applied constraints")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CounterfactualAnalysis(BaseModel):
    """Counterfactual analysis for payment instruction."""
    
    trace_id: str = Field(..., description="Transaction trace ID")
    original_instruction: PaymentInstruction = Field(..., description="Original payment instruction")
    alternatives: list[dict[str, Any]] = Field(..., description="Top-k alternative scenarios")
    scenario_differences: list[dict[str, Any]] = Field(..., description="Differences between scenarios")
    sensitivity_analysis: dict[str, Any] = Field(default_factory=dict, description="Sensitivity analysis results")


# Phase 7 - Multi-Rail + Multi-Instrument Models

class RailCapability(BaseModel):
    """Capability information for a payment rail."""
    
    rail_type: RailType = Field(..., description="Payment rail type")
    supported_instruments: list[InstrumentType] = Field(..., description="Supported payment instruments")
    max_amount: float = Field(..., description="Maximum transaction amount")
    min_amount: float = Field(..., description="Minimum transaction amount")
    settlement_time_hours: int = Field(..., description="Settlement time in hours")
    cost_basis_points: float = Field(..., description="Cost in basis points")
    availability_24_7: bool = Field(default=False, description="24/7 availability")
    cross_border: bool = Field(default=False, description="Cross-border support")
    real_time: bool = Field(default=False, description="Real-time processing")
    jurisdictions: list[str] = Field(default_factory=list, description="Supported jurisdictions")


class InstrumentCapability(BaseModel):
    """Capability information for a payment instrument."""
    
    instrument_type: InstrumentType = Field(..., description="Payment instrument type")
    supported_rails: list[RailType] = Field(..., description="Supported payment rails")
    max_amount: float = Field(..., description="Maximum transaction amount")
    min_amount: float = Field(..., description="Minimum transaction amount")
    funding_time_hours: int = Field(..., description="Funding time in hours")
    cost_basis_points: float = Field(..., description="Cost in basis points")
    requires_verification: bool = Field(default=False, description="Requires verification")
    risk_level: str = Field(default="medium", description="Risk level (low/medium/high)")
    regulatory_requirements: list[str] = Field(default_factory=list, description="Regulatory requirements")


class MultiRailEvaluation(BaseModel):
    """Evaluation result for multi-rail and multi-instrument combinations."""
    
    rail_type: RailType = Field(..., description="Payment rail type")
    instrument_type: InstrumentType = Field(..., description="Payment instrument type")
    combination_id: str = Field(..., description="Unique combination identifier")
    
    # Evaluation metrics
    total_score: float = Field(..., ge=0.0, le=1.0, description="Overall score (0.0-1.0)")
    cost_score: float = Field(..., ge=0.0, le=1.0, description="Cost efficiency score")
    speed_score: float = Field(..., ge=0.0, le=1.0, description="Speed/velocity score")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk assessment score")
    availability_score: float = Field(..., ge=0.0, le=1.0, description="Availability score")
    
    # Financial metrics
    total_cost: float = Field(..., description="Total cost in USD")
    effective_cost_bps: float = Field(..., description="Effective cost in basis points")
    settlement_time_hours: int = Field(..., description="Expected settlement time")
    
    # Capability flags
    is_available: bool = Field(..., description="Whether combination is available")
    is_real_time: bool = Field(default=False, description="Real-time processing capability")
    is_cross_border: bool = Field(default=False, description="Cross-border capability")
    
    # Risk and compliance
    risk_level: str = Field(..., description="Risk level (low/medium/high/critical)")
    compliance_status: str = Field(..., description="Compliance status")
    requires_kyc: bool = Field(default=False, description="Requires KYC verification")
    
    # Explanation and metadata
    explanation: str = Field(..., description="Human-readable explanation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in evaluation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MultiRailNegotiationRequest(BaseModel):
    """Request for multi-rail and multi-instrument negotiation."""
    
    trace_id: str = Field(..., description="Transaction trace ID")
    amount: float = Field(..., description="Transaction amount", gt=0)
    currency: str = Field(default="USD", description="Currency code")
    merchant_id: str = Field(..., description="Merchant identifier")
    customer_context: dict[str, Any] = Field(default_factory=dict, description="Customer context")
    
    # Constraints and preferences
    preferred_rails: list[RailType] = Field(default_factory=list, description="Preferred payment rails")
    preferred_instruments: list[InstrumentType] = Field(default_factory=list, description="Preferred instruments")
    excluded_rails: list[RailType] = Field(default_factory=list, description="Excluded payment rails")
    excluded_instruments: list[InstrumentType] = Field(default_factory=list, description="Excluded instruments")
    
    # Requirements
    max_settlement_hours: int = Field(default=72, description="Maximum acceptable settlement time")
    max_cost_bps: float = Field(default=100.0, description="Maximum acceptable cost in basis points")
    require_real_time: bool = Field(default=False, description="Require real-time processing")
    cross_border: bool = Field(default=False, description="Cross-border transaction")
    
    # Context
    transaction_context: dict[str, Any] = Field(default_factory=dict, description="Transaction context")
    risk_tolerance: str = Field(default="medium", description="Risk tolerance level")
    regulatory_requirements: list[str] = Field(default_factory=list, description="Regulatory requirements")


class MultiRailNegotiationResponse(BaseModel):
    """Response from multi-rail and multi-instrument negotiation."""
    
    trace_id: str = Field(..., description="Transaction trace ID")
    optimal_combination: MultiRailEvaluation = Field(..., description="Optimal rail/instrument combination")
    all_evaluations: list[MultiRailEvaluation] = Field(..., description="All evaluated combinations")
    
    # Summary metrics
    total_combinations_evaluated: int = Field(..., description="Total combinations evaluated")
    available_combinations: int = Field(..., description="Number of available combinations")
    real_time_combinations: int = Field(..., description="Number of real-time combinations")
    
    # Top alternatives
    top_alternatives: list[MultiRailEvaluation] = Field(default_factory=list, description="Top alternative combinations")
    
    # Explanation and metadata
    explanation: str = Field(..., description="Human-readable explanation of selection")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in selection")
    negotiation_metadata: dict[str, Any] = Field(default_factory=dict, description="Additional negotiation metadata")
