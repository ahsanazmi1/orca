"""
Tests for Orca Explanation CloudEvents integration.
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.orca.core.ce import CloudEvent, CloudEventEmitter, emit_explanation_event


class TestExplanationCloudEvent:
    """Test CloudEvent structure and validation for explanations."""

    def test_explanation_cloud_event_structure(self):
        """Test that explanation CloudEvent has correct structure."""
        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "This transaction was approved based on low risk indicators including normal velocity patterns and trusted payment method.",
            "confidence": 0.85,
            "key_factors": ["low_velocity", "trusted_payment_method", "normal_amount"],
            "model_provenance": {
                "model_name": "gpt-4o-mini",
                "provider": "azure_openai",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 250,
                "tokens_used": 150,
            },
            "risk_score": 0.15,
            "reason_codes": ["VELOCITY_OK", "PAYMENT_METHOD_TRUSTED"],
        }

        ce = CloudEvent(
            id="test-explanation-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.explanation.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data=explanation_data,
        )

        # Validate required fields
        assert ce.specversion == "1.0"
        assert ce.type == "ocn.orca.explanation.v1"
        assert ce.subject == "txn_1234567890abcdef"
        assert ce.datacontenttype == "application/json"
        assert ce.data["trace_id"] == "txn_1234567890abcdef"
        assert ce.data["decision_result"] == "APPROVE"
        assert ce.data["confidence"] == 0.85

    def test_explanation_cloud_event_validation(self):
        """Test CloudEvent validation for explanations."""
        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "DECLINE",
            "explanation": "Transaction declined due to high risk indicators.",
            "confidence": 0.92,
            "key_factors": ["high_velocity", "suspicious_patterns"],
            "model_provenance": {
                "model_name": "gpt-4o-mini",
                "provider": "azure_openai",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 300,
                "tokens_used": 180,
            },
            "risk_score": 0.85,
            "reason_codes": ["VELOCITY_HIGH", "PATTERN_SUSPICIOUS"],
        }

        ce = CloudEvent(
            id="test-explanation-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.explanation.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data=explanation_data,
        )

        # Serialize and validate structure
        ce_json = ce.model_dump_json()
        ce_dict = json.loads(ce_json)

        # Check required fields are present
        required_fields = ["specversion", "id", "source", "type", "subject", "time", "data"]
        for field in required_fields:
            assert field in ce_dict

        # Check explanation data structure
        assert "trace_id" in ce_dict["data"]
        assert "decision_result" in ce_dict["data"]
        assert "explanation" in ce_dict["data"]
        assert "confidence" in ce_dict["data"]
        assert "model_provenance" in ce_dict["data"]

        # Validate confidence range
        assert 0.0 <= ce_dict["data"]["confidence"] <= 1.0


class TestExplanationCloudEventEmitter:
    """Test CloudEventEmitter functionality for explanations."""

    def test_emit_explanation_event_success(self):
        """Test successful explanation event emission."""
        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "Low risk transaction approved.",
            "confidence": 0.85,
            "model_provenance": {
                "model_name": "gpt-4o-mini",
                "provider": "azure_openai",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 250,
                "tokens_used": 150,
            },
        }

        emitter = CloudEventEmitter()
        ce = emitter.emit_explanation_event(
            explanation_data, "txn_1234567890abcdef", emit_to_subscriber=False
        )

        assert ce is not None
        assert ce.type == "ocn.orca.explanation.v1"
        assert ce.subject == "txn_1234567890abcdef"
        assert ce.data == explanation_data

    def test_emit_explanation_event_missing_required_fields(self):
        """Test explanation event emission with missing required fields."""
        # Missing required fields
        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "explanation": "Test explanation",
            # Missing: decision_result, confidence, model_provenance
        }

        emitter = CloudEventEmitter()
        ce = emitter.emit_explanation_event(
            explanation_data, "txn_1234567890abcdef", emit_to_subscriber=False
        )

        assert ce is None

    def test_emit_explanation_event_invalid_trace_id(self):
        """Test explanation event emission with invalid trace_id."""
        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "Test explanation",
            "confidence": 0.85,
            "model_provenance": {
                "model_name": "test",
                "provider": "test",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 100,
                "tokens_used": 50,
            },
        }

        emitter = CloudEventEmitter()

        # Test with invalid trace_id
        ce = emitter.emit_explanation_event(
            explanation_data, "invalid_trace_id", emit_to_subscriber=False
        )
        assert ce is None

    @patch("httpx.Client.post")
    def test_emit_explanation_to_subscriber_success(self, mock_post):
        """Test successful explanation emission to subscriber URL."""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "Low risk transaction approved.",
            "confidence": 0.85,
            "model_provenance": {
                "model_name": "gpt-4o-mini",
                "provider": "azure_openai",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 250,
                "tokens_used": 150,
            },
        }

        emitter = CloudEventEmitter(subscriber_url="http://localhost:8080/events")
        ce = emitter.emit_explanation_event(
            explanation_data, "txn_1234567890abcdef", emit_to_subscriber=True
        )

        assert ce is not None
        mock_post.assert_called_once()

        # Verify POST request details
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8080/events"
        assert "application/cloudevents+json" in call_args[1]["headers"]["Content-Type"]


class TestExplanationConvenienceFunctions:
    """Test convenience functions for explanation CloudEvent emission."""

    @patch("src.orca.core.ce.get_cloud_event_emitter")
    def test_emit_explanation_event_function(self, mock_get_emitter):
        """Test emit_explanation_event convenience function."""
        # Mock emitter
        mock_emitter = MagicMock()
        mock_ce = CloudEvent(
            id="test-explanation-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.explanation.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data={},
        )
        mock_emitter.emit_explanation_event.return_value = mock_ce
        mock_get_emitter.return_value = mock_emitter

        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "Test explanation",
            "confidence": 0.85,
            "model_provenance": {
                "model_name": "test",
                "provider": "test",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 100,
                "tokens_used": 50,
            },
        }

        result = emit_explanation_event(explanation_data, "txn_1234567890abcdef")

        assert result == mock_ce
        mock_emitter.emit_explanation_event.assert_called_once_with(
            explanation_data, "txn_1234567890abcdef"
        )


class TestExplanationSchemaConformance:
    """Test explanation CloudEvent conformance to ocn-common schemas."""

    def test_explanation_schema_conformance(self):
        """Test that explanation CloudEvents conform to schema."""
        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "This transaction was approved based on the following factors: 1) Normal transaction velocity patterns indicating legitimate customer behavior, 2) Use of a trusted payment method with good history, 3) Transaction amount within expected range for this customer segment.",
            "confidence": 0.87,
            "key_factors": [
                "normal_velocity_patterns",
                "trusted_payment_method",
                "amount_within_range",
            ],
            "model_provenance": {
                "model_name": "gpt-4o-mini",
                "provider": "azure_openai",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 320,
                "tokens_used": 185,
            },
            "risk_score": 0.15,
            "reason_codes": ["VELOCITY_OK", "PAYMENT_METHOD_TRUSTED", "AMOUNT_NORMAL"],
        }

        ce = CloudEvent(
            id="test-explanation-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.explanation.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            dataschema="https://schemas.ocn.ai/ap2/v1/explanation.schema.json",
            data=explanation_data,
        )

        # Validate against schema requirements
        assert ce.specversion == "1.0"
        assert ce.type == "ocn.orca.explanation.v1"
        assert ce.datacontenttype == "application/json"
        assert ce.dataschema == "https://schemas.ocn.ai/ap2/v1/explanation.schema.json"

        # Validate data structure
        data = ce.data
        assert "trace_id" in data
        assert "decision_result" in data
        assert "explanation" in data
        assert "confidence" in data
        assert "model_provenance" in data

        # Validate explanation content
        assert len(data["explanation"]) >= 10
        assert len(data["explanation"]) <= 2000
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["decision_result"] in ["APPROVE", "DECLINE", "REVIEW"]

        # Validate model provenance
        provenance = data["model_provenance"]
        assert "model_name" in provenance
        assert "provider" in provenance
        assert "version" in provenance
        assert "timestamp" in provenance
        assert "processing_time_ms" in provenance
        assert "tokens_used" in provenance

        # Validate key factors
        assert isinstance(data["key_factors"], list)
        assert len(data["key_factors"]) <= 10

    def test_explanation_confidence_boundaries(self):
        """Test explanation confidence score boundaries."""
        base_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "Test explanation",
            "model_provenance": {
                "model_name": "test",
                "provider": "test",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_time_ms": 100,
                "tokens_used": 50,
            },
        }

        # Test minimum confidence
        data_min = {**base_data, "confidence": 0.0}
        ce_min = CloudEvent(
            id="test-min",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.explanation.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data=data_min,
        )
        assert ce_min.data["confidence"] == 0.0

        # Test maximum confidence
        data_max = {**base_data, "confidence": 1.0}
        ce_max = CloudEvent(
            id="test-max",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.explanation.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data=data_max,
        )
        assert ce_max.data["confidence"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__])
