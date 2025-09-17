"""Natural Language Generation for AP2 decision explanations.

This module generates human-readable explanations that explicitly cite AP2 field paths,
providing transparency and traceability for decision reasoning.
"""

from typing import Any, Optional

from ..core.decision_contract import AP2DecisionContract, DecisionAction, DecisionReason


class AP2NLGExplainer:
    """Generates natural language explanations with AP2 field citations."""

    def __init__(self) -> None:
        """Initialize the AP2 NLG explainer."""
        self.field_guardrails = self._build_field_guardrails()

    def _build_field_guardrails(self) -> set[str]:
        """Build set of valid AP2 field paths to prevent hallucination."""
        return {
            # Intent mandate fields
            "intent.actor",
            "intent.intent_type",
            "intent.channel",
            "intent.agent_presence",
            "intent.timestamps.created",
            "intent.timestamps.expires",
            "intent.nonce",
            # Cart mandate fields
            "cart.items",
            "cart.amount",
            "cart.currency",
            "cart.mcc",
            "cart.geo.country",
            "cart.geo.city",
            "cart.risk_flags",
            # Payment mandate fields
            "payment.instrument_ref",
            "payment.instrument_token",
            "payment.modality",
            "payment.constraints",
            "payment.routing_hints",
            "payment.auth_requirements",
            # Decision outcome fields
            "decision.result",
            "decision.risk_score",
            "decision.reasons",
            "decision.actions",
            "decision.meta.model",
            "decision.meta.trace_id",
            "decision.meta.version",
            # Signing fields
            "signing.vc_proof",
            "signing.receipt_hash",
        }

    def explain_decision(self, ap2_contract: AP2DecisionContract) -> str:
        """
        Generate a natural language explanation for an AP2 decision.

        Args:
            ap2_contract: AP2 decision contract to explain

        Returns:
            Human-readable explanation with AP2 field citations
        """
        # Extract key information from AP2 contract
        decision_result = ap2_contract.decision.result
        risk_score = ap2_contract.decision.risk_score
        reasons = ap2_contract.decision.reasons
        actions = ap2_contract.decision.actions

        # Build explanation components
        explanation_parts = []

        # Add decision result
        explanation_parts.append(f"Decision: {decision_result}")

        # Add risk score if significant
        if risk_score >= 0.1:
            explanation_parts.append(f"Risk score: {risk_score:.3f}")

        # Add AP2 field citations for reasons
        if reasons:
            reason_explanations = self._explain_reasons_with_ap2_fields(reasons, ap2_contract)
            explanation_parts.extend(reason_explanations)

        # Add AP2 field citations for actions
        if actions:
            action_explanations = self._explain_actions_with_ap2_fields(actions, ap2_contract)
            explanation_parts.extend(action_explanations)

        # Add key AP2 field context
        context_explanation = self._explain_ap2_context(ap2_contract)
        if context_explanation:
            explanation_parts.append(context_explanation)

        return ". ".join(explanation_parts) + "."

    def _explain_reasons_with_ap2_fields(
        self, reasons: list[DecisionReason], ap2_contract: AP2DecisionContract
    ) -> list[str]:
        """Explain decision reasons with AP2 field citations."""
        explanations = []

        for reason in reasons:
            explanation = self._explain_single_reason_with_ap2_fields(reason, ap2_contract)
            explanations.append(explanation)

        return explanations

    def _explain_single_reason_with_ap2_fields(
        self, reason: DecisionReason, ap2_contract: AP2DecisionContract
    ) -> str:
        """Explain a single reason with AP2 field citations."""
        reason_code = reason.code
        reason_detail = reason.detail

        # Map reason codes to AP2 field citations
        ap2_citations = self._get_ap2_citations_for_reason(reason_code, ap2_contract)

        if ap2_citations:
            citations_str = ", ".join(ap2_citations)
            return f"Reason '{reason_code}': {reason_detail} (AP2 fields: {citations_str})"
        else:
            return f"Reason '{reason_code}': {reason_detail}"

    def _explain_actions_with_ap2_fields(
        self, actions: list[DecisionAction], ap2_contract: AP2DecisionContract
    ) -> list[str]:
        """Explain decision actions with AP2 field citations."""
        explanations = []

        for action in actions:
            explanation = self._explain_single_action_with_ap2_fields(action, ap2_contract)
            explanations.append(explanation)

        return explanations

    def _explain_single_action_with_ap2_fields(
        self, action: DecisionAction, ap2_contract: AP2DecisionContract
    ) -> str:
        """Explain a single action with AP2 field citations."""
        action_type = action.type
        action_detail = action.detail or ""

        # Map action types to AP2 field citations
        ap2_citations = self._get_ap2_citations_for_action(action_type, ap2_contract)

        if ap2_citations:
            citations_str = ", ".join(ap2_citations)
            return f"Action '{action_type}': {action_detail} (AP2 fields: {citations_str})"
        else:
            return f"Action '{action_type}': {action_detail}"

    def _explain_ap2_context(self, ap2_contract: AP2DecisionContract) -> str:
        """Explain key AP2 context fields."""
        context_parts = []

        # Intent context
        intent = ap2_contract.intent
        context_parts.append(f"IntentMandate.channel={intent.channel.value}")
        context_parts.append(f"IntentMandate.actor={intent.actor.value}")

        # Cart context
        cart = ap2_contract.cart
        context_parts.append(f"CartMandate.amount={cart.amount}")
        context_parts.append(f"CartMandate.currency={cart.currency}")
        if cart.mcc:
            context_parts.append(f"CartMandate.mcc={cart.mcc}")

        # Payment context
        payment = ap2_contract.payment
        context_parts.append(f"PaymentMandate.modality={payment.modality.value}")
        if payment.auth_requirements:
            auth_reqs = [req.value for req in payment.auth_requirements]
            context_parts.append(f"PaymentMandate.auth_requirements={auth_reqs}")

        return f"AP2 context: {', '.join(context_parts)}"

    def _get_ap2_citations_for_reason(
        self, reason_code: str, ap2_contract: AP2DecisionContract
    ) -> list[str]:
        """Get AP2 field citations for a specific reason code."""
        citations = []

        # Map reason codes to relevant AP2 fields
        reason_field_mapping = {
            "high_ticket": [
                f"CartMandate.amount={ap2_contract.cart.amount}",
                f"CartMandate.currency={ap2_contract.cart.currency}",
            ],
            "velocity_flag": [
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
                f"IntentMandate.actor={ap2_contract.intent.actor.value}",
            ],
            "ach_limit_exceeded": [
                f"PaymentMandate.modality={ap2_contract.payment.modality.value}",
                f"CartMandate.amount={ap2_contract.cart.amount}",
            ],
            "location_mismatch": [
                f"CartMandate.geo.country={ap2_contract.cart.geo.country if ap2_contract.cart.geo else 'unknown'}",
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
            ],
            "online_verification": [
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
                f"PaymentMandate.modality={ap2_contract.payment.modality.value}",
            ],
            "ach_online_verification": [
                f"PaymentMandate.modality={ap2_contract.payment.modality.value}",
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
            ],
            "chargeback_history": [
                f"IntentMandate.actor={ap2_contract.intent.actor.value}",
            ],
            "high_risk": [
                f"DecisionOutcome.risk_score={ap2_contract.decision.risk_score}",
                f"DecisionOutcome.result={ap2_contract.decision.result}",
            ],
        }

        if reason_code in reason_field_mapping:
            citations = reason_field_mapping[reason_code]

        # Validate citations against guardrails
        validated_citations = []
        for citation in citations:
            if self._validate_field_citation(citation):
                validated_citations.append(citation)

        return validated_citations

    def _get_ap2_citations_for_action(
        self, action_type: str, ap2_contract: AP2DecisionContract
    ) -> list[str]:
        """Get AP2 field citations for a specific action type."""
        citations = []

        # Map action types to relevant AP2 fields
        action_field_mapping = {
            "manual_review": [
                f"DecisionOutcome.result={ap2_contract.decision.result}",
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
            ],
            "step_up_auth": [
                f"PaymentMandate.auth_requirements={[req.value for req in ap2_contract.payment.auth_requirements]}",
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
            ],
            "fallback_card": [
                f"PaymentMandate.modality={ap2_contract.payment.modality.value}",
                f"CartMandate.amount={ap2_contract.cart.amount}",
            ],
            "block_transaction": [
                f"DecisionOutcome.result={ap2_contract.decision.result}",
                f"DecisionOutcome.risk_score={ap2_contract.decision.risk_score}",
            ],
            "micro_deposit_verification": [
                f"PaymentMandate.modality={ap2_contract.payment.modality.value}",
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
            ],
            "process_payment": [
                f"DecisionOutcome.result={ap2_contract.decision.result}",
                f"PaymentMandate.modality={ap2_contract.payment.modality.value}",
            ],
            "send_confirmation": [
                f"IntentMandate.channel={ap2_contract.intent.channel.value}",
                f"DecisionOutcome.result={ap2_contract.decision.result}",
            ],
        }

        if action_type in action_field_mapping:
            citations = action_field_mapping[action_type]

        # Validate citations against guardrails
        validated_citations = []
        for citation in citations:
            if self._validate_field_citation(citation):
                validated_citations.append(citation)

        return validated_citations

    def _validate_field_citation(self, citation: str) -> bool:
        """
        Validate that a field citation references a real AP2 field.

        Args:
            citation: Field citation string (e.g., "CartMandate.amount=100.00")

        Returns:
            True if citation is valid, False otherwise
        """
        try:
            # Extract field path from citation
            if "=" in citation:
                field_path = citation.split("=")[0]
            else:
                field_path = citation

            # Convert to internal field path format
            internal_path = self._convert_to_internal_path(field_path)

            # Check against guardrails
            return internal_path in self.field_guardrails

        except Exception:
            return False

    def _convert_to_internal_path(self, field_path: str) -> str:
        """Convert external field path to internal format."""
        # Convert "CartMandate.amount" to "cart.amount"
        # Convert "IntentMandate.channel" to "intent.channel"
        # etc.

        path_mapping = {
            "CartMandate": "cart",
            "IntentMandate": "intent",
            "PaymentMandate": "payment",
            "DecisionOutcome": "decision",
            "SigningInfo": "signing",
        }

        parts = field_path.split(".")
        if len(parts) >= 2:
            mandate_type = parts[0]
            if mandate_type in path_mapping:
                internal_mandate = path_mapping[mandate_type]
                field_name = ".".join(parts[1:])
                return f"{internal_mandate}.{field_name}"

        return field_path.lower()

    def explain_decision_legacy(
        self, decision_result: str, reasons: list[str], actions: list[str], context: dict[str, Any]
    ) -> str:
        """
        Generate explanation for legacy decision format.

        Args:
            decision_result: Decision result (APPROVE/REVIEW/DECLINE)
            reasons: List of reason strings
            actions: List of action strings
            context: Additional context data

        Returns:
            Human-readable explanation
        """
        explanation_parts = []

        # Add decision result
        explanation_parts.append(f"Decision: {decision_result}")

        # Add reasons with context
        if reasons:
            for reason in reasons:
                explanation_parts.append(f"Reason: {reason}")

        # Add actions with context
        if actions:
            for action in actions:
                explanation_parts.append(f"Action: {action}")

        # Add key context fields
        context_fields = []
        if "cart_total" in context:
            context_fields.append(f"cart_total={context['cart_total']}")
        if "currency" in context:
            context_fields.append(f"currency={context['currency']}")
        if "rail" in context:
            context_fields.append(f"rail={context['rail']}")
        if "channel" in context:
            context_fields.append(f"channel={context['channel']}")

        if context_fields:
            explanation_parts.append(f"Context: {', '.join(context_fields)}")

        return ". ".join(explanation_parts) + "."


# Global AP2 NLG explainer instance
_ap2_nlg_explainer: Optional[AP2NLGExplainer] = None


def get_ap2_nlg_explainer() -> AP2NLGExplainer:
    """Get the global AP2 NLG explainer instance."""
    global _ap2_nlg_explainer
    if _ap2_nlg_explainer is None:
        _ap2_nlg_explainer = AP2NLGExplainer()
    return _ap2_nlg_explainer


def explain_ap2_decision(ap2_contract: AP2DecisionContract) -> str:
    """
    Generate natural language explanation for AP2 decision.

    Args:
        ap2_contract: AP2 decision contract to explain

    Returns:
        Human-readable explanation with AP2 field citations
    """
    explainer = get_ap2_nlg_explainer()
    return explainer.explain_decision(ap2_contract)


def explain_legacy_decision(
    decision_result: str, reasons: list[str], actions: list[str], context: dict[str, Any]
) -> str:
    """
    Generate explanation for legacy decision format.

    Args:
        decision_result: Decision result
        reasons: List of reason strings
        actions: List of action strings
        context: Additional context data

    Returns:
        Human-readable explanation
    """
    explainer = get_ap2_nlg_explainer()
    return explainer.explain_decision_legacy(decision_result, reasons, actions, context)
