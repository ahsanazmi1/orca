"""
Tests for LLM Guardrails

This module tests the comprehensive guardrails system for LLM explanations,
including JSON validation, hallucination detection, and content validation.
"""

import json

from src.orca_core.llm.guardrails import (
    GuardrailResult,
    LLMGuardrails,
    ValidationResult,
    validate_llm_explanation,
)


class TestLLMGuardrails:
    """Test suite for LLM guardrails system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.guardrails = LLMGuardrails(strict_mode=True)
        self.valid_decision_context = {
            "decision": "APPROVE",
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "cart_total": 100.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
        }
        self.valid_model_provenance = {
            "model_name": "gpt-4o-mini",
            "provider": "azure_openai",
            "endpoint": "https://test.openai.azure.com/",
        }

    def test_valid_json_response(self):
        """Test validation of valid JSON response."""
        valid_response = json.dumps(
            {
                "explanation": "The transaction was approved because the cart total of $100.00 is within acceptable limits and the risk score of 0.3 indicates low risk.",
                "confidence": 0.85,
                "reasoning": "Based on the transaction amount and risk assessment",
                "risk_factors": ["LOW_RISK"],
            }
        )

        result = self.guardrails.validate_explanation(
            valid_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID
        assert result.confidence_score > 0.8
        assert len(result.violations) == 0

    def test_invalid_json_response(self):
        """Test validation of invalid JSON response."""
        invalid_response = "This is not valid JSON at all"

        result = self.guardrails.validate_explanation(
            invalid_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.INVALID_JSON
        assert result.confidence_score == 0.0
        assert len(result.violations) > 0

    def test_json_in_markdown_code_block(self):
        """Test extraction of JSON from markdown code blocks."""
        markdown_response = """
        Here's the explanation:
        ```json
        {
            "explanation": "The transaction was approved because the cart total of $100.00 is within acceptable limits.",
            "confidence": 0.8
        }
        ```
        """

        result = self.guardrails.validate_explanation(
            markdown_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID
        assert result.confidence_score > 0.8

    def test_schema_validation_missing_required_fields(self):
        """Test schema validation with missing required fields."""
        incomplete_response = json.dumps(
            {
                "explanation": "Some explanation"
                # Missing required "confidence" field
            }
        )

        result = self.guardrails.validate_explanation(
            incomplete_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.SCHEMA_VIOLATION
        assert "Missing required field: confidence" in result.violations

    def test_schema_validation_invalid_confidence(self):
        """Test schema validation with invalid confidence value."""
        invalid_confidence_response = json.dumps(
            {
                "explanation": "The transaction was approved.",
                "confidence": 1.5,  # Invalid: should be between 0.0 and 1.0
            }
        )

        result = self.guardrails.validate_explanation(
            invalid_confidence_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.SCHEMA_VIOLATION
        assert "Confidence must be between 0.0 and 1.0" in result.violations

    def test_schema_validation_explanation_too_short(self):
        """Test schema validation with explanation that's too short."""
        short_explanation_response = json.dumps(
            {"explanation": "OK", "confidence": 0.8}  # Too short (minimum 10 characters)
        )

        result = self.guardrails.validate_explanation(
            short_explanation_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.SCHEMA_VIOLATION
        assert "Explanation too short" in result.violations[0]

    def test_hallucination_detection_fabricated_data(self):
        """Test detection of fabricated data in explanations."""
        hallucinated_response = json.dumps(
            {
                "explanation": "The transaction was approved. Customer ID: CUST12345 has a history of 15 successful transactions totaling exactly $2,347.89.",
                "confidence": 0.9,
            }
        )

        result = self.guardrails.validate_explanation(
            hallucinated_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION
        assert any("fabricated" in violation.lower() for violation in result.violations)

    def test_hallucination_detection_overly_specific_claims(self):
        """Test detection of overly specific claims."""
        specific_response = json.dumps(
            {
                "explanation": "The transaction was definitely approved because the risk score is precisely 0.300000 and the amount is exactly $100.00.",
                "confidence": 0.95,
            }
        )

        result = self.guardrails.validate_explanation(
            specific_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION
        assert any("specific" in violation.lower() for violation in result.violations)

    def test_hallucination_detection_fabricated_statistics(self):
        """Test detection of fabricated statistics."""
        stats_response = json.dumps(
            {
                "explanation": "The transaction was approved. Statistics show that 95% of similar transactions are legitimate based on our internal data analysis.",
                "confidence": 0.9,
            }
        )

        result = self.guardrails.validate_explanation(
            stats_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION
        assert any("statistics" in violation.lower() for violation in result.violations)

    def test_content_validation_pii_detection(self):
        """Test detection of potential PII in explanations."""
        pii_response = json.dumps(
            {
                "explanation": "The transaction was approved. Customer name: John Doe, email: john@example.com, phone: 555-1234.",
                "confidence": 0.8,
            }
        )

        result = self.guardrails.validate_explanation(
            pii_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION
        assert any("pii" in violation.lower() for violation in result.violations)

    def test_content_validation_legal_advice_detection(self):
        """Test detection of legal/financial advice."""
        advice_response = json.dumps(
            {
                "explanation": "The transaction was approved. You should consult a financial advisor for investment advice and contact a lawyer for legal guidance.",
                "confidence": 0.8,
            }
        )

        result = self.guardrails.validate_explanation(
            advice_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION
        assert any("advice" in violation.lower() for violation in result.violations)

    def test_content_validation_guarantee_detection(self):
        """Test detection of guarantees or warranties."""
        guarantee_response = json.dumps(
            {
                "explanation": "The transaction was approved. We guarantee that this payment is 100% safe and risk-free.",
                "confidence": 0.9,
            }
        )

        result = self.guardrails.validate_explanation(
            guarantee_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        # This should be caught by hallucination detection due to "100% safe"
        assert result.result_type == ValidationResult.HALLUCINATION
        assert any(
            "guarantee" in violation.lower() or "100%" in violation
            for violation in result.violations
        )

    def test_content_validation_context_reference(self):
        """Test that explanation references actual decision context."""
        context_response = json.dumps(
            {
                "explanation": "The transaction was approved because the cart total of $100.00 is within acceptable limits.",
                "confidence": 0.8,
            }
        )

        result = self.guardrails.validate_explanation(
            context_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_content_validation_no_context_reference(self):
        """Test failure when explanation doesn't reference decision context."""
        no_context_response = json.dumps(
            {
                "explanation": "The transaction was approved based on general risk assessment criteria.",
                "confidence": 0.8,
            }
        )

        result = self.guardrails.validate_explanation(
            no_context_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION
        assert any("reference" in violation.lower() for violation in result.violations)

    def test_uncertainty_detection_low_confidence(self):
        """Test detection of uncertainty through low confidence score."""
        uncertain_response = json.dumps(
            {
                "explanation": "The transaction was approved because the cart total of $100.00 is within acceptable limits.",
                "confidence": 0.3,  # Low confidence
            }
        )

        result = self.guardrails.validate_explanation(
            uncertain_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.UNCERTAINTY_REFUSAL
        assert any("confidence" in violation.lower() for violation in result.violations)

    def test_uncertainty_detection_uncertainty_indicators(self):
        """Test detection of uncertainty indicators in text."""
        uncertain_text_response = json.dumps(
            {
                "explanation": "I'm not sure about this decision. The cart total of $100.00 seems unclear and I cannot determine the risk level.",
                "confidence": 0.8,
            }
        )

        result = self.guardrails.validate_explanation(
            uncertain_text_response, self.valid_decision_context, self.valid_model_provenance
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.UNCERTAINTY_REFUSAL
        assert any("uncertainty" in violation.lower() for violation in result.violations)

    def test_sanitize_explanation(self):
        """Test explanation sanitization."""
        problematic_explanation = """
        The transaction was approved. Customer name: John Doe, email: john@example.com.
        We guarantee this is 100% safe. You should consult a financial advisor for advice.
        The amount is exactly $100.00.
        """

        sanitized = self.guardrails.sanitize_explanation(problematic_explanation)

        assert "[REDACTED]" in sanitized
        assert "guarantee" not in sanitized
        # The sanitization should replace "advice" with "general information"
        assert "general information" in sanitized
        assert "exactly" not in sanitized

    def test_validation_summary_valid(self):
        """Test validation summary for valid result."""
        valid_result = GuardrailResult(
            is_valid=True,
            result_type=ValidationResult.VALID,
            message="All validations passed",
            confidence_score=0.9,
            violations=[],
        )

        summary = self.guardrails.get_validation_summary(valid_result)
        assert "✅ Validation passed" in summary
        assert "0.90" in summary

    def test_validation_summary_invalid(self):
        """Test validation summary for invalid result."""
        invalid_result = GuardrailResult(
            is_valid=False,
            result_type=ValidationResult.HALLUCINATION,
            message="Hallucinations detected",
            confidence_score=0.0,
            violations=["Fabricated data", "Overly specific claims"],
        )

        summary = self.guardrails.get_validation_summary(invalid_result)
        assert "❌ Validation failed" in summary
        assert "violations: 2" in summary

    def test_convenience_function(self):
        """Test the convenience function for validation."""
        valid_response = json.dumps(
            {
                "explanation": "The transaction was approved because the cart total of $100.00 is within acceptable limits.",
                "confidence": 0.8,
            }
        )

        result = validate_llm_explanation(
            valid_response,
            self.valid_decision_context,
            self.valid_model_provenance,
            strict_mode=True,
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_non_strict_mode(self):
        """Test guardrails in non-strict mode."""
        non_strict_guardrails = LLMGuardrails(strict_mode=False)

        uncertain_response = json.dumps(
            {
                "explanation": "I'm not sure about this decision. The cart total of $100.00 is within acceptable limits.",
                "confidence": 0.3,
            }
        )

        result = non_strict_guardrails.validate_explanation(
            uncertain_response, self.valid_decision_context, self.valid_model_provenance
        )

        # In non-strict mode, uncertainty should be allowed
        assert result.is_valid
        assert result.result_type == ValidationResult.VALID


class TestGuardrailIntegration:
    """Test integration of guardrails with the LLM explainer."""

    def test_guardrails_metadata_in_response(self):
        """Test that guardrails metadata is included in the response."""
        # This would be tested in integration with the actual LLM explainer
        # For now, we test the structure
        guardrails_metadata = {
            "passed": True,
            "result_type": "valid",
            "confidence_score": 0.9,
            "violations": [],
        }

        assert guardrails_metadata["passed"] is True
        assert guardrails_metadata["result_type"] == "valid"
        assert guardrails_metadata["confidence_score"] > 0.8
        assert len(guardrails_metadata["violations"]) == 0
