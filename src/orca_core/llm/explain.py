"""
LLM Explanation Module for Orca Core

This module provides Azure OpenAI integration for generating
human-readable explanations of decision engine outputs with
proper JSON schema enforcement and model provenance tracking.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Azure OpenAI imports
from openai import AzureOpenAI  # type: ignore

# Import guardrails
from .guardrails import ValidationResult, validate_llm_explanation

# Import negotiation models for rail selection explanations
try:
    from ..models import NegotiationRequest, NegotiationResponse, RailEvaluation
    NEGOTIATION_MODELS_AVAILABLE = True
except ImportError:
    NEGOTIATION_MODELS_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExplanationRequest:
    """Request structure for LLM explanation generation."""

    decision: str
    risk_score: float
    reason_codes: list[str]
    transaction_data: dict[str, Any]
    model_type: str
    model_version: str
    rules_evaluated: list[str]
    meta_data: dict[str, Any]


@dataclass
class ExplanationResponse:
    """Response structure for LLM explanation generation."""

    explanation: str
    confidence: float
    model_provenance: dict[str, Any]
    processing_time_ms: int
    tokens_used: int


class AzureOpenAIClient:
    """Azure OpenAI client with configuration validation."""

    def __init__(self) -> None:
        """Initialize Azure OpenAI client with graceful fallback for missing configuration."""
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

        # Check if configuration is missing
        self.is_configured = bool(self.endpoint and self.api_key)

        if not self.is_configured:
            logger.warning(
                "⚠️ Azure OpenAI configuration missing. LLM explanations will return 503. "
                "Please run 'make configure-azure-openai' to set up your Azure OpenAI credentials."
            )
            self.client = None
            return

        # Initialize client
        if self.endpoint is None:
            raise ValueError("Azure OpenAI endpoint not configured")
        self.client = AzureOpenAI(
            api_key=self.api_key, api_version="2024-06-01", azure_endpoint=self.endpoint
        )

        logger.info(f"✅ Azure OpenAI client initialized with deployment: {self.deployment}")

    def generate_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        """
        Generate human-readable explanation using Azure OpenAI.

        Args:
            request: Explanation request with decision context

        Returns:
            ExplanationResponse with generated explanation and metadata
        """
        # Check if client is configured
        if not self.is_configured or not self.client:
            raise ValueError(
                "Azure OpenAI not configured. LLM explanations unavailable. "
                "Please configure Azure OpenAI credentials to enable LLM explanations."
            )

        start_time = datetime.now()

        try:
            # Construct the prompt
            prompt = self._build_explanation_prompt(request)

            # Make API call
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent output
                max_tokens=300,  # Limit token usage
                response_format={"type": "json_object"},  # Enforce JSON output
            )

            # Get raw response for guardrails validation
            raw_response = response.choices[0].message.content

            # Prepare decision context for guardrails
            decision_context = {
                "decision": request.decision,
                "risk_score": request.risk_score,
                "reason_codes": request.reason_codes,
                "cart_total": request.transaction_data.get("amount", 0),
                "currency": request.transaction_data.get("currency", "USD"),
                "rail": request.transaction_data.get("rail", "Card"),
                "channel": request.transaction_data.get("channel", "online"),
            }

            # Build model provenance
            model_provenance: dict[str, Any] = {
                "model_name": self.deployment,
                "provider": "azure_openai",
                "endpoint": self.endpoint,
                "api_version": "2024-06-01",
                "temperature": 0.1,
                "max_tokens": 300,
                "response_format": "json_object",
                "timestamp": datetime.now().isoformat(),
                "request_id": response.id if hasattr(response, "id") else None,
            }

            # Apply guardrails validation
            if raw_response is None:
                raise ValueError("No response received from Azure OpenAI")
            guardrail_result = validate_llm_explanation(
                raw_response=raw_response,
                decision_context=decision_context,
                model_provenance=model_provenance,
                strict_mode=True,
            )

            if not guardrail_result.is_valid:
                logger.warning(f"🚨 Guardrails validation failed: {guardrail_result.message}")
                logger.warning(f"   Violations: {guardrail_result.violations}")

                # In strict mode, fall back to mock explanation
                if guardrail_result.result_type in [
                    ValidationResult.HALLUCINATION,
                    ValidationResult.CONTENT_VIOLATION,
                ]:
                    logger.warning("🔄 Falling back to mock explanation due to guardrails failure")
                    return self._generate_mock_explanation(request)
                else:
                    # For other validation failures, try to sanitize and continue
                    logger.warning("🔄 Attempting to sanitize response and continue")
                    if guardrail_result.sanitized_content:
                        raw_response = guardrail_result.sanitized_content

            # Parse validated response
            if raw_response is None:
                raise ValueError("No response content to parse")
            explanation_data = json.loads(raw_response)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Extract token usage
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Add guardrails metadata to model provenance
            model_provenance["guardrails_validation"] = {
                "passed": guardrail_result.is_valid,
                "result_type": str(guardrail_result.result_type.value),
                "confidence_score": guardrail_result.confidence_score,
                "violations": guardrail_result.violations,
            }

            return ExplanationResponse(
                explanation=explanation_data.get("explanation", ""),
                confidence=explanation_data.get("confidence", 0.0),
                model_provenance=model_provenance,
                processing_time_ms=int(processing_time),
                tokens_used=tokens_used,
            )

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from Azure OpenAI: {e}") from e
        except Exception as e:
            logger.error(f"❌ Azure OpenAI API error: {e}")
            # Fallback to mock explanation for testing
            logger.warning("🔄 Falling back to mock explanation for testing")
            return self._generate_mock_explanation(request)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for explanation generation."""
        return """You are an expert financial risk analyst for Orca Core, a payment decision engine.
Your task is to generate clear, concise, and accurate explanations for payment decisions.

CRITICAL REQUIREMENTS:
1. You MUST respond with valid JSON only
2. Follow the exact schema provided
3. Be factual and avoid speculation
4. Use professional, clear language
5. Focus on the key risk factors that influenced the decision

JSON SCHEMA:
{
  "explanation": "string - Clear explanation of the decision (max 200 words)",
  "confidence": "number - Confidence score between 0.0 and 1.0",
  "key_factors": ["string"] - List of 2-3 most important risk factors
}

GUARDRAILS:
- Do not include sensitive customer information
- Do not make claims about future outcomes
- Do not provide financial advice
- Keep explanations factual and objective
- Use standard financial terminology"""

    def _build_explanation_prompt(self, request: ExplanationRequest) -> str:
        """Build the user prompt for explanation generation."""
        return f"""Generate a clear explanation for this payment decision:

DECISION: {request.decision}
RISK SCORE: {request.risk_score:.3f}
REASON CODES: {", ".join(request.reason_codes)}
MODEL TYPE: {request.model_type} (v{request.model_version})

TRANSACTION CONTEXT:
- Amount: ${request.transaction_data.get("amount", 0):.2f}
- Channel: {request.transaction_data.get("channel", "unknown")}
- Rail: {request.transaction_data.get("rail", "unknown")}

RULES EVALUATED: {", ".join(request.rules_evaluated) if request.rules_evaluated else "None"}

Please provide a JSON response following the schema above."""

    def _generate_mock_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        """Generate a mock explanation for testing when Azure OpenAI is not available."""
        start_time = datetime.now()

        # Generate contextual explanation based on decision and risk factors
        if request.decision == "APPROVE":
            explanation = f"Transaction approved. The payment of ${request.transaction_data.get('amount', 0):.2f} was processed successfully through {request.transaction_data.get('channel', 'unknown')} channel. Risk assessment indicates acceptable risk level."
            confidence = 0.85
        elif request.decision == "DECLINE":
            explanation = f"Transaction declined due to elevated risk factors. Risk score of {request.risk_score:.3f} exceeds acceptable thresholds. Key concerns include: {', '.join(request.reason_codes[:3])}."
            confidence = 0.90
        else:  # REVIEW
            explanation = f"Transaction flagged for manual review. Risk score of {request.risk_score:.3f} requires additional verification. Factors contributing to review: {', '.join(request.reason_codes[:2])}."
            confidence = 0.75

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Build mock model provenance
        model_provenance = {
            "model_name": "mock-explainer",
            "provider": "orca_core",
            "endpoint": "mock",
            "api_version": "1.0.0",
            "temperature": 0.1,
            "max_tokens": 300,
            "response_format": "json_object",
            "timestamp": datetime.now().isoformat(),
            "request_id": f"mock-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "fallback_mode": True,
        }

        return ExplanationResponse(
            explanation=explanation,
            confidence=confidence,
            model_provenance=model_provenance,
            processing_time_ms=int(processing_time),
            tokens_used=0,  # Mock doesn't use tokens
        )


class LLMExplainer:
    """Main LLM explanation service."""

    def __init__(self) -> None:
        """Initialize LLM explainer with Azure OpenAI client."""
        self.client = AzureOpenAIClient()
        self.is_available = self.client.is_configured

        if self.is_available:
            logger.info("✅ LLM Explainer initialized successfully")
        else:
            logger.warning("⚠️ LLM Explainer not available - Azure OpenAI not configured")

    def explain_decision(
        self,
        decision: str,
        risk_score: float,
        reason_codes: list[str],
        transaction_data: dict[str, Any],
        model_type: str = "unknown",
        model_version: str = "unknown",
        rules_evaluated: list[str] | None = None,
        meta_data: dict[str, Any] | None = None,
    ) -> ExplanationResponse | None:
        """
        Generate explanation for a decision.

        Args:
            decision: The decision made (APPROVE, DECLINE, REVIEW)
            risk_score: Risk score from ML model
            reason_codes: List of reason codes
            transaction_data: Transaction context data
            model_type: Type of ML model used
            model_version: Version of ML model
            rules_evaluated: List of rules that were evaluated
            meta_data: Additional metadata

        Returns:
            ExplanationResponse if successful, None if LLM not available
        """
        if not self.is_available:
            logger.warning("⚠️ LLM Explainer not available, skipping explanation generation")
            # Return a 503-style response indicating service unavailable
            return ExplanationResponse(
                explanation="LLM explanation service unavailable. Azure OpenAI not configured.",
                confidence=0.0,
                model_provenance={
                    "model_name": "unavailable",
                    "provider": "none",
                    "status": "503_service_unavailable",
                    "message": "Please configure Azure OpenAI credentials to enable LLM explanations.",
                },
                processing_time_ms=0,
                tokens_used=0,
            )

        try:
            # Build request
            request = ExplanationRequest(
                decision=decision,
                risk_score=risk_score,
                reason_codes=reason_codes,
                transaction_data=transaction_data,
                model_type=model_type,
                model_version=model_version,
                rules_evaluated=rules_evaluated or [],
                meta_data=meta_data or {},
            )

            # Generate explanation
            response = self.client.generate_explanation(request)

            logger.info(
                f"✅ Generated explanation in {response.processing_time_ms}ms using {response.tokens_used} tokens"
            )
            return response

        except Exception as e:
            logger.error(f"❌ Failed to generate explanation: {e}")
            return None

    def is_configured(self) -> bool:
        """Check if LLM explainer is properly configured."""
        return self.is_available

    def get_configuration_status(self) -> dict[str, Any]:
        """Get configuration status for debugging."""
        if not self.is_available:
            return {
                "status": "not_configured",
                "message": "Azure OpenAI configuration missing. Run 'make configure-azure-openai'",
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": "***" if os.getenv("AZURE_OPENAI_API_KEY") else None,
                "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            }

        return {
            "status": "configured",
            "endpoint": self.client.endpoint,
            "deployment": self.client.deployment,
            "api_key": "***" if self.client.api_key else None,
        }


# Global explainer instance
_explainer = None


def get_llm_explainer() -> LLMExplainer:
    """Get global LLM explainer instance."""
    global _explainer
    if _explainer is None:
        _explainer = LLMExplainer()
    return _explainer


def explain_decision_llm(
    decision: str,
    risk_score: float,
    reason_codes: list[str],
    transaction_data: dict[str, Any],
    model_type: str = "unknown",
    model_version: str = "unknown",
    rules_evaluated: list[str] | None = None,
    meta_data: dict[str, Any] | None = None,
) -> ExplanationResponse | None:
    """
    Generate LLM explanation for a decision.

    This is the main entry point for LLM explanation generation.
    """
    explainer = get_llm_explainer()
    return explainer.explain_decision(
        decision=decision,
        risk_score=risk_score,
        reason_codes=reason_codes,
        transaction_data=transaction_data,
        model_type=model_type,
        model_version=model_version,
        rules_evaluated=rules_evaluated,
        meta_data=meta_data,
    )


def is_llm_configured() -> bool:
    """Check if LLM explanation service is configured."""
    explainer = get_llm_explainer()
    return explainer.is_configured()


def get_llm_configuration_status() -> dict[str, Any]:
    """Get LLM configuration status."""
    explainer = get_llm_explainer()
    return explainer.get_configuration_status()


# Phase 3 - Rail Selection LLM Explanations

def explain_rail_selection_llm(
    negotiation_response: NegotiationResponse,
    request: NegotiationRequest
) -> str:
    """
    Generate LLM-powered explanation for rail selection in negotiation.
    
    Args:
        negotiation_response: Response from rail negotiation
        request: Original negotiation request
        
    Returns:
        Human-readable explanation of rail selection reasoning
    """
    if not NEGOTIATION_MODELS_AVAILABLE:
        return "Rail selection explanation not available (models not imported)"
    
    explainer = get_llm_explainer()
    if not explainer.is_configured():
        return "LLM explanation service not configured"
    
    # Build context for LLM explanation
    optimal_rail = negotiation_response.optimal_rail
    optimal_evaluation = next(
        (e for e in negotiation_response.rail_evaluations if e.rail_type == optimal_rail), 
        None
    )
    
    if not optimal_evaluation:
        return f"Selected {optimal_rail} as default payment rail."
    
    # Create detailed context for LLM
    context_data = {
        "transaction": {
            "cart_total": request.cart_total,
            "currency": request.currency,
            "channel": request.channel,
            "available_rails": request.available_rails,
        },
        "weights": {
            "cost_weight": request.cost_weight,
            "speed_weight": request.speed_weight,
            "risk_weight": request.risk_weight,
        },
        "optimal_rail": {
            "rail_type": optimal_evaluation.rail_type,
            "cost_score": optimal_evaluation.cost_score,
            "speed_score": optimal_evaluation.speed_score,
            "risk_score": optimal_evaluation.risk_score,
            "composite_score": optimal_evaluation.composite_score,
            "base_cost": optimal_evaluation.base_cost,
            "settlement_days": optimal_evaluation.settlement_days,
            "ml_risk_score": optimal_evaluation.ml_risk_score,
            "cost_factors": optimal_evaluation.cost_factors,
            "speed_factors": optimal_evaluation.speed_factors,
            "risk_factors": optimal_evaluation.risk_factors,
        },
        "alternative_rails": [
            {
                "rail_type": eval.rail_type,
                "composite_score": eval.composite_score,
                "base_cost": eval.base_cost,
                "risk_score": eval.risk_score,
                "cost_factors": eval.cost_factors,
                "risk_factors": eval.risk_factors,
            }
            for eval in negotiation_response.rail_evaluations
            if eval.rail_type != optimal_rail
        ],
        "ml_model": {
            "model_used": negotiation_response.ml_model_used,
            "risk_score": optimal_evaluation.ml_risk_score,
        }
    }
    
    # Create explanation request
    explanation_request = ExplanationRequest(
        decision=f"SELECT_RAIL_{optimal_rail}",
        risk_score=optimal_evaluation.ml_risk_score,
        reason_codes=optimal_evaluation.risk_factors,
        transaction_data=context_data,
        model_type=negotiation_response.ml_model_used,
        model_version="1.0",
        rules_evaluated=[],  # Not applicable for rail selection
        meta_data=negotiation_response.negotiation_metadata,
    )
    
    try:
        # Generate LLM explanation
        response = explainer.explain_decision(explanation_request)
        
        if response and response.explanation:
            # Create enhanced JSON explanation with detailed breakdown
            enhanced_explanation = {
                "reason": response.explanation,
                "key_signals": {
                    "cost_signals": optimal_evaluation.cost_factors,
                    "speed_signals": optimal_evaluation.speed_factors,
                    "risk_signals": optimal_evaluation.risk_factors,
                    "ml_risk_score": optimal_evaluation.ml_risk_score,
                    "composite_score": optimal_evaluation.composite_score,
                },
                "mitigation": {
                    "declined_rails": [
                        {
                            "rail": eval.rail_type,
                            "reason": f"Composite score {eval.composite_score:.3f} vs {optimal_evaluation.composite_score:.3f}",
                            "primary_factors": eval.cost_factors + eval.risk_factors,
                        }
                        for eval in negotiation_response.rail_evaluations
                        if eval.rail_type != optimal_rail
                    ],
                    "risk_mitigation": f"ML risk score {optimal_evaluation.ml_risk_score:.3f} within acceptable threshold",
                },
                "confidence": {
                    "score_difference": optimal_evaluation.composite_score - max(
                        [eval.composite_score for eval in negotiation_response.rail_evaluations 
                         if eval.rail_type != optimal_rail], default=0.0
                    ),
                    "decision_strength": "high" if optimal_evaluation.composite_score > 0.7 else "medium" if optimal_evaluation.composite_score > 0.5 else "low",
                    "alternative_count": len([e for e in negotiation_response.rail_evaluations if e.rail_type != optimal_rail]),
                }
            }
            
            # Return both human-readable and structured explanation
            rail_explanation = f"Rail Selection Analysis: {response.explanation}"
            
            # Add specific rail reasoning
            if optimal_evaluation.cost_score > 0.8:
                rail_explanation += f" {optimal_rail} was chosen primarily for cost efficiency at {optimal_evaluation.base_cost:.1f} basis points."
            
            if optimal_evaluation.speed_score > 0.8:
                rail_explanation += f" Settlement speed is optimal at {optimal_evaluation.settlement_days} day(s)."
            
            if optimal_evaluation.risk_score < 0.3:
                rail_explanation += f" Risk profile is favorable with ML score of {optimal_evaluation.ml_risk_score:.3f}."
            
            # Add structured JSON to explanation
            rail_explanation += f"\n\nStructured Analysis: {json.dumps(enhanced_explanation, indent=2)}"
            
            return rail_explanation
        else:
            return f"LLM explanation failed, using fallback: {negotiation_response.explanation}"
            
    except Exception as e:
        logger.error(f"LLM rail selection explanation failed: {e}")
        return f"LLM explanation unavailable: {negotiation_response.explanation}"


def explain_rail_decline_llm(
    declined_rail: str,
    decline_reasons: list[str],
    optimal_rail: str,
    ml_risk_score: float
) -> str:
    """
    Generate LLM-powered explanation for why a rail was declined.
    
    Args:
        declined_rail: Rail type that was declined
        decline_reasons: List of reasons for decline
        optimal_rail: Rail that was selected instead
        ml_risk_score: ML risk score used in evaluation
        
    Returns:
        Human-readable explanation of rail decline reasoning
    """
    if not NEGOTIATION_MODELS_AVAILABLE:
        return f"{declined_rail} declined due to: {', '.join(decline_reasons)}"
    
    explainer = get_llm_explainer()
    if not explainer.is_configured():
        return f"{declined_rail} declined due to: {', '.join(decline_reasons)}"
    
    # Create context for decline explanation
    context_data = {
        "declined_rail": declined_rail,
        "decline_reasons": decline_reasons,
        "selected_rail": optimal_rail,
        "ml_risk_score": ml_risk_score,
        "analysis_type": "rail_decline",
    }
    
    explanation_request = ExplanationRequest(
        decision=f"DECLINE_RAIL_{declined_rail}",
        risk_score=ml_risk_score,
        reason_codes=decline_reasons,
        transaction_data=context_data,
        model_type="rail_negotiation",
        model_version="1.0",
        rules_evaluated=[],
        meta_data={"decline_analysis": True},
    )
    
    try:
        response = explainer.explain_decision(explanation_request)
        
        if response and response.explanation:
            return f"Rail Decline Analysis: {response.explanation}"
        else:
            return f"{declined_rail} declined due to: {', '.join(decline_reasons)}"
            
    except Exception as e:
        logger.error(f"LLM rail decline explanation failed: {e}")
        return f"{declined_rail} declined due to: {', '.join(decline_reasons)}"
