"""
LLM Guardrails for Orca Core

This module provides comprehensive validation and safety mechanisms for LLM-generated
explanations, including JSON validation, hallucination detection, and content validation.
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Validation result types."""

    VALID = "valid"
    INVALID_JSON = "invalid_json"
    HALLUCINATION = "hallucination"
    CONTENT_VIOLATION = "content_violation"
    SCHEMA_VIOLATION = "schema_violation"
    UNCERTAINTY_REFUSAL = "uncertainty_refusal"


@dataclass
class GuardrailResult:
    """Result of guardrail validation."""

    is_valid: bool
    result_type: ValidationResult
    message: str
    confidence_score: float
    violations: list[str]
    sanitized_content: str | None = None


class LLMGuardrails:
    """Comprehensive guardrails system for LLM explanations."""

    def __init__(self, strict_mode: bool = True):
        """
        Initialize guardrails system.

        Args:
            strict_mode: If True, apply strict validation rules
        """
        self.strict_mode = strict_mode
        self.hallucination_patterns = self._load_hallucination_patterns()
        self.content_rules = self._load_content_rules()
        self.uncertainty_indicators = self._load_uncertainty_indicators()

        # JSON schema for expected LLM response
        self.expected_schema = {
            "type": "object",
            "required": ["explanation", "confidence"],
            "properties": {
                "explanation": {"type": "string", "minLength": 10, "maxLength": 2000},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reasoning": {"type": "string", "maxLength": 1000},
                "risk_factors": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
            },
        }

    def _load_hallucination_patterns(self) -> list[str]:
        """Load patterns that indicate potential hallucinations."""
        return [
            # Fabricated data patterns
            r"\b(?:exactly|precisely|specifically)\s+\d+(?:\.\d+)?\s*(?:dollars?|USD|EUR|GBP)\b",
            r"\b(?:customer|user|account)\s+(?:ID|number|code)\s*[:=]\s*\w+\b",
            r"\b(?:transaction|payment)\s+(?:ID|number|reference)\s*[:=]\s*\w+\b",
            r"\b(?:IP\s+address|location|coordinates)\s*[:=]\s*[\d\.]+(?:\s*,\s*[\d\.]+)?\b",
            r"\b(?:timestamp|date|time)\s*[:=]\s*\d{4}-\d{2}-\d{2}\b",
            # Overly specific claims
            r"\b(?:definitely|certainly|absolutely|guaranteed)\b",
            r"\b(?:100%|completely|totally)\s+(?:safe|secure|legitimate)\b",
            r"\b(?:never|always)\s+(?:happens|occurs|fails)\b",
            # Fabricated statistics
            r"\b(?:statistics|studies|research)\s+(?:show|indicate|prove)\b",
            r"\b\d+(?:\.\d+)?%\s+(?:of|chance|probability)\b",
            r"\b(?:based on|according to)\s+(?:our|internal|proprietary)\s+(?:data|analysis)\b",
            # Unverifiable claims
            r"\b(?:similar|previous|past)\s+(?:transactions|customers|cases)\b",
            r"\b(?:typically|usually|normally)\s+(?:results in|leads to|causes)\b",
            r"\b(?:industry|market|sector)\s+(?:standards|practices|norms)\b",
        ]

    def _load_content_rules(self) -> list[str]:
        """Load content validation rules."""
        return [
            # Must reference actual decision data
            r"\b(?:cart_total|amount|transaction)\s+(?:is|was|of)\s+\$?\d+(?:\.\d+)?",
            r"\b(?:currency|rail|channel)\s+(?:is|was|set to)\s+\w+",
            r"\b(?:risk\s+score|confidence)\s+(?:is|was|of)\s+\d+(?:\.\d+)?",
            # Must not contain PII
            r"\b(?:name|email|phone|address|ssn|credit\s+card)\s*[:=]",
            r"\b(?:personal|private|sensitive)\s+(?:information|data)\b",
            # Must not make legal/financial advice
            r"\b(?:legal|financial|investment|tax)\s+(?:advice|recommendation|guidance)\b",
            r"\b(?:should|must|need to)\s+(?:contact|consult|seek)\s+(?:lawyer|attorney|advisor)\b",
            # Must not make guarantees
            r"\b(?:guarantee|warranty|promise|assure)\b",
            r"\b(?:no\s+risk|risk-free|safe\s+investment)\b",
        ]

    def _load_uncertainty_indicators(self) -> list[str]:
        """Load patterns that indicate uncertainty or refusal."""
        return [
            r"\b(?:i\s+don't\s+know|i'm\s+not\s+sure|unclear|uncertain)\b",
            r"\b(?:cannot|cannot|cannot)\s+(?:determine|assess|evaluate)\b",
            r"\b(?:insufficient|limited|incomplete)\s+(?:information|data|context)\b",
            r"\b(?:refuse|decline|cannot\s+provide)\s+(?:explanation|analysis|assessment)\b",
            r"\b(?:not\s+enough|lack\s+of|missing)\s+(?:information|data|details)\b",
        ]

    def _extract_json_from_markdown(self, text: str) -> dict[str, Any] | None:
        """
        Extract JSON from markdown code blocks or plain text.

        Args:
            text: Text that may contain JSON in markdown code blocks

        Returns:
            Parsed JSON dict or None if extraction fails
        """
        try:
            # First try to parse as plain JSON
            result = json.loads(text.strip())
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code blocks
        markdown_patterns = [
            r"```json\s*\n\s*(.*?)\s*\n\s*```",  # ```json ... ``` with spaces around content
            r"```\s*\n\s*(.*?)\s*\n\s*```",  # ``` ... ``` with spaces around content
            r"```json\s*\n(.*?)\n```",  # ```json ... ```
            r"```\s*\n(.*?)\n```",  # ``` ... ```
            r"`(.*?)`",  # `...`
        ]

        for pattern in markdown_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    # Clean up the match by removing leading/trailing whitespace and common indentation
                    cleaned_match = match.strip()
                    # Remove common leading indentation (4 spaces or tabs)
                    lines = cleaned_match.split("\n")
                    if lines:
                        # Find minimum indentation (excluding empty lines)
                        non_empty_lines = [line for line in lines if line.strip()]
                        if non_empty_lines:
                            min_indent = min(
                                len(line) - len(line.lstrip()) for line in non_empty_lines
                            )
                            if min_indent > 0:
                                lines = [
                                    line[min_indent:] if len(line) > min_indent else line
                                    for line in lines
                                ]
                                cleaned_match = "\n".join(lines)

                    result = json.loads(cleaned_match)
                    return result if isinstance(result, dict) else None
                except json.JSONDecodeError:
                    continue

        return None

    def validate_explanation(
        self, raw_response: str, decision_context: dict[str, Any], model_provenance: dict[str, Any]
    ) -> GuardrailResult:
        """
        Comprehensive validation of LLM explanation.

        Args:
            raw_response: Raw LLM response text
            decision_context: Context about the decision being explained
            model_provenance: Information about the model that generated the response

        Returns:
            GuardrailResult with validation outcome
        """
        confidence_score = 1.0

        # Step 1: JSON Validation
        json_result = self._validate_json_structure(raw_response)
        if not json_result.is_valid:
            return json_result

        # Step 2: Schema Validation
        if json_result.sanitized_content is None:
            return GuardrailResult(
                is_valid=False,
                result_type=ValidationResult.INVALID_JSON,
                message="JSON parsing failed",
                confidence_score=0.0,
                violations=["JSON parsing failed"],
                sanitized_content=None,
            )

        schema_result = self._validate_schema(json_result.sanitized_content)
        if not schema_result.is_valid:
            return schema_result

        # Step 3: Hallucination Detection
        hallucination_result = self._detect_hallucinations(json_result.sanitized_content)
        if not hallucination_result.is_valid:
            return hallucination_result

        # Step 4: Content Validation
        content_result = self._validate_content(json_result.sanitized_content, decision_context)
        if not content_result.is_valid:
            return content_result

        # Step 5: Uncertainty Detection
        uncertainty_result = self._detect_uncertainty(json_result.sanitized_content)
        if not uncertainty_result.is_valid and self.strict_mode:
            return uncertainty_result

        # Calculate final confidence score
        confidence_score = min(
            json_result.confidence_score,
            schema_result.confidence_score,
            hallucination_result.confidence_score,
            content_result.confidence_score,
            uncertainty_result.confidence_score,
        )

        return GuardrailResult(
            is_valid=True,
            result_type=ValidationResult.VALID,
            message="Explanation passed all guardrail validations",
            confidence_score=confidence_score,
            violations=[],
            sanitized_content=json_result.sanitized_content,
        )

    def _validate_json_structure(self, raw_response: str) -> GuardrailResult:
        """Validate that response is valid JSON."""
        if not raw_response:
            return GuardrailResult(
                is_valid=False,
                result_type=ValidationResult.INVALID_JSON,
                message="Response cannot be None",
                confidence_score=0.0,
                violations=["None response"],
            )

        try:
            # Try to parse as JSON
            parsed_json = json.loads(raw_response)

            # Check if it's a dictionary (not a list or primitive)
            if not isinstance(parsed_json, dict):
                return GuardrailResult(
                    is_valid=False,
                    result_type=ValidationResult.INVALID_JSON,
                    message="Response must be a JSON object, not array or primitive",
                    confidence_score=0.0,
                    violations=["Invalid JSON structure"],
                )

            return GuardrailResult(
                is_valid=True,
                result_type=ValidationResult.VALID,
                message="Valid JSON structure",
                confidence_score=1.0,
                violations=[],
                sanitized_content=raw_response,
            )

        except json.JSONDecodeError as e:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group(1))
                    return GuardrailResult(
                        is_valid=True,
                        result_type=ValidationResult.VALID,
                        message="Valid JSON extracted from markdown",
                        confidence_score=0.9,
                        violations=[],
                        sanitized_content=json_match.group(1),
                    )
                except json.JSONDecodeError:
                    pass

            return GuardrailResult(
                is_valid=False,
                result_type=ValidationResult.INVALID_JSON,
                message=f"Invalid JSON format: {str(e)}",
                confidence_score=0.0,
                violations=[f"JSON decode error: {str(e)}"],
            )

    def _validate_schema(self, json_content: str) -> GuardrailResult:
        """Validate JSON against expected schema."""
        try:
            parsed_json = json.loads(json_content)
            violations = []

            # Check required fields
            required_fields = self.expected_schema["required"]
            for field in required_fields:
                if field not in parsed_json:
                    violations.append(f"Missing required field: {field}")

            # Check field types and constraints
            if "explanation" in parsed_json:
                explanation = parsed_json["explanation"]
                if not isinstance(explanation, str):
                    violations.append("Explanation must be a string")
                elif len(explanation) < 10:
                    violations.append("Explanation too short (minimum 10 characters)")
                elif len(explanation) > 2000:
                    violations.append("Explanation too long (maximum 2000 characters)")

            if "confidence" in parsed_json:
                confidence = parsed_json["confidence"]
                if not isinstance(confidence, int | float):
                    violations.append("Confidence must be a number")
                elif confidence < 0.0 or confidence > 1.0:
                    violations.append("Confidence must be between 0.0 and 1.0")

            if violations:
                return GuardrailResult(
                    is_valid=False,
                    result_type=ValidationResult.SCHEMA_VIOLATION,
                    message=f"Schema validation failed: {', '.join(violations)}",
                    confidence_score=0.0,
                    violations=violations,
                )

            return GuardrailResult(
                is_valid=True,
                result_type=ValidationResult.VALID,
                message="Schema validation passed",
                confidence_score=1.0,
                violations=[],
            )

        except json.JSONDecodeError:
            return GuardrailResult(
                is_valid=False,
                result_type=ValidationResult.SCHEMA_VIOLATION,
                message="Cannot parse JSON for schema validation",
                confidence_score=0.0,
                violations=["JSON parse error"],
            )

    def _detect_hallucinations(self, json_content: str) -> GuardrailResult:
        """Detect potential hallucinations in the explanation."""
        try:
            parsed_json = json.loads(json_content)
            explanation = parsed_json.get("explanation", "")
            violations = []

            # Check for hallucination patterns
            for pattern in self.hallucination_patterns:
                matches = re.findall(pattern, explanation, re.IGNORECASE)
                if matches:
                    violations.append(f"Potential hallucination: {pattern}")

            # Check for overly specific claims
            if re.search(r"\b(?:exactly|precisely|specifically)\s+\d+", explanation, re.IGNORECASE):
                violations.append("Overly specific numerical claims")

            # Check for fabricated data
            if re.search(
                r"\b(?:customer|user|account)\s+(?:ID|number)", explanation, re.IGNORECASE
            ):
                violations.append("Potential fabricated customer data")

            if violations:
                return GuardrailResult(
                    is_valid=False,
                    result_type=ValidationResult.HALLUCINATION,
                    message=f"Potential hallucinations detected: {', '.join(violations)}",
                    confidence_score=0.0,
                    violations=violations,
                )

            return GuardrailResult(
                is_valid=True,
                result_type=ValidationResult.VALID,
                message="No hallucinations detected",
                confidence_score=1.0,
                violations=[],
            )

        except json.JSONDecodeError:
            return GuardrailResult(
                is_valid=False,
                result_type=ValidationResult.HALLUCINATION,
                message="Cannot parse JSON for hallucination detection",
                confidence_score=0.0,
                violations=["JSON parse error"],
            )

    def _validate_content(
        self, json_content: str, decision_context: dict[str, Any]
    ) -> GuardrailResult:
        """Validate content against decision context and rules."""
        try:
            parsed_json = json.loads(json_content)
            explanation = parsed_json.get("explanation", "")
            violations = []

            # Check for PII
            if re.search(
                r"\b(?:name|email|phone|address|ssn|credit\s+card)\s*[:=]",
                explanation,
                re.IGNORECASE,
            ):
                violations.append("Potential PII disclosure")

            # Check for legal/financial advice
            if re.search(
                r"\b(?:legal|financial|investment|tax)\s+(?:advice|recommendation)",
                explanation,
                re.IGNORECASE,
            ):
                violations.append("Potential legal/financial advice")

            # Check for guarantees
            if re.search(r"\b(?:guarantee|warranty|promise|assure)\b", explanation, re.IGNORECASE):
                violations.append("Potential guarantee or warranty claim")

            # Check if explanation references actual decision data
            context_references = 0

            # Check for amount/cart_total reference
            if "cart_total" in decision_context:
                amount = decision_context["cart_total"]
                if (
                    re.search(rf"\$?{amount}", explanation, re.IGNORECASE)
                    or re.search(
                        rf"\b(?:cart_total|amount|transaction)\s+(?:is|was|of)\s+\$?{amount}",
                        explanation,
                        re.IGNORECASE,
                    )
                    or re.search(
                        rf"\b(?:cart_total|amount|transaction)\s+(?:of|at)\s+\$?{amount}",
                        explanation,
                        re.IGNORECASE,
                    )
                ):
                    context_references += 1

            # Check for currency reference
            if "currency" in decision_context:
                currency = decision_context["currency"]
                if re.search(rf"\b{currency}\b", explanation, re.IGNORECASE) or re.search(
                    rf"\b(?:currency|rail|channel)\s+(?:is|was|set to)\s+{currency}",
                    explanation,
                    re.IGNORECASE,
                ):
                    context_references += 1

            # Check for decision reference
            if "decision" in decision_context:
                decision = decision_context["decision"]
                if re.search(rf"\b{decision}\b", explanation, re.IGNORECASE):
                    context_references += 1

            # Check for risk score reference
            if "risk_score" in decision_context:
                risk_score = decision_context["risk_score"]
                if re.search(
                    rf"\b(?:risk\s+score|risk)\s+(?:is|was|of)\s+{risk_score}",
                    explanation,
                    re.IGNORECASE,
                ):
                    context_references += 1

            # Only require at least one context reference
            if context_references == 0:
                violations.append("Explanation does not reference actual decision data")

            if violations:
                return GuardrailResult(
                    is_valid=False,
                    result_type=ValidationResult.CONTENT_VIOLATION,
                    message=f"Content validation failed: {', '.join(violations)}",
                    confidence_score=0.0,
                    violations=violations,
                )

            return GuardrailResult(
                is_valid=True,
                result_type=ValidationResult.VALID,
                message="Content validation passed",
                confidence_score=1.0,
                violations=[],
            )

        except json.JSONDecodeError:
            return GuardrailResult(
                is_valid=False,
                result_type=ValidationResult.CONTENT_VIOLATION,
                message="Cannot parse JSON for content validation",
                confidence_score=0.0,
                violations=["JSON parse error"],
            )

    def _detect_uncertainty(self, json_content: str) -> GuardrailResult:
        """Detect uncertainty or refusal indicators."""
        try:
            parsed_json = json.loads(json_content)
            explanation = parsed_json.get("explanation", "")
            violations = []

            # Check for uncertainty indicators
            for pattern in self.uncertainty_indicators:
                if re.search(pattern, explanation, re.IGNORECASE):
                    violations.append(f"Uncertainty indicator: {pattern}")

            # Check confidence score
            confidence = parsed_json.get("confidence", 1.0)
            if confidence < 0.5:
                violations.append(f"Low confidence score: {confidence}")

            if violations:
                return GuardrailResult(
                    is_valid=False,
                    result_type=ValidationResult.UNCERTAINTY_REFUSAL,
                    message=f"Uncertainty or refusal detected: {', '.join(violations)}",
                    confidence_score=0.0,
                    violations=violations,
                )

            return GuardrailResult(
                is_valid=True,
                result_type=ValidationResult.VALID,
                message="No uncertainty detected",
                confidence_score=1.0,
                violations=[],
            )

        except json.JSONDecodeError:
            return GuardrailResult(
                is_valid=False,
                result_type=ValidationResult.UNCERTAINTY_REFUSAL,
                message="Cannot parse JSON for uncertainty detection",
                confidence_score=0.0,
                violations=["JSON parse error"],
            )

    def sanitize_explanation(self, explanation: str) -> str:
        """Sanitize explanation by removing potential issues."""
        # Remove potential PII - names
        explanation = re.sub(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", "[REDACTED NAME]", explanation)

        # Remove SSN patterns
        explanation = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED SSN]", explanation)

        # Remove other PII patterns
        explanation = re.sub(
            r"\b(?:name|email|phone|address|ssn|credit\s+card)\s*[:=]\s*\w+",
            "[REDACTED]",
            explanation,
            flags=re.IGNORECASE,
        )

        # Remove overly specific claims
        explanation = re.sub(
            r"\b(?:exactly|precisely|specifically)\s+\d+(?:\.\d+)?\s*(?:dollars?|USD|EUR|GBP)\b",
            "the transaction amount",
            explanation,
            flags=re.IGNORECASE,
        )

        # Remove standalone "exactly" references
        explanation = re.sub(
            r"\bexactly\s+\$?\d+(?:\.\d+)?\b",
            "approximately the amount",
            explanation,
            flags=re.IGNORECASE,
        )

        # Remove guarantees
        explanation = re.sub(
            r"\b(?:guarantee|guaranteed|warranty|promise|assure|assured)\b",
            "indicate",
            explanation,
            flags=re.IGNORECASE,
        )

        # Remove legal advice
        explanation = re.sub(
            r"\b(?:legal|financial|investment|tax)\s+(?:advice|recommendation|guidance)\b",
            "general information",
            explanation,
            flags=re.IGNORECASE,
        )

        # Remove advice recommendations
        explanation = re.sub(
            r"\b(?:should|must|need to)\s+(?:contact|consult|seek)\s+(?:lawyer|attorney|advisor)\b",
            "may want to consider professional guidance",
            explanation,
            flags=re.IGNORECASE,
        )

        # Remove standalone "advice" references
        explanation = re.sub(
            r"\bfor advice\b", "for general information", explanation, flags=re.IGNORECASE
        )

        return explanation.strip()

    def get_validation_summary(self, result: GuardrailResult) -> str:
        """Get a human-readable summary of validation results."""
        if result.is_valid:
            return f"✅ Validation passed (confidence: {result.confidence_score:.2f})"
        else:
            return f"❌ Validation failed: {result.message} (violations: {len(result.violations)})"


# Global guardrails instance
_guardrails_instance: LLMGuardrails | None = None


def get_guardrails(strict_mode: bool = True) -> LLMGuardrails:
    """Get or create global guardrails instance."""
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = LLMGuardrails(strict_mode=strict_mode)
    return _guardrails_instance


def validate_llm_explanation(
    raw_response: str,
    decision_context: dict[str, Any],
    model_provenance: dict[str, Any],
    strict_mode: bool = True,
) -> GuardrailResult:
    """
    Convenience function to validate LLM explanation.

    Args:
        raw_response: Raw LLM response text
        decision_context: Context about the decision being explained
        model_provenance: Information about the model that generated the response
        strict_mode: If True, apply strict validation rules

    Returns:
        GuardrailResult with validation outcome
    """
    guardrails = get_guardrails(strict_mode=strict_mode)
    return guardrails.validate_explanation(raw_response, decision_context, model_provenance)
