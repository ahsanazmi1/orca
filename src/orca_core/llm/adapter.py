"""LLM adapter for generating plain-English explanations."""

import os
from typing import Literal

from ..models import DecisionResponse

ExplanationStyle = Literal["merchant", "developer"]


def explain_decision(decision: DecisionResponse, style: ExplanationStyle = "merchant") -> str:
    """
    Generate a plain-English explanation of the decision.

    Args:
        decision: The decision response to explain
        style: The explanation style ("merchant" or "developer")

    Returns:
        Human-readable explanation of the decision
    """
    # Check if LLM provider is configured
    provider = os.getenv("ORCA_LLM_PROVIDER", "none").lower()

    if provider == "none":
        return _fallback_explanation(decision, style)
    elif provider in ["openai", "azure"]:
        return _llm_explanation(decision, style, provider)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. Supported providers: none, openai, azure"
        )


def _fallback_explanation(decision: DecisionResponse, style: ExplanationStyle) -> str:
    """Generate explanation using template fallback when no LLM is configured."""

    if style == "merchant":
        return _merchant_template_explanation(decision)
    else:  # developer
        return _developer_template_explanation(decision)


def _merchant_template_explanation(decision: DecisionResponse) -> str:
    """Generate merchant-friendly explanation using templates."""

    if decision.decision == "APPROVE":
        cart_total = decision.meta_structured.cart_total if decision.meta_structured else 0.0
        return f"✅ Payment approved for ${cart_total:.2f}. Your transaction has been processed successfully."

    elif decision.decision == "DECLINE":
        if "ml_score_high" in decision.reasons:
            return "❌ Payment declined due to high risk assessment. Please contact support if you believe this is an error."
        else:
            reasons_text = _format_reasons_for_merchant(decision.reasons)
            return f"❌ Payment declined: {reasons_text}. Please try a different payment method or contact support."

    elif decision.decision == "REVIEW":
        reasons_text = _format_reasons_for_merchant(decision.reasons)
        return f"⏳ Payment under review: {reasons_text}. You will receive an email with next steps shortly."

    else:
        return f"Payment status: {decision.decision}"


def _developer_template_explanation(decision: DecisionResponse) -> str:
    """Generate developer-friendly explanation with technical details."""

    explanation_parts = []

    # Decision summary
    explanation_parts.append(f"Decision: {decision.decision}")

    # Risk score if available
    if decision.meta_structured and decision.meta_structured.risk_score > 0:
        explanation_parts.append(
            f"Risk Score: {decision.meta_structured.risk_score:.3f} (Model: {decision.meta_structured.model_version})"
        )

    # Rules evaluated
    if decision.meta_structured and decision.meta_structured.rules_evaluated:
        explanation_parts.append(
            f"Rules Evaluated: {', '.join(decision.meta_structured.rules_evaluated)}"
        )

    # Reasons
    if decision.reasons:
        explanation_parts.append(f"Reasons: {', '.join(decision.reasons)}")

    # Actions
    if decision.actions:
        explanation_parts.append(f"Actions: {', '.join(decision.actions)}")

    # Features used (if ML was used)
    if decision.meta_structured and decision.meta_structured.features_used:
        explanation_parts.append(
            f"ML Features: {', '.join(decision.meta_structured.features_used)}"
        )

    return " | ".join(explanation_parts)


def _format_reasons_for_merchant(reasons: list[str]) -> str:
    """Format technical reasons into merchant-friendly language."""

    merchant_reasons = []

    for reason in reasons:
        if "HIGH_TICKET" in reason:
            merchant_reasons.append("transaction amount exceeds limit")
        elif "velocity_flag" in reason:
            merchant_reasons.append("unusual transaction pattern detected")
        elif "ach_limit_exceeded" in reason:
            merchant_reasons.append("ACH transaction limit exceeded")
        elif "location_mismatch" in reason:
            merchant_reasons.append("location verification required")
        elif "online_verification" in reason:
            merchant_reasons.append("additional verification required")
        elif "chargeback_history" in reason:
            merchant_reasons.append("account history review required")
        elif "high_risk" in reason:
            merchant_reasons.append("high risk assessment")
        else:
            # Keep original reason if no mapping found
            merchant_reasons.append(reason.lower().replace("_", " "))

    # Join with commas and handle the last item
    if len(merchant_reasons) == 1:
        return merchant_reasons[0]
    elif len(merchant_reasons) == 2:
        return f"{merchant_reasons[0]} and {merchant_reasons[1]}"
    else:
        return f"{', '.join(merchant_reasons[:-1])}, and {merchant_reasons[-1]}"


def _llm_explanation(decision: DecisionResponse, style: ExplanationStyle, provider: str) -> str:
    """Generate explanation using LLM provider (placeholder implementation)."""

    # Check for API key
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
    elif provider == "azure" and not os.getenv("AZURE_OPENAI_API_KEY"):
        raise ValueError("AZURE_OPENAI_API_KEY environment variable is required for Azure provider")

    # TODO: Implement actual LLM calls
    # For now, return a placeholder message
    return f"[LLM {provider.upper()} explanation would be generated here for {style} style]"


def get_supported_providers() -> list[str]:
    """Get list of supported LLM providers."""
    return ["none", "openai", "azure"]


def validate_provider_config(provider: str) -> bool:
    """Validate that the provider is properly configured."""

    if provider == "none":
        return True
    elif provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    elif provider == "azure":
        return bool(os.getenv("AZURE_OPENAI_API_KEY"))
    else:
        return False
