"""Decision engine for Orca Core."""

from datetime import datetime

try:
    from ocn_common.trace import new_trace_id
except ImportError:
    # Fallback when ocn-common is not available
    def new_trace_id():
        return f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


from .config import decision_mode, get_settings, is_ai_enabled
from .explanations import generate_human_explanation
from .llm.explain import explain_decision_llm, is_llm_configured, explain_rail_selection_llm
from .ml.model import predict_risk
from .models import DecisionMeta, DecisionRequest, DecisionResponse, DecisionStatus, NegotiationRequest, NegotiationResponse, RailEvaluation, RailType
from .events import emit_negotiation_explanation_event
from .rules.registry import run_rules


def determine_routing_hint(decision: str, request: DecisionRequest, meta: dict) -> str:
    """Determine routing hint based on decision and context."""
    # Check for payment method in context
    payment_method = request.context.get("payment_method", "unknown")

    # Handle case where payment_method might be a dict
    if isinstance(payment_method, dict):
        payment_method = payment_method.get("type", "unknown")

    # Convert to string and lowercase for comparison
    payment_method_str = str(payment_method).lower()

    if decision == "DECLINE":
        return "BLOCK_TRANSACTION"
    elif decision == "ROUTE":
        return "ROUTE_TO_MANUAL_REVIEW"
    elif payment_method_str in ["visa", "mastercard", "amex"]:
        return "ROUTE_TO_VISA_NETWORK"
    elif payment_method_str in ["ach", "bank_transfer"]:
        return "ROUTE_TO_ACH_NETWORK"
    else:
        return "PROCESS_NORMALLY"


def generate_explanation(
    decision: str, reasons: list[str], request: DecisionRequest, meta: dict
) -> str:
    """Generate human-readable explanation of the decision."""
    if decision == "APPROVE":
        return f"Transaction approved for ${request.cart_total:.2f}. Cart total within approved limits."
    elif decision == "DECLINE":
        risk_score = meta.get("risk_score", 0.0)
        if risk_score > 0.80:
            return f"Transaction declined due to high ML risk score of {risk_score:.3f}."
        else:
            return f"Transaction declined due to: {', '.join(reasons[:2])}."
    elif decision == "ROUTE":
        return f"Transaction flagged for manual review due to: {', '.join(reasons[:2])}."
    else:
        return f"Transaction decision: {decision}"


def evaluate_rules(request: DecisionRequest) -> DecisionResponse:
    """
    Evaluate decision rules against the request using the new rules system.

    Final decision logic:
    1. Start with APPROVE
    2. Apply registry rules → if any REVIEW hints → decision = REVIEW
    3. If ML risk hook > 0.80 → decision = DECLINE, add HIGH_RISK, BLOCK
    4. Return DecisionResponse with unique reasons/actions and meta.risk_score

    Args:
        request: The decision request to evaluate

    Returns:
        Decision response with decision, reasons, and actions
    """
    # Get current configuration
    get_settings()
    decision_mode()

    # Get risk prediction (enhanced for AI mode)
    ai_risk_data = None
    if is_ai_enabled():
        # Use ML model (XGBoost or stub based on configuration)
        ai_risk_data = predict_risk(request.features)
        risk_score = ai_risk_data["risk_score"]
    else:
        # Use local ML model for RULES_ONLY mode
        ai_risk_data = predict_risk(request.features)
        risk_score = ai_risk_data["risk_score"]

    # Run deterministic rules
    decision_hint, reasons, actions, rules_evaluated = run_rules(request)

    # Start with APPROVE
    final_decision: str = "APPROVE"

    # Generate transaction metadata using centralized trace utility
    trace_id = new_trace_id()
    transaction_id = f"txn_{trace_id.replace('-', '')[:16]}"
    timestamp = datetime.now()

    # Create structured metadata
    meta_structured = DecisionMeta(
        timestamp=timestamp,
        transaction_id=transaction_id,
        rail=request.rail,
        channel=request.channel,
        cart_total=request.cart_total,
        risk_score=risk_score,
        rules_evaluated=rules_evaluated,
        approved_amount=None,
    )

    # Create legacy meta dict for backward compatibility
    meta = {
        "risk_score": risk_score,
        "rules_evaluated": rules_evaluated,
        "timestamp": timestamp,
        "transaction_id": transaction_id,
        "rail": request.rail,
        "channel": request.channel,
        "cart_total": request.cart_total,
    }

    # Add AI risk data for RULES_PLUS_AI mode
    if ai_risk_data:
        meta["ai"] = {
            "risk_score": ai_risk_data["risk_score"],
            "reason_codes": ai_risk_data["reason_codes"],
            "version": ai_risk_data["version"],
            "model_type": ai_risk_data.get("model_type", "unknown"),
            "ml_version": ai_risk_data["version"],  # Add ml_version for compatibility
        }

        # Generate LLM explanation if available
        if is_llm_configured():
            try:
                llm_explanation = explain_decision_llm(
                    decision=final_decision,
                    risk_score=ai_risk_data["risk_score"],
                    reason_codes=ai_risk_data["reason_codes"],
                    transaction_data={
                        "amount": request.cart_total,
                        "channel": request.channel,
                        "rail": request.rail,
                        "currency": request.currency,
                    },
                    model_type=ai_risk_data.get("model_type", "unknown"),
                    model_version=ai_risk_data["version"],
                    rules_evaluated=rules_evaluated,
                    meta_data=meta,
                )

                if llm_explanation:
                    meta["ai"]["llm_explanation"] = {
                        "explanation": llm_explanation.explanation,
                        "confidence": llm_explanation.confidence,
                        "model_provenance": llm_explanation.model_provenance,
                        "processing_time_ms": llm_explanation.processing_time_ms,
                        "tokens_used": llm_explanation.tokens_used,
                    }
            except Exception as e:
                # Log error but don't fail the decision
                import logging

                logging.warning(f"Failed to generate LLM explanation: {e}")

    # If any rule hints REVIEW, set decision to REVIEW
    if decision_hint == "REVIEW":
        final_decision = "REVIEW"

    # If ML risk score > 0.80, override to DECLINE
    if risk_score > 0.80:
        final_decision = "DECLINE"
        reasons.append(f"HIGH_RISK: ML risk score {risk_score:.3f} exceeds 0.800 threshold")
        actions.append("BLOCK")
        meta_structured.rules_evaluated.append("HIGH_RISK")
        if isinstance(meta["rules_evaluated"], list):
            meta["rules_evaluated"].append("HIGH_RISK")

    # If no rules triggered, provide default approval reasoning
    if not reasons:
        reasons.append(f"Cart total ${request.cart_total:.2f} within approved threshold")
        actions.append("Process payment")
        actions.append("Send confirmation")
        meta_structured.approved_amount = request.cart_total
        meta["approved_amount"] = request.cart_total

    # Remove duplicate reasons while preserving order, but keep duplicate actions
    unique_reasons = list(dict.fromkeys(reasons))
    # For actions, we want to preserve duplicates for backward compatibility with tests
    unique_actions = actions

    # Determine routing hint based on decision and context
    routing_hint = determine_routing_hint(final_decision, request, meta)

    # Generate explanation
    explanation = generate_explanation(final_decision, unique_reasons, request, meta)

    # Generate human-readable explanation using templates
    # Enhanced with AI/LLM for RULES_PLUS_AI mode
    if is_ai_enabled():
        # TODO: Integrate with Azure OpenAI for enhanced explanations
        explanation_human = generate_human_explanation(
            unique_reasons, final_decision, request.context
        )
    else:
        # Use template-based explanations for RULES_ONLY mode
        explanation_human = generate_human_explanation(
            unique_reasons, final_decision, request.context
        )

    # Extract signals triggered from rules_evaluated
    signals_triggered: list[str] = []
    for item in meta_structured.rules_evaluated:
        signals_triggered.append(str(item))
    if risk_score > 0.80:
        signals_triggered.append("HIGH_RISK")

    # Map REVIEW to ROUTE for the new status field
    if final_decision == "REVIEW":
        status: DecisionStatus = "ROUTE"
    elif final_decision == "APPROVE":
        status = "APPROVE"
    elif final_decision == "DECLINE":
        status = "DECLINE"
    else:
        status = "APPROVE"  # Default fallback

    return DecisionResponse(
        # Legacy fields for backward compatibility
        decision=final_decision,
        reasons=unique_reasons,
        actions=unique_actions,
        meta=meta,
        # New Week 4 fields
        status=status,
        meta_structured=meta_structured,
        # Enhanced fields
        signals_triggered=signals_triggered,
        explanation=explanation,
        explanation_human=explanation_human,
        routing_hint=routing_hint,
        # Backward compatibility fields (deprecated)
        transaction_id=transaction_id,
        cart_total=request.cart_total,
        timestamp=timestamp,
        rail=request.rail,
    )


# Phase 3 - Negotiation & Live Fee Bidding Functions

def get_rail_cost_data(rail_type: RailType, cart_total: float) -> dict[str, float]:
    """Get cost data for a specific rail type."""
    # Base costs in basis points (1 basis point = 0.01%)
    rail_costs = {
        "ACH": {"base_cost": 5.0, "settlement_days": 2},  # 5 bps, 2 days
        "Debit": {"base_cost": 25.0, "settlement_days": 1},  # 25 bps, 1 day
        "Credit": {"base_cost": 150.0, "settlement_days": 1},  # 150 bps, 1 day
        "Card": {"base_cost": 150.0, "settlement_days": 1},  # Alias for Credit
    }
    
    base_data = rail_costs.get(rail_type, rail_costs["Credit"])
    
    # Adjust cost based on transaction size (volume discounts)
    if cart_total > 10000:  # Large transactions get volume discount
        cost_multiplier = 0.8
    elif cart_total > 1000:  # Medium transactions get small discount
        cost_multiplier = 0.9
    else:
        cost_multiplier = 1.0
    
    return {
        "base_cost": base_data["base_cost"] * cost_multiplier,
        "settlement_days": base_data["settlement_days"],
    }


def get_rail_speed_score(rail_type: RailType, channel: str) -> float:
    """Calculate speed score for a rail type."""
    # Speed scoring: 1.0 = fastest, 0.0 = slowest
    speed_scores = {
        "ACH": 0.3,  # Slower settlement
        "Debit": 0.9,  # Fast settlement
        "Credit": 0.95,  # Very fast settlement
        "Card": 0.95,  # Alias for Credit
    }
    
    base_score = speed_scores.get(rail_type, 0.5)
    
    # Adjust for channel
    if channel == "pos" and rail_type in ["Debit", "Credit", "Card"]:
        base_score += 0.05  # POS is slightly faster for card rails
    
    return min(base_score, 1.0)


def get_rail_risk_score(rail_type: RailType, ml_risk_score: float, channel: str) -> float:
    """Calculate risk-adjusted score for a rail type."""
    # Base risk by rail type (higher = more risky)
    rail_risk_base = {
        "ACH": 0.2,  # Lower risk, but higher fraud potential
        "Debit": 0.4,  # Medium risk
        "Credit": 0.7,  # Higher risk, chargebacks
        "Card": 0.7,  # Alias for Credit
    }
    
    base_risk = rail_risk_base.get(rail_type, 0.5)
    
    # Incorporate ML risk score (weighted)
    ml_weight = 0.6  # ML risk contributes 60% to final risk score
    rail_weight = 0.4  # Rail base risk contributes 40%
    
    combined_risk = (ml_risk_score * ml_weight) + (base_risk * rail_weight)
    
    # Adjust for channel
    if channel == "online" and rail_type in ["ACH"]:
        combined_risk += 0.1  # Online ACH is riskier
    
    return min(combined_risk, 1.0)


def evaluate_rail_with_weights(rail_type: RailType, request: NegotiationRequest, ml_risk_score: float, weights: dict) -> RailEvaluation:
    """Evaluate a single payment rail with specific weights."""
    cost_data = get_rail_cost_data(rail_type, request.cart_total)
    
    # Calculate scores (higher = better for cost and speed, lower = better for risk)
    cost_score = max(0.0, 1.0 - (cost_data["base_cost"] / 200.0))  # Normalize to 0-1
    speed_score = get_rail_speed_score(rail_type, request.channel)
    risk_score = get_rail_risk_score(rail_type, ml_risk_score, request.channel)
    
    # Calculate composite score with specified weights
    composite_score = (
        cost_score * weights["cost"] +
        speed_score * weights["speed"] +
        (1.0 - risk_score) * weights["risk"]  # Invert risk (lower risk = higher score)
    )
    
    # Generate explanation factors
    cost_factors = []
    if cost_data["base_cost"] < 50:
        cost_factors.append("low processing cost")
    elif cost_data["base_cost"] > 100:
        cost_factors.append("high processing cost")
    
    speed_factors = []
    if cost_data["settlement_days"] <= 1:
        speed_factors.append("instant settlement")
    elif cost_data["settlement_days"] <= 2:
        speed_factors.append("fast settlement")
    else:
        speed_factors.append("delayed settlement")
    
    risk_factors = []
    if ml_risk_score > 0.7:
        risk_factors.append("high ML risk score")
    if rail_type in ["Credit", "Card"]:
        risk_factors.append("chargeback risk")
    if rail_type == "ACH" and request.channel == "online":
        risk_factors.append("ACH fraud risk")
    
    return RailEvaluation(
        rail_type=rail_type,
        cost_score=cost_score,
        speed_score=speed_score,
        risk_score=risk_score,
        composite_score=composite_score,
        base_cost=cost_data["base_cost"],
        settlement_days=cost_data["settlement_days"],
        ml_risk_score=ml_risk_score,
        cost_factors=cost_factors,
        speed_factors=speed_factors,
        risk_factors=risk_factors,
    )


def evaluate_rail(rail_type: RailType, request: NegotiationRequest, ml_risk_score: float) -> RailEvaluation:
    """Evaluate a single payment rail."""
    cost_data = get_rail_cost_data(rail_type, request.cart_total)
    
    # Calculate scores (higher = better for cost and speed, lower = better for risk)
    cost_score = max(0.0, 1.0 - (cost_data["base_cost"] / 200.0))  # Normalize to 0-1
    speed_score = get_rail_speed_score(rail_type, request.channel)
    risk_score = get_rail_risk_score(rail_type, ml_risk_score, request.channel)
    
    # Calculate composite score with weights
    composite_score = (
        cost_score * request.cost_weight +
        speed_score * request.speed_weight +
        (1.0 - risk_score) * request.risk_weight  # Invert risk (lower risk = higher score)
    )
    
    # Generate explanation factors
    cost_factors = []
    if cost_data["base_cost"] < 50:
        cost_factors.append("low processing cost")
    elif cost_data["base_cost"] > 100:
        cost_factors.append("high processing cost")
    
    speed_factors = []
    if cost_data["settlement_days"] <= 1:
        speed_factors.append("instant settlement")
    elif cost_data["settlement_days"] <= 2:
        speed_factors.append("fast settlement")
    else:
        speed_factors.append("delayed settlement")
    
    risk_factors = []
    if ml_risk_score > 0.7:
        risk_factors.append("high ML risk score")
    if rail_type in ["Credit", "Card"]:
        risk_factors.append("chargeback risk")
    if rail_type == "ACH" and request.channel == "online":
        risk_factors.append("ACH fraud risk")
    
    return RailEvaluation(
        rail_type=rail_type,
        cost_score=cost_score,
        speed_score=speed_score,
        risk_score=risk_score,
        composite_score=composite_score,
        base_cost=cost_data["base_cost"],
        settlement_days=cost_data["settlement_days"],
        ml_risk_score=ml_risk_score,
        cost_factors=cost_factors,
        speed_factors=speed_factors,
        risk_factors=risk_factors,
    )


def determine_optimal_rail(request: NegotiationRequest) -> NegotiationResponse:
    """
    Determine the optimal payment rail using weighted scoring.
    
    Weights: cost=0.4, speed=0.3, risk=0.3
    
    Args:
        request: Negotiation request with cart details and preferences
        
    Returns:
        NegotiationResponse with optimal rail and evaluations
    """
    import os
    import random
    import numpy as np
    
    # Set deterministic seed for consistent results
    deterministic_seed = int(request.context.get("deterministic_seed", 42))
    random.seed(deterministic_seed)
    np.random.seed(deterministic_seed)
    
    # Generate trace ID
    trace_id = new_trace_id()
    timestamp = datetime.now()
    
    # Get ML risk score with deterministic seed
    ml_result = predict_risk(request.features)
    ml_risk_score = ml_result["risk_score"]
    ml_model_used = ml_result.get("model_type", "xgboost")
    
    # Override weights to ensure exact specification: cost=0.4, speed=0.3, risk=0.3
    normalized_weights = {
        "cost": 0.4,
        "speed": 0.3, 
        "risk": 0.3
    }
    
    # Evaluate all available rails with normalized weights
    rail_evaluations = []
    for rail_type in request.available_rails:
        evaluation = evaluate_rail_with_weights(rail_type, request, ml_risk_score, normalized_weights)
        rail_evaluations.append(evaluation)
    
    # Sort by composite score (highest first)
    rail_evaluations.sort(key=lambda x: x.composite_score, reverse=True)
    optimal_rail = rail_evaluations[0].rail_type if rail_evaluations else "Credit"
    
    # Generate explanation (try LLM first, fallback to deterministic)
    if is_llm_configured():
        try:
            # Create temporary response for LLM explanation
            temp_response = NegotiationResponse(
                optimal_rail=optimal_rail,
                rail_evaluations=rail_evaluations,
                explanation="",  # Will be filled by LLM
                trace_id=trace_id,
                timestamp=timestamp,
                ml_model_used=ml_model_used,
                negotiation_metadata={
                    "weights": normalized_weights,
                    "original_weights": {
                        "cost": request.cost_weight,
                        "speed": request.speed_weight,
                        "risk": request.risk_weight,
                    },
                    "ml_risk_score": ml_risk_score,
                    "rails_evaluated": len(rail_evaluations),
                    "deterministic_seed": deterministic_seed,
                },
            )
            explanation = explain_rail_selection_llm(temp_response, request)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM rail explanation failed, using fallback: {e}")
            explanation = generate_rail_explanation(optimal_rail, rail_evaluations, request)
    else:
        explanation = generate_rail_explanation(optimal_rail, rail_evaluations, request)
    
    # Create negotiation response
    response = NegotiationResponse(
        optimal_rail=optimal_rail,
        rail_evaluations=rail_evaluations,
        explanation=explanation,
        trace_id=trace_id,
        timestamp=timestamp,
        ml_model_used=ml_model_used,
        negotiation_metadata={
            "weights": normalized_weights,
            "original_weights": {
                "cost": request.cost_weight,
                "speed": request.speed_weight,
                "risk": request.risk_weight,
            },
            "ml_risk_score": ml_risk_score,
            "rails_evaluated": len(rail_evaluations),
            "deterministic_seed": deterministic_seed,
        },
    )
    
    # Emit CloudEvent for negotiation explanation
    try:
        emit_negotiation_explanation_event(response, trace_id)
    except Exception as e:
        # Log error but don't fail the negotiation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to emit negotiation explanation event: {e}")
    
    return response


def generate_rail_explanation(optimal_rail: RailType, evaluations: list[RailEvaluation], request: NegotiationRequest) -> str:
    """Generate human-readable explanation for rail selection."""
    optimal_eval = next((e for e in evaluations if e.rail_type == optimal_rail), None)
    if not optimal_eval:
        return f"Selected {optimal_rail} as the default payment rail."
    
    # Build explanation
    reasons = []
    
    # Cost reasoning
    if optimal_eval.cost_score > 0.7:
        reasons.append(f"{optimal_rail} offers the lowest cost at {optimal_eval.base_cost:.1f} basis points")
    
    # Speed reasoning
    if optimal_eval.speed_score > 0.8:
        reasons.append(f"{optimal_rail} provides fastest settlement in {optimal_eval.settlement_days} day(s)")
    
    # Risk reasoning
    if optimal_eval.risk_score < 0.4:
        reasons.append(f"{optimal_rail} has the lowest risk profile")
    
    # Explain why other rails were not chosen
    declined_reasons = []
    for eval_rail in evaluations:
        if eval_rail.rail_type != optimal_rail:
            if eval_rail.composite_score < optimal_eval.composite_score * 0.8:
                if eval_rail.cost_score < optimal_eval.cost_score * 0.8:
                    declined_reasons.append(f"{eval_rail.rail_type} declined due to higher cost ({eval_rail.base_cost:.1f} bps)")
                elif eval_rail.risk_score > optimal_eval.risk_score * 1.5:
                    declined_reasons.append(f"{eval_rail.rail_type} declined due to higher risk ({eval_rail.risk_score:.2f})")
    
    explanation_parts = [f"Selected {optimal_rail} because: " + ", ".join(reasons)]
    
    if declined_reasons:
        explanation_parts.append("Other rails declined: " + "; ".join(declined_reasons[:2]))
    
    return ". ".join(explanation_parts) + "."
