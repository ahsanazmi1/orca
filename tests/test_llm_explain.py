"""Tests for LLM explanation module."""

import json
import os
from unittest.mock import Mock, patch

import pytest

from src.orca_core.llm.explain import (
    AzureOpenAIClient,
    ExplanationRequest,
    ExplanationResponse,
    LLMExplainer,
    explain_decision_llm,
    get_llm_configuration_status,
    get_llm_explainer,
    is_llm_configured,
)


class TestExplanationRequest:
    """Test ExplanationRequest dataclass."""

    def test_explanation_request_creation(self):
        """Test creating an ExplanationRequest."""
        request = ExplanationRequest(
            decision="APPROVE",
            risk_score=0.15,
            reason_codes=["HIGH_TICKET"],
            transaction_data={"amount": 100.0, "currency": "USD"},
            model_type="xgb",
            model_version="1.0.0",
            rules_evaluated=["high_ticket_rule"],
            meta_data={"test": "data"},
        )

        assert request.decision == "APPROVE"
        assert request.risk_score == 0.15
        assert request.reason_codes == ["HIGH_TICKET"]
        assert request.transaction_data == {"amount": 100.0, "currency": "USD"}
        assert request.model_type == "xgb"
        assert request.model_version == "1.0.0"
        assert request.rules_evaluated == ["high_ticket_rule"]
        assert request.meta_data == {"test": "data"}


class TestExplanationResponse:
    """Test ExplanationResponse dataclass."""

    def test_explanation_response_creation(self):
        """Test creating an ExplanationResponse."""
        response = ExplanationResponse(
            explanation="Test explanation",
            confidence=0.85,
            model_provenance={"model": "test"},
            processing_time_ms=100,
            tokens_used=50,
        )

        assert response.explanation == "Test explanation"
        assert response.confidence == 0.85
        assert response.model_provenance == {"model": "test"}
        assert response.processing_time_ms == 100
        assert response.tokens_used == 50


class TestAzureOpenAIClient:
    """Test AzureOpenAIClient class."""

    def test_client_initialization_without_config(self):
        """Test client initialization without Azure OpenAI configuration."""
        with patch.dict(os.environ, {}, clear=True):
            client = AzureOpenAIClient()

            assert not client.is_configured
            assert client.client is None
            assert client.endpoint is None
            assert client.api_key is None
            assert client.deployment == "gpt-4o-mini"

    def test_client_initialization_with_config(self):
        """Test client initialization with Azure OpenAI configuration."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI") as mock_openai:
                client = AzureOpenAIClient()

                assert client.is_configured
                assert client.endpoint == "https://test.openai.azure.com/"
                assert client.api_key == "test-key"
                assert client.deployment == "gpt-4"
                mock_openai.assert_called_once()

    def test_generate_explanation_not_configured(self):
        """Test generate_explanation when client is not configured."""
        with patch.dict(os.environ, {}, clear=True):
            client = AzureOpenAIClient()
            request = ExplanationRequest(
                decision="APPROVE",
                risk_score=0.15,
                reason_codes=["HIGH_TICKET"],
                transaction_data={"amount": 100.0},
                model_type="xgb",
                model_version="1.0.0",
                rules_evaluated=[],
                meta_data={},
            )

            with pytest.raises(ValueError, match="Azure OpenAI not configured"):
                client.generate_explanation(request)

    @patch("src.orca_core.llm.explain.validate_llm_explanation")
    def test_generate_explanation_success(self, mock_validate):
        """Test successful explanation generation."""
        # Mock the validation to pass
        mock_validate.return_value = Mock(
            is_valid=True, result_type=Mock(value="valid"), confidence_score=0.9, violations=[]
        )

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI") as mock_openai:
                # Mock the API response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = json.dumps(
                    {
                        "explanation": "Test explanation",
                        "confidence": 0.85,
                        "key_factors": ["risk_score", "amount"],
                    }
                )
                mock_response.usage = Mock(total_tokens=50)
                mock_response.id = "test-id"

                mock_client = Mock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                client = AzureOpenAIClient()
                request = ExplanationRequest(
                    decision="APPROVE",
                    risk_score=0.15,
                    reason_codes=["HIGH_TICKET"],
                    transaction_data={
                        "amount": 100.0,
                        "currency": "USD",
                        "rail": "Card",
                        "channel": "online",
                    },
                    model_type="xgb",
                    model_version="1.0.0",
                    rules_evaluated=["high_ticket_rule"],
                    meta_data={},
                )

                response = client.generate_explanation(request)

                assert response.explanation == "Test explanation"
                assert response.confidence == 0.85
                assert response.tokens_used == 50
                assert "azure_openai" in response.model_provenance["provider"]
                assert response.model_provenance["request_id"] == "test-id"

    @patch("src.orca_core.llm.explain.validate_llm_explanation")
    def test_generate_explanation_guardrails_failure(self, mock_validate):
        """Test explanation generation with guardrails failure."""
        # Import the ValidationResult enum to use the actual value
        from src.orca_core.llm.guardrails import ValidationResult

        # Mock the validation to fail
        mock_validate.return_value = Mock(
            is_valid=False,
            result_type=ValidationResult.HALLUCINATION,
            confidence_score=0.3,
            violations=["test violation"],
            sanitized_content=None,
        )

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI") as mock_openai:
                # Mock the API response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = json.dumps(
                    {"explanation": "Test explanation", "confidence": 0.85}
                )
                mock_response.usage = Mock(total_tokens=50)
                mock_response.id = "test-id"

                mock_client = Mock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                client = AzureOpenAIClient()
                request = ExplanationRequest(
                    decision="APPROVE",
                    risk_score=0.15,
                    reason_codes=["HIGH_TICKET"],
                    transaction_data={
                        "amount": 100.0,
                        "currency": "USD",
                        "rail": "Card",
                        "channel": "online",
                    },
                    model_type="xgb",
                    model_version="1.0.0",
                    rules_evaluated=["high_ticket_rule"],
                    meta_data={},
                )

                response = client.generate_explanation(request)

                # Should fall back to mock explanation
                assert "Transaction approved" in response.explanation
                assert response.model_provenance["fallback_mode"] is True

    @patch("src.orca_core.llm.explain.validate_llm_explanation")
    def test_generate_explanation_json_error(self, mock_validate):
        """Test explanation generation with JSON parsing error."""
        # Mock the validation to pass
        mock_validate.return_value = Mock(
            is_valid=True, result_type=Mock(value="valid"), confidence_score=0.9, violations=[]
        )

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI") as mock_openai:
                # Mock the API response with invalid JSON
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = "invalid json"
                mock_response.usage = Mock(total_tokens=50)

                mock_client = Mock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                client = AzureOpenAIClient()
                request = ExplanationRequest(
                    decision="APPROVE",
                    risk_score=0.15,
                    reason_codes=["HIGH_TICKET"],
                    transaction_data={
                        "amount": 100.0,
                        "currency": "USD",
                        "rail": "Card",
                        "channel": "online",
                    },
                    model_type="xgb",
                    model_version="1.0.0",
                    rules_evaluated=["high_ticket_rule"],
                    meta_data={},
                )

                with pytest.raises(ValueError, match="Invalid JSON response"):
                    client.generate_explanation(request)

    def test_generate_mock_explanation_approve(self):
        """Test mock explanation generation for APPROVE decision."""
        with patch.dict(os.environ, {}, clear=True):
            client = AzureOpenAIClient()
            request = ExplanationRequest(
                decision="APPROVE",
                risk_score=0.15,
                reason_codes=["HIGH_TICKET"],
                transaction_data={"amount": 100.0, "channel": "online"},
                model_type="xgb",
                model_version="1.0.0",
                rules_evaluated=["high_ticket_rule"],
                meta_data={},
            )

            response = client._generate_mock_explanation(request)

            assert "Transaction approved" in response.explanation
            assert response.confidence == 0.85
            assert response.model_provenance["model_name"] == "mock-explainer"
            assert response.model_provenance["fallback_mode"] is True
            assert response.tokens_used == 0

    def test_generate_mock_explanation_decline(self):
        """Test mock explanation generation for DECLINE decision."""
        with patch.dict(os.environ, {}, clear=True):
            client = AzureOpenAIClient()
            request = ExplanationRequest(
                decision="DECLINE",
                risk_score=0.95,
                reason_codes=["HIGH_RISK", "VELOCITY_FLAG"],
                transaction_data={"amount": 1000.0, "channel": "online"},
                model_type="xgb",
                model_version="1.0.0",
                rules_evaluated=["high_risk_rule"],
                meta_data={},
            )

            response = client._generate_mock_explanation(request)

            assert "Transaction declined" in response.explanation
            assert response.confidence == 0.90
            assert "0.950" in response.explanation
            assert "HIGH_RISK" in response.explanation

    def test_generate_mock_explanation_review(self):
        """Test mock explanation generation for REVIEW decision."""
        with patch.dict(os.environ, {}, clear=True):
            client = AzureOpenAIClient()
            request = ExplanationRequest(
                decision="REVIEW",
                risk_score=0.65,
                reason_codes=["LOCATION_MISMATCH"],
                transaction_data={"amount": 500.0, "channel": "online"},
                model_type="xgb",
                model_version="1.0.0",
                rules_evaluated=["location_rule"],
                meta_data={},
            )

            response = client._generate_mock_explanation(request)

            assert "flagged for manual review" in response.explanation
            assert response.confidence == 0.75
            assert "0.650" in response.explanation
            assert "LOCATION_MISMATCH" in response.explanation

    def test_get_system_prompt(self):
        """Test system prompt generation."""
        with patch.dict(os.environ, {}, clear=True):
            client = AzureOpenAIClient()
            prompt = client._get_system_prompt()

            assert "expert financial risk analyst" in prompt
            assert "JSON" in prompt
            assert "schema" in prompt
            assert "guardrails" in prompt.lower()

    def test_build_explanation_prompt(self):
        """Test explanation prompt building."""
        with patch.dict(os.environ, {}, clear=True):
            client = AzureOpenAIClient()
            request = ExplanationRequest(
                decision="APPROVE",
                risk_score=0.15,
                reason_codes=["HIGH_TICKET"],
                transaction_data={
                    "amount": 100.0,
                    "currency": "USD",
                    "channel": "online",
                    "rail": "Card",
                },
                model_type="xgb",
                model_version="1.0.0",
                rules_evaluated=["high_ticket_rule"],
                meta_data={},
            )

            prompt = client._build_explanation_prompt(request)

            assert "APPROVE" in prompt
            assert "0.150" in prompt
            assert "HIGH_TICKET" in prompt
            assert "xgb" in prompt
            assert "1.0.0" in prompt
            assert "100.00" in prompt
            assert "online" in prompt
            assert "Card" in prompt
            assert "high_ticket_rule" in prompt


class TestLLMExplainer:
    """Test LLMExplainer class."""

    def test_explainer_initialization_not_configured(self):
        """Test explainer initialization when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            explainer = LLMExplainer()

            assert not explainer.is_available
            assert not explainer.is_configured()

    def test_explainer_initialization_configured(self):
        """Test explainer initialization when configured."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI"):
                explainer = LLMExplainer()

                assert explainer.is_available
                assert explainer.is_configured()

    def test_explain_decision_not_available(self):
        """Test explain_decision when LLM is not available."""
        with patch.dict(os.environ, {}, clear=True):
            explainer = LLMExplainer()

            response = explainer.explain_decision(
                decision="APPROVE",
                risk_score=0.15,
                reason_codes=["HIGH_TICKET"],
                transaction_data={"amount": 100.0},
                model_type="xgb",
                model_version="1.0.0",
            )

            assert response is not None
            assert "service unavailable" in response.explanation
            assert response.confidence == 0.0
            assert response.model_provenance["status"] == "503_service_unavailable"

    @patch("src.orca_core.llm.explain.validate_llm_explanation")
    def test_explain_decision_success(self, mock_validate):
        """Test successful decision explanation."""
        # Mock the validation to pass
        mock_validate.return_value = Mock(
            is_valid=True, result_type=Mock(value="valid"), confidence_score=0.9, violations=[]
        )

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI") as mock_openai:
                # Mock the API response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = json.dumps(
                    {"explanation": "Test explanation", "confidence": 0.85}
                )
                mock_response.usage = Mock(total_tokens=50)
                mock_response.id = "test-id"

                mock_client = Mock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                explainer = LLMExplainer()

                response = explainer.explain_decision(
                    decision="APPROVE",
                    risk_score=0.15,
                    reason_codes=["HIGH_TICKET"],
                    transaction_data={
                        "amount": 100.0,
                        "currency": "USD",
                        "rail": "Card",
                        "channel": "online",
                    },
                    model_type="xgb",
                    model_version="1.0.0",
                    rules_evaluated=["high_ticket_rule"],
                    meta_data={"test": "data"},
                )

                assert response is not None
                assert response.explanation == "Test explanation"
                assert response.confidence == 0.85

    def test_explain_decision_exception(self):
        """Test explain_decision with exception."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI") as mock_openai:
                # Mock client to raise exception
                mock_client = Mock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client

                explainer = LLMExplainer()

                response = explainer.explain_decision(
                    decision="APPROVE",
                    risk_score=0.15,
                    reason_codes=["HIGH_TICKET"],
                    transaction_data={
                        "amount": 100.0,
                        "currency": "USD",
                        "rail": "Card",
                        "channel": "online",
                    },
                    model_type="xgb",
                    model_version="1.0.0",
                )

                # Should fall back to mock explanation on exception
                assert response is not None
                assert "Transaction approved" in response.explanation
                assert response.model_provenance["fallback_mode"] is True

    def test_get_configuration_status_not_configured(self):
        """Test configuration status when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            explainer = LLMExplainer()
            status = explainer.get_configuration_status()

            assert status["status"] == "not_configured"
            assert "configuration missing" in status["message"]
            assert status["endpoint"] is None
            assert status["api_key"] is None

    def test_get_configuration_status_configured(self):
        """Test configuration status when configured."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI"):
                explainer = LLMExplainer()
                status = explainer.get_configuration_status()

                assert status["status"] == "configured"
                assert status["endpoint"] == "https://test.openai.azure.com/"
                assert status["deployment"] == "gpt-4"
                assert status["api_key"] == "***"


class TestGlobalFunctions:
    """Test global functions."""

    def test_get_llm_explainer_singleton(self):
        """Test that get_llm_explainer returns singleton instance."""
        explainer1 = get_llm_explainer()
        explainer2 = get_llm_explainer()
        assert explainer1 is explainer2

    def test_explain_decision_llm_function(self):
        """Test the explain_decision_llm function."""
        with patch.dict(os.environ, {}, clear=True):
            response = explain_decision_llm(
                decision="APPROVE",
                risk_score=0.15,
                reason_codes=["HIGH_TICKET"],
                transaction_data={"amount": 100.0},
                model_type="xgb",
                model_version="1.0.0",
            )

            assert response is not None
            assert "service unavailable" in response.explanation

    def test_is_llm_configured(self):
        """Test is_llm_configured function."""
        # Reset global singleton
        import src.orca_core.llm.explain

        src.orca_core.llm.explain._explainer = None

        with patch.dict(os.environ, {}, clear=True):
            assert not is_llm_configured()

        # Reset global singleton again
        src.orca_core.llm.explain._explainer = None

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI"):
                assert is_llm_configured()

    def test_get_llm_configuration_status(self):
        """Test get_llm_configuration_status function."""
        # Reset global singleton
        import src.orca_core.llm.explain

        src.orca_core.llm.explain._explainer = None

        with patch.dict(os.environ, {}, clear=True):
            status = get_llm_configuration_status()
            assert status["status"] == "not_configured"

        # Reset global singleton again
        src.orca_core.llm.explain._explainer = None

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
        ):
            with patch("src.orca_core.llm.explain.AzureOpenAI"):
                status = get_llm_configuration_status()
                assert status["status"] == "configured"
