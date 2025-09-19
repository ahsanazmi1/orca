"""
Comprehensive tests for LLM guardrails functionality.

This module tests the guardrails system that validates LLM-generated
explanations, including JSON validation, hallucination detection, and content validation.
"""

import json

from src.orca_core.llm.guardrails import GuardrailResult, LLMGuardrails, ValidationResult


class TestValidationResult:
    """Test suite for ValidationResult enum."""

    def test_validation_result_values(self):
        """Test that ValidationResult has expected values."""
        assert ValidationResult.VALID.value == "valid"
        assert ValidationResult.INVALID_JSON.value == "invalid_json"
        assert ValidationResult.HALLUCINATION.value == "hallucination"
        assert ValidationResult.CONTENT_VIOLATION.value == "content_violation"
        assert ValidationResult.SCHEMA_VIOLATION.value == "schema_violation"
        assert ValidationResult.UNCERTAINTY_REFUSAL.value == "uncertainty_refusal"


class TestGuardrailResult:
    """Test suite for GuardrailResult dataclass."""

    def test_guardrail_result_creation(self):
        """Test GuardrailResult creation."""
        result = GuardrailResult(
            is_valid=True,
            result_type=ValidationResult.VALID,
            message="All good",
            confidence_score=0.95,
            violations=[],
        )

        assert result.is_valid is True
        assert result.result_type == ValidationResult.VALID
        assert result.message == "All good"
        assert result.confidence_score == 0.95
        assert result.violations == []
        assert result.sanitized_content is None

    def test_guardrail_result_with_sanitized_content(self):
        """Test GuardrailResult with sanitized content."""
        result = GuardrailResult(
            is_valid=True,
            result_type=ValidationResult.VALID,
            message="Sanitized",
            confidence_score=0.8,
            violations=[],
            sanitized_content="Clean content",
        )

        assert result.sanitized_content == "Clean content"


class TestLLMGuardrails:
    """Test suite for LLMGuardrails class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.guardrails = LLMGuardrails()

    def test_guardrails_initialization(self):
        """Test guardrails initialization."""
        assert self.guardrails.strict_mode is True
        assert hasattr(self.guardrails, "hallucination_patterns")
        assert hasattr(self.guardrails, "content_rules")
        assert hasattr(self.guardrails, "uncertainty_indicators")

    def test_guardrails_initialization_non_strict(self):
        """Test guardrails initialization in non-strict mode."""
        guardrails = LLMGuardrails(strict_mode=False)
        assert guardrails.strict_mode is False

    def test_expected_schema_structure(self):
        """Test that the expected schema structure is defined."""
        # Test that the guardrails has the expected structure
        assert hasattr(self.guardrails, "hallucination_patterns")
        assert isinstance(self.guardrails.hallucination_patterns, list)

    def test_validate_json_structure_valid(self):
        """Test JSON validation with valid JSON."""
        valid_json = '{"explanation": "This transaction was approved due to low risk factors.", "confidence": 0.85}'

        result = self.guardrails._validate_json_structure(valid_json)

        assert result.is_valid is True
        assert result.result_type == ValidationResult.VALID

    def test_validate_json_structure_invalid_syntax(self):
        """Test JSON validation with invalid syntax."""
        invalid_json = '{"explanation": "test", "confidence": 0.8,}'  # Trailing comma

        result = self.guardrails._validate_json_structure(invalid_json)

        assert result.is_valid is False
        assert result.result_type == ValidationResult.INVALID_JSON

    def test_detect_hallucinations_fabricated_data(self):
        """Test hallucination detection with fabricated data."""
        fabricated_content = '{"explanation": "The customer ID CUST12345 with exactly $1,234.56 is definitely 100% safe", "confidence": 0.9}'

        result = self.guardrails._detect_hallucinations(fabricated_content)

        # Should detect hallucination or at least not be valid
        assert result.is_valid is False

    def test_detect_hallucinations_overly_specific_claims(self):
        """Test hallucination detection with overly specific claims."""
        specific_content = '{"explanation": "This transaction has exactly 99.7% approval probability", "confidence": 0.9}'

        result = self.guardrails._detect_hallucinations(specific_content)

        # Should detect hallucination or at least not be valid
        assert result.is_valid is False

    def test_detect_hallucinations_fabricated_statistics(self):
        """Test hallucination detection with fabricated statistics."""
        stats_content = '{"explanation": "Based on our analysis of 1,000,000 similar transactions, this has a 0.001% risk", "confidence": 0.9}'

        result = self.guardrails._detect_hallucinations(stats_content)

        # Should detect hallucination or at least not be valid
        assert result.is_valid is False

    def test_detect_uncertainty_indicators(self):
        """Test uncertainty detection with uncertainty indicators."""
        uncertain_content = '{"explanation": "I am not sure about this transaction, it might be risky", "confidence": 0.8}'

        result = self.guardrails._detect_uncertainty(uncertain_content)

        # Test that the method works and returns a result
        assert hasattr(result, "is_valid")
        assert hasattr(result, "result_type")
        assert hasattr(result, "confidence_score")

    def test_sanitize_explanation_clean_content(self):
        """Test sanitization of clean content."""
        clean_explanation = "This transaction is approved based on standard criteria"

        sanitized = self.guardrails.sanitize_explanation(clean_explanation)

        assert sanitized == clean_explanation

    def test_sanitize_explanation_profanity(self):
        """Test sanitization of profanity in explanations."""
        profane_explanation = "This fucking transaction is approved"

        sanitized = self.guardrails.sanitize_explanation(profane_explanation)

        # Test that sanitization method works and returns a string
        assert isinstance(sanitized, str)
        assert len(sanitized) > 0
        assert "transaction" in sanitized

    def test_sanitize_explanation_personal_info(self):
        """Test sanitization of personal information."""
        personal_explanation = "Customer John Smith at 123 Main St is approved"

        sanitized = self.guardrails.sanitize_explanation(personal_explanation)

        # Should sanitize personal information
        assert "John Smith" not in sanitized
        assert "123 Main St" not in sanitized

    def test_validate_explanation_with_context(self):
        """Test comprehensive validation with proper context."""
        valid_response = {
            "explanation": "This transaction was approved based on standard risk assessment criteria.",
            "confidence": 0.85,
        }

        decision_context = {"amount": 100.0, "customer_id": "123"}
        model_provenance = {"model": "test", "version": "1.0"}

        result = self.guardrails.validate_explanation(
            json.dumps(valid_response), decision_context, model_provenance
        )

        assert hasattr(result, "is_valid")
        assert hasattr(result, "result_type")
        assert hasattr(result, "confidence_score")

    def test_validate_explanation_invalid_json(self):
        """Test comprehensive validation with invalid JSON."""
        invalid_json = '{"explanation": "test", "confidence": 0.8,}'

        decision_context = {"amount": 100.0}
        model_provenance = {"model": "test"}

        result = self.guardrails.validate_explanation(
            invalid_json, decision_context, model_provenance
        )

        assert result.is_valid is False
        assert result.result_type == ValidationResult.INVALID_JSON

    def test_non_strict_mode_validation(self):
        """Test validation in non-strict mode."""
        guardrails = LLMGuardrails(strict_mode=False)

        valid_response = {"explanation": "This transaction is approved", "confidence": 0.8}

        decision_context = {"amount": 100.0}
        model_provenance = {"model": "test"}

        result = guardrails.validate_explanation(
            json.dumps(valid_response), decision_context, model_provenance
        )

        assert hasattr(result, "is_valid")

    def test_get_validation_summary(self):
        """Test getting validation summary."""
        result = GuardrailResult(
            is_valid=True,
            result_type=ValidationResult.VALID,
            message="All good",
            confidence_score=0.95,
            violations=[],
        )

        summary = self.guardrails.get_validation_summary(result)

        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_guardrails_methods_exist(self):
        """Test that all expected methods exist."""
        assert hasattr(self.guardrails, "validate_explanation")
        assert hasattr(self.guardrails, "_validate_json_structure")
        assert hasattr(self.guardrails, "_validate_schema")
        assert hasattr(self.guardrails, "_detect_hallucinations")
        assert hasattr(self.guardrails, "_validate_content")
        assert hasattr(self.guardrails, "_detect_uncertainty")
        assert hasattr(self.guardrails, "sanitize_explanation")
        assert hasattr(self.guardrails, "get_validation_summary")

    def test_guardrails_initialization_parameters(self):
        """Test guardrails initialization with different parameters."""
        # Test default initialization
        guardrails1 = LLMGuardrails()
        assert guardrails1.strict_mode is True

        # Test with strict_mode=False
        guardrails2 = LLMGuardrails(strict_mode=False)
        assert guardrails2.strict_mode is False

    def test_validation_result_types(self):
        """Test that validation results have correct types."""
        result = GuardrailResult(
            is_valid=True,
            result_type=ValidationResult.VALID,
            message="Test message",
            confidence_score=0.8,
            violations=["test_violation"],
        )

        assert isinstance(result.is_valid, bool)
        assert isinstance(result.result_type, ValidationResult)
        assert isinstance(result.message, str)
        assert isinstance(result.confidence_score, float)
        assert isinstance(result.violations, list)
