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
from .llm.explain import explain_decision_llm, is_llm_configured
from .ml.model import predict_risk
from .models import DecisionMeta, DecisionRequest, DecisionResponse, DecisionStatus
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


def determine_optimal_rail(request: DecisionRequest, risk_score: float, decision: str) -> dict | None:
    """Determine optimal payment rail based on transaction characteristics and risk."""
    if decision != "APPROVE":
        return None

    amount = request.cart_total
    channel = request.channel
    original_rail = request.rail

    # Rail characteristics (cost, speed, limits)
    rails = {
        "ACH": {
            "cost": 0.25,
            "speed_hours": 24,
            "limit": 25000,
            "risk_tolerance": 0.7,
            "description": "Low cost, slower, high limits"
        },
        "Card": {
            "cost": 2.9,
            "speed_hours": 0.1,
            "limit": 10000,
            "risk_tolerance": 0.5,
            "description": "Higher cost, instant, moderate limits"
        },
        "Wire": {
            "cost": 15.0,
            "speed_hours": 4,
            "limit": 100000,
            "risk_tolerance": 0.8,
            "description": "High cost, fast, very high limits"
        },
        "RTP": {
            "cost": 0.50,
            "speed_hours": 0.1,
            "limit": 25000,
            "risk_tolerance": 0.6,
            "description": "Low cost, instant, high limits"
        }
    }

    # Filter rails based on amount limits
    available_rails = {rail: info for rail, info in rails.items() if amount <= info["limit"]}

    if not available_rails:
        return None

    # Score rails based on cost, speed, and risk compatibility
    scored_rails = []
    for rail, info in available_rails.items():
        # Cost score (lower is better) - normalized to 0-1
        cost_score = max(0, 1 - (info["cost"] / 15.0))

        # Speed score (faster is better) - normalized to 0-1
        speed_score = max(0, 1 - (info["speed_hours"] / 24.0))

        # Risk compatibility score (higher risk tolerance for higher risk scores)
        risk_score_compatibility = 1 - abs(risk_score - info["risk_tolerance"])

        # Weighted total score
        total_score = (cost_score * 0.4) + (speed_score * 0.3) + (risk_score_compatibility * 0.3)

        scored_rails.append({
            "rail": rail,
            "score": total_score,
            "cost": info["cost"],
            "speed_hours": info["speed_hours"],
            "reason": info["description"]
        })

    # Sort by score (highest first)
    scored_rails.sort(key=lambda x: x["score"], reverse=True)

    if not scored_rails:
        return None

    best_rail = scored_rails[0]

    # Determine if rail was optimized
    was_optimized = best_rail["rail"] != original_rail

    return {
        "selected_rail": best_rail["rail"],
        "original_rail": original_rail,
        "was_optimized": was_optimized,
        "score": best_rail["score"],
        "cost": best_rail["cost"],
        "speed_hours": best_rail["speed_hours"],
        "reason": best_rail["reason"],
        "alternatives": scored_rails[1:3] if len(scored_rails) > 1 else []
    }


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

    # Add rail selection and optimization logic
    rail_selection = determine_optimal_rail(request, risk_score, final_decision)
    if rail_selection:
        meta["rail_selection"] = rail_selection
        meta_structured.rail_selection = rail_selection

        # Add rail-specific reasoning
        if rail_selection["selected_rail"] != request.rail:
            reasons.append(f"Rail optimized: {request.rail} → {rail_selection['selected_rail']} for better cost/speed")
        else:
            reasons.append(f"Rail {rail_selection['selected_rail']} selected: {rail_selection['reason']}")

        actions.append(f"Route via {rail_selection['selected_rail']}")

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
        # Use LLM explanation if available, otherwise fall back to templates
        if "llm_explanation" in meta.get("ai", {}):
            explanation_human = meta["ai"]["llm_explanation"]["explanation"]
            # Also update the main explanation field with LLM explanation
            explanation = explanation_human
        else:
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
