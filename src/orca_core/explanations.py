"""Human-readable explanation templates for Orca Core decision engine."""

from typing import Any

# Version of explanation templates
EXPLANATION_VERSION = "1.0.0"

# Template mapping from rule keys to human-readable explanations
EXPLANATION_TEMPLATES: dict[str, dict[str, str]] = {
    # Card-specific rules
    "high_ticket": {
        "APPROVE": "Approved: Card transaction amount within normal limits.",
        "DECLINE": "Declined: Amount exceeds card threshold of ${threshold}. Please try a smaller amount or contact support.",
        "REVIEW": "Under review: High-value card transaction requires additional verification. Please check your email for next steps.",
    },
    "velocity_flag": {
        "APPROVE": "Approved: Transaction frequency within normal limits.",
        "DECLINE": "Declined: Too many recent attempts (last 24h: {velocity} transactions). Please wait 2 hours before trying again.",
        "REVIEW": "Under review: Unusual transaction frequency detected. Please wait 1 hour before trying again.",
    },
    "online_verification": {
        "APPROVE": "Approved: Online transaction verified successfully.",
        "DECLINE": "Declined: Online verification failed.",
        "REVIEW": "Under review: Additional verification required for online card transaction.",
    },
    "pos_processing": {
        "APPROVE": "Approved: Point-of-sale transaction processed normally.",
        "DECLINE": "Declined: Point-of-sale transaction declined.",
        "REVIEW": "Under review: Point-of-sale transaction requires attention.",
    },
    # ACH-specific rules
    "ach_limit_exceeded": {
        "APPROVE": "Approved: ACH transaction within limit.",
        "DECLINE": "Declined: Amount exceeds ACH limit of ${limit}. Please try an amount under ${limit} or use a credit card instead.",
        "REVIEW": "Under review: ACH transaction approaching limit. Please try a smaller amount or use a different payment method.",
    },
    "location_mismatch": {
        "APPROVE": "Approved: Location verified successfully.",
        "DECLINE": "Declined: Unusual location compared to profile.",
        "REVIEW": "Under review: Location differs from billing address.",
    },
    "ach_online_verification": {
        "APPROVE": "Approved: Online ACH transaction verified.",
        "DECLINE": "Declined: Online ACH verification failed.",
        "REVIEW": "Under review: Additional verification required for online ACH transaction.",
    },
    "ach_pos_processing": {
        "APPROVE": "Approved: Point-of-sale ACH transaction processed.",
        "DECLINE": "Declined: Point-of-sale ACH transaction declined.",
        "REVIEW": "Under review: Point-of-sale ACH transaction requires attention.",
    },
    # General rules
    "HIGH_TICKET": {
        "APPROVE": "Approved: Transaction amount within approved limits.",
        "DECLINE": "Declined: Transaction amount exceeds approved threshold.",
        "REVIEW": "Under review: High-value transaction requires verification.",
    },
    "VELOCITY_FLAG": {
        "APPROVE": "Approved: Transaction frequency within normal limits.",
        "DECLINE": "Declined: Excessive transaction frequency detected.",
        "REVIEW": "Under review: Unusual transaction pattern detected.",
    },
    "LOCATION_MISMATCH": {
        "APPROVE": "Approved: Location verified successfully.",
        "DECLINE": "Declined: Location mismatch detected.",
        "REVIEW": "Under review: Location verification required.",
    },
    "CHARGEBACK_HISTORY": {
        "APPROVE": "Approved: No recent chargeback issues.",
        "DECLINE": "Declined: Recent chargeback history detected.",
        "REVIEW": "Under review: Chargeback history requires attention.",
    },
    "LOYALTY_BOOST": {
        "APPROVE": "Approved: Loyalty benefits applied successfully.",
        "DECLINE": "Declined: Loyalty benefits could not be applied.",
        "REVIEW": "Under review: Loyalty benefits verification required.",
    },
    "loyalty": {
        "APPROVE": "Approved: Customer loyalty tier benefits applied.",
        "DECLINE": "Declined: Loyalty benefits could not be applied.",
        "REVIEW": "Under review: Loyalty tier verification required.",
    },
    "ITEM_COUNT": {
        "APPROVE": "Approved: Cart item count within normal limits.",
        "DECLINE": "Declined: Too many items in cart.",
        "REVIEW": "Under review: High item count requires verification.",
    },
    "HIGH_RISK": {
        "APPROVE": "Approved: Risk assessment passed.",
        "DECLINE": "Declined: High risk score detected.",
        "REVIEW": "Under review: Risk assessment requires manual review.",
    },
    "cart_total": {
        "APPROVE": "Approved: Transaction amount within approved limits.",
        "DECLINE": "Declined: Transaction amount exceeds approved threshold.",
        "REVIEW": "Under review: Transaction amount requires verification.",
    },
}

# Fallback template for unknown reasons
FALLBACK_TEMPLATE = "We made this decision based on {reasons}. More detail coming soon."


def get_explanation_template(reason: str, status: str) -> str:
    """
    Get explanation template for a specific reason and status.

    Args:
        reason: The rule reason (e.g., "high_ticket", "velocity_flag")
        status: The decision status ("APPROVE", "DECLINE", "REVIEW")

    Returns:
        Explanation template string
    """
    # Clean up reason to match template keys
    clean_reason = reason.lower()

    # Try exact match first
    if clean_reason in EXPLANATION_TEMPLATES:
        return EXPLANATION_TEMPLATES[clean_reason].get(status, FALLBACK_TEMPLATE)

    # Try partial matches for complex reasons
    for template_key, templates in EXPLANATION_TEMPLATES.items():
        if template_key in clean_reason or clean_reason in template_key:
            return templates.get(status, FALLBACK_TEMPLATE)

    # Handle specific patterns
    if "cart total" in clean_reason and "$" in reason:
        return EXPLANATION_TEMPLATES["HIGH_TICKET"].get(status, FALLBACK_TEMPLATE)

    if "loyalty" in clean_reason or "gold" in clean_reason or "silver" in clean_reason:
        return EXPLANATION_TEMPLATES["loyalty"].get(status, FALLBACK_TEMPLATE)

    # Return fallback if no match found
    return FALLBACK_TEMPLATE


def generate_human_explanation(
    reasons: list[str], status: str, context: dict[str, Any] | None = None
) -> str:
    """
    Generate human-readable explanation from reasons and status.

    Args:
        reasons: List of machine-readable reasons
        status: Decision status ("APPROVE", "DECLINE", "REVIEW")
        context: Additional context for template variables

    Returns:
        Human-readable explanation string
    """
    if not reasons:
        return "Transaction approved with no specific issues detected."

    context = context or {}

    # Extract template variables from context
    template_vars = {
        "threshold": context.get("threshold", "$5,000"),
        "limit": context.get("limit", "$2,000"),
        "velocity": context.get("velocity_24h", "multiple"),
    }

    explanations = []
    seen_explanations = set()

    for reason in reasons:
        # Extract the core reason (before colon if present)
        core_reason = reason.split(":")[0].strip()

        # Get template for this reason
        template = get_explanation_template(core_reason, status)

        # Format template with variables
        try:
            explanation = template.format(**template_vars)
        except KeyError:
            # If template formatting fails, use fallback
            explanation = FALLBACK_TEMPLATE.format(reasons=", ".join(reasons))

        # Only add if we haven't seen this explanation before
        if explanation not in seen_explanations:
            explanations.append(explanation)
            seen_explanations.add(explanation)

    # Join explanations
    if len(explanations) == 1:
        return explanations[0]
    elif len(explanations) == 2:
        return f"{explanations[0]} Additionally, {explanations[1].lower()}"
    else:
        primary = explanations[0]
        additional = "; ".join([exp.lower() for exp in explanations[1:]])
        return f"{primary} Additionally: {additional}"


def get_template_coverage() -> dict[str, list[str]]:
    """
    Get coverage of explanation templates.

    Returns:
        Dictionary mapping status to list of covered reasons
    """
    coverage: dict[str, list[str]] = {"APPROVE": [], "DECLINE": [], "REVIEW": []}

    for reason, templates in EXPLANATION_TEMPLATES.items():
        for status in coverage:
            if status in templates:
                coverage[status].append(reason)

    return coverage
