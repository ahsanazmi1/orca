"""Tests for LLM explanation functionality."""

import os
from datetime import datetime

import pytest

from src.orca_core.llm.adapter import (
    _developer_template_explanation,
    _merchant_template_explanation,
    explain_decision,
    get_supported_providers,
    validate_provider_config,
)
from src.orca_core.models import DecisionMeta, DecisionResponse


class TestLLMAdapter:
    """Test the LLM adapter functionality."""

    def test_get_supported_providers(self):
        """Test that supported providers are returned correctly."""
        providers = get_supported_providers()
        assert "none" in providers
        assert "openai" in providers
        assert "azure" in providers

    def test_validate_provider_config_none(self):
        """Test validation for 'none' provider."""
        assert validate_provider_config("none") is True

    def test_validate_provider_config_openai_with_key(self):
        """Test validation for OpenAI provider with API key."""
        os.environ["OPENAI_API_KEY"] = "test-key"
        assert validate_provider_config("openai") is True
        del os.environ["OPENAI_API_KEY"]

    def test_validate_provider_config_openai_without_key(self):
        """Test validation for OpenAI provider without API key."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        assert validate_provider_config("openai") is False

    def test_validate_provider_config_azure_with_key(self):
        """Test validation for Azure provider with API key."""
        os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
        assert validate_provider_config("azure") is True
        del os.environ["AZURE_OPENAI_API_KEY"]

    def test_validate_provider_config_azure_without_key(self):
        """Test validation for Azure provider without API key."""
        if "AZURE_OPENAI_API_KEY" in os.environ:
            del os.environ["AZURE_OPENAI_API_KEY"]
        assert validate_provider_config("azure") is False

    def test_validate_provider_config_invalid(self):
        """Test validation for invalid provider."""
        assert validate_provider_config("invalid") is False


class TestFallbackExplanations:
    """Test fallback explanation functionality."""

    def create_test_response(self, decision="APPROVE", reasons=None, risk_score=0.0):
        """Helper to create test decision response."""
        if reasons is None:
            reasons = []

        meta = DecisionMeta(
            timestamp=datetime.now(),
            transaction_id="test-txn",
            rail="Card",
            channel="online",
            cart_total=100.0,
            risk_score=risk_score,
            model_version="stub-0.1",
            features_used=["cart_total"],
            rules_evaluated=[],
        )

        return DecisionResponse(
            decision=decision,
            reasons=reasons,
            actions=["Process payment"],
            meta={},
            meta_structured=meta,
        )

    def test_merchant_explanation_approve(self):
        """Test merchant explanation for approved transaction."""
        response = self.create_test_response("APPROVE")
        explanation = _merchant_template_explanation(response)

        assert "✅ Payment approved" in explanation
        assert "$100.00" in explanation
        assert "processed successfully" in explanation

    def test_merchant_explanation_decline_ml_risk(self):
        """Test merchant explanation for declined transaction with ML risk."""
        response = self.create_test_response("DECLINE", ["ml_score_high"], risk_score=0.9)
        explanation = _merchant_template_explanation(response)

        assert "❌ Payment declined" in explanation
        assert "high risk assessment" in explanation
        assert "contact support" in explanation

    def test_merchant_explanation_decline_other_reasons(self):
        """Test merchant explanation for declined transaction with other reasons."""
        response = self.create_test_response("DECLINE", ["HIGH_TICKET", "velocity_flag"])
        explanation = _merchant_template_explanation(response)

        assert "❌ Payment declined" in explanation
        assert "transaction amount exceeds limit" in explanation
        assert "unusual transaction pattern detected" in explanation

    def test_merchant_explanation_review(self):
        """Test merchant explanation for review transaction."""
        response = self.create_test_response("REVIEW", ["HIGH_TICKET", "online_verification"])
        explanation = _merchant_template_explanation(response)

        assert "⏳ Payment under review" in explanation
        assert "transaction amount exceeds limit" in explanation
        assert "additional verification required" in explanation
        assert "email with next steps" in explanation

    def test_developer_explanation_approve(self):
        """Test developer explanation for approved transaction."""
        response = self.create_test_response("APPROVE")
        explanation = _developer_template_explanation(response)

        assert "Decision: APPROVE" in explanation
        # Risk score is only shown when > 0
        assert "Model: stub-0.1" not in explanation  # Model only shown when risk score > 0

    def test_developer_explanation_decline(self):
        """Test developer explanation for declined transaction."""
        response = self.create_test_response(
            "DECLINE", ["HIGH_RISK", "ml_score_high"], risk_score=0.9
        )
        response.meta_structured.rules_evaluated = ["HIGH_RISK"]
        response.actions = ["BLOCK"]

        explanation = _developer_template_explanation(response)

        assert "Decision: DECLINE" in explanation
        assert "Risk Score: 0.900" in explanation
        assert "Model: stub-0.1" in explanation
        assert "Rules Evaluated: HIGH_RISK" in explanation
        assert "Reasons: HIGH_RISK, ml_score_high" in explanation
        assert "Actions: BLOCK" in explanation
        assert "ML Features: cart_total" in explanation

    def test_format_reasons_for_merchant(self):
        """Test formatting of technical reasons for merchant display."""
        from src.orca_core.llm.adapter import _format_reasons_for_merchant

        reasons = [
            "HIGH_TICKET: Cart total $1000.00 exceeds $500.00 threshold",
            "velocity_flag: 6 transactions in 24h exceeds 5 threshold",
            "location_mismatch: IP location differs from billing address",
        ]

        formatted = _format_reasons_for_merchant(reasons)

        assert "transaction amount exceeds limit" in formatted
        assert "unusual transaction pattern detected" in formatted
        assert "location verification required" in formatted


class TestLLMIntegration:
    """Test LLM integration with the decision engine."""

    def test_explain_decision_fallback(self):
        """Test explain_decision with fallback (no LLM provider)."""
        # Ensure no LLM provider is set
        if "ORCA_LLM_PROVIDER" in os.environ:
            del os.environ["ORCA_LLM_PROVIDER"]

        meta = DecisionMeta(
            timestamp=datetime.now(),
            transaction_id="test-txn",
            rail="Card",
            channel="online",
            cart_total=100.0,
            risk_score=0.0,
            model_version="stub-0.1",
            features_used=["cart_total"],
            rules_evaluated=[],
        )

        response = DecisionResponse(
            decision="APPROVE",
            reasons=["Cart total $100.00 within approved threshold"],
            actions=["Process payment"],
            meta={},
            meta_structured=meta,
        )

        # Test merchant style
        merchant_explanation = explain_decision(response, "merchant")
        assert "✅ Payment approved" in merchant_explanation

        # Test developer style
        developer_explanation = explain_decision(response, "developer")
        assert "Decision: APPROVE" in developer_explanation

    def test_explain_decision_invalid_style(self):
        """Test explain_decision with invalid style raises error."""
        meta = DecisionMeta(
            timestamp=datetime.now(),
            transaction_id="test-txn",
            rail="Card",
            channel="online",
            cart_total=100.0,
            risk_score=0.0,
            model_version="stub-0.1",
            features_used=[],
            rules_evaluated=[],
        )

        response = DecisionResponse(
            decision="APPROVE", reasons=[], actions=[], meta={}, meta_structured=meta
        )

        # This should not raise an error, but return a fallback explanation
        explanation = explain_decision(response, "invalid_style")
        assert explanation is not None

    def test_explain_decision_openai_no_key(self):
        """Test explain_decision with OpenAI provider but no API key."""
        os.environ["ORCA_LLM_PROVIDER"] = "openai"
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        meta = DecisionMeta(
            timestamp=datetime.now(),
            transaction_id="test-txn",
            rail="Card",
            channel="online",
            cart_total=100.0,
            risk_score=0.0,
            model_version="stub-0.1",
            features_used=[],
            rules_evaluated=[],
        )

        response = DecisionResponse(
            decision="APPROVE", reasons=[], actions=[], meta={}, meta_structured=meta
        )

        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
            explain_decision(response, "merchant")

        del os.environ["ORCA_LLM_PROVIDER"]

    def test_explain_decision_azure_no_key(self):
        """Test explain_decision with Azure provider but no API key."""
        os.environ["ORCA_LLM_PROVIDER"] = "azure"
        if "AZURE_OPENAI_API_KEY" in os.environ:
            del os.environ["AZURE_OPENAI_API_KEY"]

        meta = DecisionMeta(
            timestamp=datetime.now(),
            transaction_id="test-txn",
            rail="Card",
            channel="online",
            cart_total=100.0,
            risk_score=0.0,
            model_version="stub-0.1",
            features_used=[],
            rules_evaluated=[],
        )

        response = DecisionResponse(
            decision="APPROVE", reasons=[], actions=[], meta={}, meta_structured=meta
        )

        with pytest.raises(
            ValueError, match="AZURE_OPENAI_API_KEY environment variable is required"
        ):
            explain_decision(response, "merchant")

        del os.environ["ORCA_LLM_PROVIDER"]
