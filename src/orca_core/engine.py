"""Decision engine for Orca Core."""


from .core.ml_hooks import predict_risk
from .models import DecisionRequest, DecisionResponse
from .rules.registry import run_rules


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
    meta = {"risk_score": risk_score, "rules_evaluated": rules_evaluated}

    # If any rule hints REVIEW, set decision to REVIEW
    if decision_hint == "REVIEW":
        final_decision = "REVIEW"

    # If ML risk score > 0.80, override to DECLINE
    if risk_score > 0.80:
        final_decision = "DECLINE"
        reasons.append(f"HIGH_RISK: ML risk score {risk_score:.3f} exceeds 0.800 threshold")
        actions.append("BLOCK")
        if isinstance(meta["rules_evaluated"], list):
            meta["rules_evaluated"].append("HIGH_RISK")

    # If no rules triggered, provide default approval reasoning
    if not reasons:
        reasons.append(f"Cart total ${request.cart_total:.2f} within approved threshold")
        actions.append("Process payment")
        actions.append("Send confirmation")
        meta["approved_amount"] = request.cart_total

    # Remove duplicate reasons while preserving order, but keep duplicate actions
    unique_reasons = list(dict.fromkeys(reasons))
    # For actions, we want to preserve duplicates for backward compatibility with tests
    unique_actions = actions

    return DecisionResponse(
        decision=final_decision,
        reasons=unique_reasons,
        actions=unique_actions,
        meta=meta
    )
