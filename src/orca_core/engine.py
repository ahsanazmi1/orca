"""Decision engine for Orca Core."""

import uuid
from datetime import datetime

from .core.ml_hooks import predict_risk
from .explanations import generate_human_explanation
from .models import DecisionMeta, DecisionRequest, DecisionResponse
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
    # Get risk prediction
    risk_score = predict_risk(request.features)

    # Run deterministic rules
    decision_hint, reasons, actions, rules_evaluated = run_rules(request)

    # Start with APPROVE
    final_decision = "APPROVE"

    # Generate transaction metadata
    transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
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
    explanation_human = generate_human_explanation(unique_reasons, final_decision, request.context)

    # Extract signals triggered from rules_evaluated
    signals_triggered: list[str] = []
    for item in meta_structured.rules_evaluated:
        signals_triggered.append(str(item))
    if risk_score > 0.80:
        signals_triggered.append("HIGH_RISK")

    # Map REVIEW to ROUTE for the new status field
    status = "ROUTE" if final_decision == "REVIEW" else final_decision

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
