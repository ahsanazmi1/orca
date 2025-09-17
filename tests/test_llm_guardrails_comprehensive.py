"""Comprehensive tests for LLM guardrails and validation."""

import json

from orca_core.llm.guardrails import (
    GuardrailResult,
    LLMGuardrails,
    ValidationResult,
    validate_llm_explanation,
)


class TestLLMGuardrailsComprehensive:
    """Comprehensive tests for LLM guardrails system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.guardrails = LLMGuardrails(strict_mode=True)
        self.decision_context = {
            "decision": "APPROVE",
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "cart_total": 100.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
        }

    def test_json_parsing_valid_json(self):
        """Test JSON parsing with valid JSON."""
        valid_json = '{"explanation": "Transaction approved", "confidence": 0.8}'
        result = self.guardrails._extract_json_from_markdown(valid_json)

        assert result is not None
        assert result["explanation"] == "Transaction approved"
        assert result["confidence"] == 0.8

    def test_json_parsing_markdown_code_block(self):
        """Test JSON parsing from markdown code block."""
        markdown_json = """
        ```json
        {
            "explanation": "Transaction approved",
            "confidence": 0.8
        }
        ```
        """
        result = self.guardrails._extract_json_from_markdown(markdown_json)

        assert result is not None
        assert result["explanation"] == "Transaction approved"

    def test_json_parsing_invalid_json(self):
        """Test JSON parsing with invalid JSON."""
        invalid_json = (
            '{"explanation": "Transaction approved", "confidence": 0.8'  # Missing closing brace
        )
        result = self.guardrails._extract_json_from_markdown(invalid_json)

        assert result is None

    def test_json_schema_validation_valid(self):
        """Test JSON schema validation with valid data."""
        valid_data = {
            "explanation": "Transaction approved due to low risk factors",
            "confidence": 0.8,
            "key_factors": ["low_amount", "normal_velocity"],
        }

        result = self.guardrails._validate_schema(json.dumps(valid_data))

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_json_schema_validation_missing_fields(self):
        """Test JSON schema validation with missing required fields."""
        invalid_data = {
            "explanation": "Transaction approved"
            # Missing confidence and key_factors
        }

        result = self.guardrails._validate_schema(json.dumps(invalid_data))

        assert not result.is_valid
        assert result.result_type == ValidationResult.SCHEMA_VIOLATION

    def test_json_schema_validation_invalid_types(self):
        """Test JSON schema validation with invalid field types."""
        invalid_data = {
            "explanation": 123,  # Should be string
            "confidence": "high",  # Should be number
            "key_factors": "single_factor",  # Should be array
        }

        result = self.guardrails._validate_schema(json.dumps(invalid_data))

        assert not result.is_valid
        assert result.result_type == ValidationResult.SCHEMA_VIOLATION

    def test_hallucination_detection_fabricated_data(self):
        """Test hallucination detection for fabricated data."""
        hallucinated_text = json.dumps(
            {
                "explanation": "The transaction was processed at exactly 2:34:56 PM on January 15th, 2025",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._detect_hallucinations(hallucinated_text)

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION

    def test_hallucination_detection_fake_statistics(self):
        """Test hallucination detection for fake statistics."""
        hallucinated_text = json.dumps(
            {
                "explanation": "This transaction has a 99.7% probability of being fraudulent",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._detect_hallucinations(hallucinated_text)

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION

    def test_hallucination_detection_overly_specific_claims(self):
        """Test hallucination detection for overly specific claims."""
        hallucinated_text = json.dumps(
            {
                "explanation": "The customer has made exactly 47 transactions in the past 30 days",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._detect_hallucinations(hallucinated_text)

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION

    def test_hallucination_detection_valid_content(self):
        """Test hallucination detection with valid content."""
        valid_text = json.dumps(
            {
                "explanation": "The transaction was approved based on the risk assessment",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._detect_hallucinations(valid_text)

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_content_validation_pii_detection(self):
        """Test content validation for PII detection."""
        pii_text = json.dumps(
            {
                "explanation": "The customer John Smith (SSN: 123-45-6789) was approved",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._validate_content(pii_text, self.decision_context)

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION

    def test_content_validation_legal_advice(self):
        """Test content validation for legal advice."""
        legal_advice_text = json.dumps(
            {
                "explanation": "You should consult with a lawyer about this transaction",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._validate_content(legal_advice_text, self.decision_context)

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION

    def test_content_validation_guarantees(self):
        """Test content validation for guarantees."""
        guarantee_text = json.dumps(
            {
                "explanation": "This transaction is guaranteed to be safe and secure",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._validate_content(guarantee_text, self.decision_context)

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION

    def test_content_validation_context_reference(self):
        """Test content validation for context reference."""
        context_text = json.dumps(
            {
                "explanation": "The transaction for $100.00 was approved due to low risk",
                "confidence": 0.8,
            }
        )

        result = self.guardrails._validate_content(context_text, self.decision_context)

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_content_validation_missing_context_reference(self):
        """Test content validation with missing context reference."""
        no_context_text = json.dumps(
            {"explanation": "The transaction was processed successfully", "confidence": 0.8}
        )

        result = self.guardrails._validate_content(no_context_text, self.decision_context)

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION

    def test_uncertainty_detection_low_confidence(self):
        """Test uncertainty detection for low confidence scores."""
        uncertain_text = json.dumps(
            {
                "explanation": "I'm not sure about this decision, but it might be okay",
                "confidence": 0.3,
            }
        )

        result = self.guardrails._detect_uncertainty(uncertain_text)

        assert not result.is_valid
        assert result.result_type == ValidationResult.UNCERTAINTY_REFUSAL

    def test_uncertainty_detection_confidence_keywords(self):
        """Test uncertainty detection for confidence keywords."""
        uncertain_text = json.dumps(
            {"explanation": "This might be a good decision, but I'm uncertain", "confidence": 0.8}
        )

        result = self.guardrails._detect_uncertainty(uncertain_text)

        assert not result.is_valid
        assert result.result_type == ValidationResult.UNCERTAINTY_REFUSAL

    def test_uncertainty_detection_valid_confidence(self):
        """Test uncertainty detection with valid confidence."""
        confident_text = json.dumps(
            {"explanation": "The transaction was approved with high confidence", "confidence": 0.9}
        )

        result = self.guardrails._detect_uncertainty(confident_text)

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_sanitization_pii_redaction(self):
        """Test sanitization for PII redaction."""
        pii_text = "Customer John Smith (SSN: 123-45-6789) was approved"

        sanitized = self.guardrails.sanitize_explanation(pii_text)

        assert "John Smith" not in sanitized
        assert "123-45-6789" not in sanitized
        assert "[REDACTED NAME]" in sanitized
        assert "[REDACTED SSN]" in sanitized

    def test_sanitization_guarantee_replacement(self):
        """Test sanitization for guarantee replacement."""
        guarantee_text = "This transaction is guaranteed to be safe"

        sanitized = self.guardrails.sanitize_explanation(guarantee_text)

        assert "guaranteed" not in sanitized
        assert "indicate" in sanitized

    def test_sanitization_advice_replacement(self):
        """Test sanitization for advice replacement."""
        advice_text = "You should consult a lawyer for advice"

        sanitized = self.guardrails.sanitize_explanation(advice_text)

        assert "for advice" not in sanitized
        assert "for general information" in sanitized

    def test_sanitization_exact_replacement(self):
        """Test sanitization for exact replacement."""
        exact_text = "The amount was exactly $100.00"

        sanitized = self.guardrails.sanitize_explanation(exact_text)

        assert "exactly" not in sanitized
        assert "approximately" in sanitized

    def test_complete_validation_pipeline_valid(self):
        """Test complete validation pipeline with valid content."""
        valid_response = """
        ```json
        {
            "explanation": "The transaction for $100.00 was approved due to low risk factors",
            "confidence": 0.8,
            "key_factors": ["low_amount", "normal_velocity"]
        }
        ```
        """

        result = self.guardrails.validate_explanation(
            raw_response=valid_response,
            decision_context=self.decision_context,
            model_provenance={"model_name": "gpt-4o-mini"},
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID
        assert result.confidence_score > 0.8

    def test_complete_validation_pipeline_hallucination(self):
        """Test complete validation pipeline with hallucination."""
        hallucinated_response = """
        ```json
        {
            "explanation": "The transaction was processed at exactly 2:34:56 PM on January 15th, 2025",
            "confidence": 0.9,
            "key_factors": ["specific_timing"]
        }
        ```
        """

        result = self.guardrails.validate_explanation(
            raw_response=hallucinated_response,
            decision_context=self.decision_context,
            model_provenance={"model_name": "gpt-4o-mini"},
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION

    def test_complete_validation_pipeline_content_violation(self):
        """Test complete validation pipeline with content violation."""
        violation_response = """
        ```json
        {
            "explanation": "The transaction was processed successfully",
            "confidence": 0.8,
            "key_factors": ["success"]
        }
        ```
        """

        result = self.guardrails.validate_explanation(
            raw_response=violation_response,
            decision_context=self.decision_context,
            model_provenance={"model_name": "gpt-4o-mini"},
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.CONTENT_VIOLATION

    def test_complete_validation_pipeline_uncertainty(self):
        """Test complete validation pipeline with uncertainty."""
        uncertain_response = """
        ```json
        {
            "explanation": "I'm not sure about this $100.00 transaction decision, but it might be okay",
            "confidence": 0.3,
            "key_factors": ["uncertainty"]
        }
        ```
        """

        result = self.guardrails.validate_explanation(
            raw_response=uncertain_response,
            decision_context=self.decision_context,
            model_provenance={"model_name": "gpt-4o-mini"},
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.UNCERTAINTY_REFUSAL

    def test_validation_summary_generation(self):
        """Test validation summary generation."""
        result = GuardrailResult(
            is_valid=False,
            result_type=ValidationResult.HALLUCINATION,
            message="Potential hallucinations detected: Fabricated timing data",
            confidence_score=0.2,
            violations=["Fabricated timing data"],
            sanitized_content="The transaction was processed [REDACTED]",
        )

        summary = self.guardrails.get_validation_summary(result)

        assert "Validation failed" in summary
        assert "hallucinations detected" in summary
        assert "Fabricated timing data" in summary

    def test_strict_mode_vs_non_strict_mode(self):
        """Test strict mode vs non-strict mode behavior."""
        # Test strict mode
        strict_guardrails = LLMGuardrails(strict_mode=True)

        # Test non-strict mode
        non_strict_guardrails = LLMGuardrails(strict_mode=False)

        # Both should behave the same for valid content
        valid_response = """
        ```json
        {
            "explanation": "The transaction for $100.00 was approved",
            "confidence": 0.8,
            "key_factors": ["low_amount"]
        }
        ```
        """

        strict_result = strict_guardrails.validate_explanation(
            valid_response, self.decision_context, {}
        )

        non_strict_result = non_strict_guardrails.validate_explanation(
            valid_response, self.decision_context, {}
        )

        assert strict_result.is_valid == non_strict_result.is_valid

    def test_edge_cases_empty_response(self):
        """Test edge cases with empty response."""
        result = self.guardrails.validate_explanation(
            raw_response="", decision_context=self.decision_context, model_provenance={}
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.INVALID_JSON

    def test_edge_cases_none_response(self):
        """Test edge cases with None response."""
        result = self.guardrails.validate_explanation(
            raw_response=None, decision_context=self.decision_context, model_provenance={}
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.INVALID_JSON

    def test_edge_cases_malformed_json(self):
        """Test edge cases with malformed JSON."""
        malformed_response = '{"explanation": "Test", "confidence": 0.8'  # Missing closing brace

        result = self.guardrails.validate_explanation(
            raw_response=malformed_response,
            decision_context=self.decision_context,
            model_provenance={},
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.INVALID_JSON

    def test_edge_cases_very_long_response(self):
        """Test edge cases with very long response."""
        long_explanation = "This is a very long explanation for the $100.00 transaction. " * 1000
        long_response = f"""
        ```json
        {{
            "explanation": "{long_explanation}",
            "confidence": 0.8,
            "key_factors": ["length"]
        }}
        ```
        """

        result = self.guardrails.validate_explanation(
            raw_response=long_response, decision_context=self.decision_context, model_provenance={}
        )

        # Should fail due to length limit
        assert not result.is_valid
        assert result.result_type == ValidationResult.SCHEMA_VIOLATION

    def test_edge_cases_special_characters(self):
        """Test edge cases with special characters."""
        special_response = """
        ```json
        {
            "explanation": "Transaction for $100.00 approved with special chars: @#$%^&*()",
            "confidence": 0.8,
            "key_factors": ["special_chars"]
        }
        ```
        """

        result = self.guardrails.validate_explanation(
            raw_response=special_response,
            decision_context=self.decision_context,
            model_provenance={},
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_validation_with_different_decision_types(self):
        """Test validation with different decision types."""
        decision_types = ["APPROVE", "DECLINE", "REVIEW"]

        for decision in decision_types:
            context = self.decision_context.copy()
            context["decision"] = decision

            response = f"""
            ```json
            {{
                "explanation": "The transaction for $100.00 was {decision.lower()}ed",
                "confidence": 0.8,
                "key_factors": ["decision_type"]
            }}
            ```
            """

            result = self.guardrails.validate_explanation(
                raw_response=response, decision_context=context, model_provenance={}
            )

            assert result.is_valid
            assert result.result_type == ValidationResult.VALID

    def test_validation_with_different_risk_scores(self):
        """Test validation with different risk scores."""
        risk_scores = [0.1, 0.5, 0.9]

        for risk_score in risk_scores:
            context = self.decision_context.copy()
            context["risk_score"] = risk_score

            response = f"""
            ```json
            {{
                "explanation": "The transaction for $100.00 has a risk score of {risk_score}",
                "confidence": 0.8,
                "key_factors": ["risk_score"]
            }}
            ```
            """

            result = self.guardrails.validate_explanation(
                raw_response=response, decision_context=context, model_provenance={}
            )

            assert result.is_valid
            assert result.result_type == ValidationResult.VALID

    def test_validation_with_different_currencies(self):
        """Test validation with different currencies."""
        currencies = ["USD", "EUR", "GBP", "JPY"]

        for currency in currencies:
            context = self.decision_context.copy()
            context["currency"] = currency

            response = f"""
            ```json
            {{
                "explanation": "The transaction for $100.00 {currency} was approved",
                "confidence": 0.8,
                "key_factors": ["currency"]
            }}
            ```
            """

            result = self.guardrails.validate_explanation(
                raw_response=response, decision_context=context, model_provenance={}
            )

            assert result.is_valid
            assert result.result_type == ValidationResult.VALID


class TestValidateLLMExplanationFunction:
    """Test the validate_llm_explanation function."""

    def test_validate_llm_explanation_valid(self):
        """Test validate_llm_explanation function with valid input."""
        valid_response = """
        ```json
        {
            "explanation": "The transaction for $100.00 was approved",
            "confidence": 0.8,
            "key_factors": ["low_amount"]
        }
        ```
        """

        decision_context = {
            "decision": "APPROVE",
            "risk_score": 0.3,
            "cart_total": 100.0,
            "currency": "USD",
        }

        result = validate_llm_explanation(
            raw_response=valid_response,
            decision_context=decision_context,
            model_provenance={"model_name": "gpt-4o-mini"},
            strict_mode=True,
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID

    def test_validate_llm_explanation_invalid(self):
        """Test validate_llm_explanation function with invalid input."""
        invalid_response = """
        ```json
        {
            "explanation": "The transaction was processed at exactly 2:34:56 PM",
            "confidence": 0.9,
            "key_factors": ["specific_timing"]
        }
        ```
        """

        decision_context = {
            "decision": "APPROVE",
            "risk_score": 0.3,
            "cart_total": 100.0,
            "currency": "USD",
        }

        result = validate_llm_explanation(
            raw_response=invalid_response,
            decision_context=decision_context,
            model_provenance={"model_name": "gpt-4o-mini"},
            strict_mode=True,
        )

        assert not result.is_valid
        assert result.result_type == ValidationResult.HALLUCINATION

    def test_validate_llm_explanation_default_parameters(self):
        """Test validate_llm_explanation function with default parameters."""
        valid_response = """
        ```json
        {
            "explanation": "The transaction for $100.00 was approved",
            "confidence": 0.8,
            "key_factors": ["low_amount"]
        }
        ```
        """

        decision_context = {
            "decision": "APPROVE",
            "risk_score": 0.3,
            "cart_total": 100.0,
            "currency": "USD",
        }

        result = validate_llm_explanation(
            raw_response=valid_response,
            decision_context=decision_context,
            model_provenance={"model_name": "gpt-4o-mini"},
        )

        assert result.is_valid
        assert result.result_type == ValidationResult.VALID
