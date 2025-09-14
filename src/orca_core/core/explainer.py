"""Decision explanation utilities for Orca Core decision engine."""

from ..models import DecisionResponse


def explain_decision(response: DecisionResponse) -> str:
    """
    Convert a DecisionResponse into a plain-English explanation.

    This function takes the technical decision response and translates it into
    human-readable explanations that can be shown to users or logged for
    audit purposes.

    Args:
        response: The decision response to explain

    Returns:
        A plain-English explanation of the decision

    Examples:
        >>> response = DecisionResponse(
        ...     decision="REVIEW",
        ...     reasons=["HIGH_TICKET: Cart total $750.00 exceeds $500.00 threshold"],
        ...     actions=["ROUTE_TO_REVIEW"],
        ...     meta={"risk_score": 0.15}
        ... )
        >>> explanation = explain_decision(response)
        >>> print(explanation)
        The cart total was unusually high, so the transaction was flagged for review. Final decision: REVIEW.
    """
    # Mapping of reason codes to plain-English explanations
    reason_explanations: dict[str, str] = {
        "HIGH_TICKET": "The cart total was unusually high, so the transaction was flagged for review.",
        "VELOCITY_FLAG": "This customer made multiple purchases in a short time, which triggered a velocity check.",
        "LOCATION_MISMATCH": "The billing country did not match the IP location.",
        "HIGH_IP_DISTANCE": "The customer's IP address was far from their billing address.",
        "CHARGEBACK_HISTORY": "The customer has a history of chargebacks.",
        "LOYALTY_BOOST": "The customer's loyalty tier provided a benefit.",
        "HIGH_RISK": "The ML model predicted this transaction as high risk.",
    }

    # Extract explanation sentences from reasons
    explanation_sentences = []

    for reason in response.reasons:
        # Extract the reason code from the full reason string
        # Reason format: "REASON_CODE: description"
        reason_code = reason.split(":")[0].strip()

        if reason_code in reason_explanations:
            explanation_sentences.append(reason_explanations[reason_code])
        else:
            # Fallback for unknown reason codes
            explanation_sentences.append(f"Rule '{reason_code}' was triggered.")

    # If no reasons were found or processed, use default explanation
    if not explanation_sentences:
        if response.decision == "APPROVE":
            explanation_sentences.append(
                "The decision engine approved the transaction because no risk rules were triggered."
            )
        else:
            explanation_sentences.append(
                "The decision engine processed the transaction based on configured rules."
            )

    # Join all explanation sentences
    explanation = " ".join(explanation_sentences)

    # Always end with the final decision summary
    decision_summary = f"Final decision: {response.decision}."

    # Combine explanation with decision summary
    full_explanation = f"{explanation} {decision_summary}"

    return full_explanation
