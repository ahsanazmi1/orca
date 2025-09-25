"""
Tests for Orca Decision CloudEvents integration.
"""

import json
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.orca.core.ce import CloudEvent, CloudEventEmitter, emit_decision_event


class TestDecisionCloudEvent:
    """Test CloudEvent structure and validation."""

    def test_decision_cloud_event_structure(self):
        """Test that decision CloudEvent has correct structure."""
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": {"id": "customer_123", "type": "individual"},
                "channel": "web",
                "geo": {"country": "US"},
                "metadata": {},
            },
            "cart": {"amount": "100.00", "currency": "USD", "items": [], "geo": {}},
            "payment": {
                "method": "card",
                "modality": "immediate",
                "auth_requirements": [],
                "metadata": {},
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.15,
                "reasons": [],
                "actions": [],
                "meta": {},
            },
            "signing": {"vc_proof": None, "receipt_hash": "sha256:abc123"},
        }

        ce = CloudEvent(
            id="test-event-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.decision.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data=decision_data,
        )

        # Validate required fields
        assert ce.specversion == "1.0"
        assert ce.type == "ocn.orca.decision.v1"
        assert ce.subject == "txn_1234567890abcdef"
        assert ce.datacontenttype == "application/json"
        assert ce.data["ap2_version"] == "0.1.0"
        assert ce.data["decision"]["result"] == "APPROVE"

    def test_decision_cloud_event_validation(self):
        """Test CloudEvent validation against schema."""
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": {"id": "customer_123", "type": "individual"},
                "channel": "web",
                "geo": {},
                "metadata": {},
            },
            "cart": {"amount": "100.00", "currency": "USD", "items": [], "geo": {}},
            "payment": {
                "method": "card",
                "modality": "immediate",
                "auth_requirements": [],
                "metadata": {},
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.15,
                "reasons": [],
                "actions": [],
                "meta": {},
            },
            "signing": {"vc_proof": None, "receipt_hash": "sha256:abc123"},
        }

        ce = CloudEvent(
            id="test-event-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.decision.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data=decision_data,
        )

        # Serialize and validate structure
        ce_json = ce.model_dump_json()
        ce_dict = json.loads(ce_json)

        # Check required fields are present
        required_fields = ["specversion", "id", "source", "type", "subject", "time", "data"]
        for field in required_fields:
            assert field in ce_dict

        # Check data structure
        assert "ap2_version" in ce_dict["data"]
        assert "decision" in ce_dict["data"]
        assert ce_dict["data"]["decision"]["result"] == "APPROVE"


class TestCloudEventEmitter:
    """Test CloudEventEmitter functionality."""

    def test_emitter_initialization(self):
        """Test emitter initialization with and without subscriber URL."""
        # Test without subscriber URL
        emitter = CloudEventEmitter()
        assert emitter.subscriber_url is None or emitter.subscriber_url == os.getenv(
            "ORCA_CE_SUBSCRIBER_URL"
        )

        # Test with subscriber URL
        test_url = "http://localhost:8080/events"
        emitter = CloudEventEmitter(subscriber_url=test_url)
        assert emitter.subscriber_url == test_url

    def test_emit_decision_event_success(self):
        """Test successful decision event emission."""
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {"actor": {"id": "test"}, "channel": "web", "geo": {}, "metadata": {}},
            "cart": {"amount": "100.00", "currency": "USD", "items": [], "geo": {}},
            "payment": {
                "method": "card",
                "modality": "immediate",
                "auth_requirements": [],
                "metadata": {},
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.15,
                "reasons": [],
                "actions": [],
                "meta": {},
            },
            "signing": {"vc_proof": None, "receipt_hash": "sha256:abc123"},
        }

        emitter = CloudEventEmitter()
        ce = emitter.emit_decision_event(
            decision_data, "txn_1234567890abcdef", emit_to_subscriber=False
        )

        assert ce is not None
        assert ce.type == "ocn.orca.decision.v1"
        assert ce.subject == "txn_1234567890abcdef"
        assert ce.data == decision_data

    def test_emit_decision_event_invalid_trace_id(self):
        """Test decision event emission with invalid trace_id."""
        decision_data = {"ap2_version": "0.1.0", "decision": {"result": "APPROVE"}}

        emitter = CloudEventEmitter()

        # Test with invalid trace_id
        ce = emitter.emit_decision_event(
            decision_data, "invalid_trace_id", emit_to_subscriber=False
        )
        assert ce is None

    @patch("httpx.Client.post")
    def test_emit_to_subscriber_success(self, mock_post):
        """Test successful emission to subscriber URL."""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {"actor": {"id": "test"}, "channel": "web", "geo": {}, "metadata": {}},
            "cart": {"amount": "100.00", "currency": "USD", "items": [], "geo": {}},
            "payment": {
                "method": "card",
                "modality": "immediate",
                "auth_requirements": [],
                "metadata": {},
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.15,
                "reasons": [],
                "actions": [],
                "meta": {},
            },
            "signing": {"vc_proof": None, "receipt_hash": "sha256:abc123"},
        }

        emitter = CloudEventEmitter(subscriber_url="http://localhost:8080/events")
        ce = emitter.emit_decision_event(
            decision_data, "txn_1234567890abcdef", emit_to_subscriber=True
        )

        assert ce is not None
        mock_post.assert_called_once()

        # Verify POST request details
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8080/events"
        assert "application/cloudevents+json" in call_args[1]["headers"]["Content-Type"]

    @patch("httpx.Client.post")
    def test_emit_to_subscriber_failure(self, mock_post):
        """Test emission failure to subscriber URL."""
        # Mock HTTP error
        mock_post.side_effect = Exception("Connection error")

        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": {"id": "user_12345", "type": "individual"},
                "channel": "web",
                "geo": {"country": "US", "region": "CA", "city": "San Francisco"},
            },
            "cart": {"total": 100.0, "currency": "USD", "items": []},
            "payment": {"method": "card", "amount": 100.0, "currency": "USD"},
            "decision": {"result": "APPROVE", "risk_score": 0.15},
            "signing": {"signature": "test_signature"},
        }

        emitter = CloudEventEmitter(subscriber_url="http://localhost:8080/events")
        ce = emitter.emit_decision_event(
            decision_data, "txn_1234567890abcdef", emit_to_subscriber=True
        )

        # Should still create CloudEvent but fail to POST
        assert ce is not None
        assert ce.type == "ocn.orca.decision.v1"


class TestConvenienceFunctions:
    """Test convenience functions for CloudEvent emission."""

    @patch("src.orca.core.ce.get_cloud_event_emitter")
    def test_emit_decision_event_function(self, mock_get_emitter):
        """Test emit_decision_event convenience function."""
        # Mock emitter
        mock_emitter = MagicMock()
        mock_ce = CloudEvent(
            id="test-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.decision.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            data={},
        )
        mock_emitter.emit_decision_event.return_value = mock_ce
        mock_get_emitter.return_value = mock_emitter

        decision_data = {"ap2_version": "0.1.0", "decision": {"result": "APPROVE"}}
        result = emit_decision_event(decision_data, "txn_1234567890abcdef")

        assert result == mock_ce
        mock_emitter.emit_decision_event.assert_called_once_with(
            decision_data, "txn_1234567890abcdef"
        )


class TestCloudEventSchemaConformance:
    """Test CloudEvent conformance to ocn-common schemas."""

    def test_decision_schema_conformance(self):
        """Test that decision CloudEvents conform to schema."""
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": {
                    "id": "customer_123",
                    "type": "individual",
                    "metadata": {"loyalty_score": 0.8},
                },
                "channel": "web",
                "geo": {"country": "US", "region": "CA"},
                "metadata": {"velocity_24h": 2.0},
            },
            "cart": {
                "amount": "89.99",
                "currency": "USD",
                "items": [{"name": "Software License", "mcc": "5734"}],
                "geo": {"country": "US"},
            },
            "payment": {
                "method": "card",
                "modality": "immediate",
                "auth_requirements": ["none"],
                "metadata": {"method_risk": 0.2},
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.15,
                "reasons": [{"type": "low_risk", "message": "Low risk transaction"}],
                "actions": [{"type": "route", "target": "PROCESSOR_A"}],
                "meta": {
                    "model": "model:xgb",
                    "model_version": "1.0.0",
                    "trace_id": "txn_1234567890abcdef",
                },
            },
            "signing": {"vc_proof": None, "receipt_hash": "sha256:abc123def456"},
        }

        ce = CloudEvent(
            id="test-event-id",
            source="https://orca.ocn.ai/decision-engine",
            type="ocn.orca.decision.v1",
            subject="txn_1234567890abcdef",
            time=datetime.now(UTC).isoformat(),
            dataschema="https://schemas.ocn.ai/ap2/v1/decision.schema.json",
            data=decision_data,
        )

        # Validate against schema requirements
        assert ce.specversion == "1.0"
        assert ce.type == "ocn.orca.decision.v1"
        assert ce.datacontenttype == "application/json"
        assert ce.dataschema == "https://schemas.ocn.ai/ap2/v1/decision.schema.json"

        # Validate data structure
        assert "ap2_version" in ce.data
        assert "intent" in ce.data
        assert "cart" in ce.data
        assert "payment" in ce.data
        assert "decision" in ce.data
        assert "signing" in ce.data

        # Validate decision structure
        decision = ce.data["decision"]
        assert "result" in decision
        assert "risk_score" in decision
        assert decision["result"] in ["APPROVE", "DECLINE", "REVIEW"]
        assert 0.0 <= decision["risk_score"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])
