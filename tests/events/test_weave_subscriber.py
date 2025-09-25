"""
Tests for Weave CloudEvents subscriber integration.
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from weave.subscriber import SchemaValidator, WeaveClient, WeaveReceipt, app


class TestWeaveSubscriber:
    """Test Weave CloudEvents subscriber endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_receive_decision_cloud_event(self):
        """Test receiving and processing a decision CloudEvent."""
        decision_ce = {
            "specversion": "1.0",
            "id": "test-decision-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_1234567890abcdef",
            "time": datetime.now(UTC).isoformat(),
            "datacontenttype": "application/json",
            "dataschema": "https://schemas.ocn.ai/ap2/v1/decision.schema.json",
            "data": {
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
            },
        }

        with patch("weave.subscriber.weave_client") as mock_weave:
            # Mock Weave receipt
            mock_receipt = WeaveReceipt(
                trace_id="txn_1234567890abcdef",
                receipt_hash="sha256:test_hash",
                event_type="decision",
                timestamp=datetime.now(UTC).isoformat(),
                block_height=1000001,
                transaction_hash="0x1234567890abcdef",
                gas_used=21000,
                gas_price="20000000000",
                status="success",
            )
            mock_weave.store_receipt.return_value = mock_receipt

            response = self.client.post("/events", json=decision_ce)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "receipt" in data
            assert data["receipt"]["trace_id"] == "txn_1234567890abcdef"
            assert data["receipt"]["event_type"] == "decision"

    def test_receive_explanation_cloud_event(self):
        """Test receiving and processing an explanation CloudEvent."""
        explanation_ce = {
            "specversion": "1.0",
            "id": "test-explanation-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.explanation.v1",
            "subject": "txn_1234567890abcdef",
            "time": datetime.now(UTC).isoformat(),
            "datacontenttype": "application/json",
            "dataschema": "https://schemas.ocn.ai/ap2/v1/explanation.schema.json",
            "data": {
                "trace_id": "txn_1234567890abcdef",
                "decision_result": "APPROVE",
                "explanation": "Low risk transaction approved.",
                "confidence": 0.85,
                "key_factors": ["low_velocity", "trusted_payment"],
                "model_provenance": {
                    "model_name": "gpt-4o-mini",
                    "provider": "azure_openai",
                    "version": "1.0.0",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "processing_time_ms": 250,
                    "tokens_used": 150,
                },
                "risk_score": 0.15,
                "reason_codes": ["VELOCITY_OK"],
            },
        }

        with patch("weave.subscriber.weave_client") as mock_weave:
            # Mock Weave receipt
            mock_receipt = WeaveReceipt(
                trace_id="txn_1234567890abcdef",
                receipt_hash="sha256:test_explanation_hash",
                event_type="explanation",
                timestamp=datetime.now(UTC).isoformat(),
                block_height=1000002,
                transaction_hash="0xabcdef1234567890",
                gas_used=21000,
                gas_price="20000000000",
                status="success",
            )
            mock_weave.store_receipt.return_value = mock_receipt

            response = self.client.post("/events", json=explanation_ce)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "receipt" in data
            assert data["receipt"]["trace_id"] == "txn_1234567890abcdef"
            assert data["receipt"]["event_type"] == "explanation"

    def test_invalid_cloud_event_format(self):
        """Test handling of invalid CloudEvent format."""
        invalid_ce = {
            "specversion": "1.0",
            "id": "test-id",
            # Missing required fields
            "type": "ocn.orca.decision.v1",
            "data": {},
        }

        response = self.client.post("/events", json=invalid_ce)
        assert response.status_code == 422  # Validation error

    def test_invalid_event_type(self):
        """Test handling of unsupported event type."""
        invalid_ce = {
            "specversion": "1.0",
            "id": "test-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.unknown.event.v1",  # Unsupported type
            "subject": "txn_1234567890abcdef",
            "time": datetime.now(UTC).isoformat(),
            "data": {},
        }

        response = self.client.post("/events", json=invalid_ce)
        # Should still process but with warning
        assert response.status_code in [200, 400]

    def test_invalid_subject_format(self):
        """Test handling of invalid subject format."""
        invalid_ce = {
            "specversion": "1.0",
            "id": "test-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "invalid_trace_id",  # Invalid format
            "time": datetime.now(UTC).isoformat(),
            "data": {"ap2_version": "0.1.0"},
        }

        response = self.client.post("/events", json=invalid_ce)
        assert response.status_code == 400

    def test_weave_client_error(self):
        """Test handling of Weave client errors."""
        decision_ce = {
            "specversion": "1.0",
            "id": "test-decision-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_1234567890abcdef",
            "time": datetime.now(UTC).isoformat(),
            "datacontenttype": "application/json",
            "dataschema": "https://schemas.ocn.ai/ap2/v1/decision.schema.json",
            "data": {
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
            },
        }

        with patch("weave.subscriber.weave_client") as mock_weave:
            # Mock Weave error
            mock_weave.store_receipt.side_effect = Exception("Weave connection failed")

            response = self.client.post("/events", json=decision_ce)
            assert response.status_code == 500

    def test_get_receipt(self):
        """Test retrieving receipt information."""
        trace_id = "txn_1234567890abcdef"

        response = self.client.get(f"/receipts/{trace_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "receipt" in data
        assert data["receipt"]["trace_id"] == trace_id

    def test_get_receipt_invalid_trace_id(self):
        """Test retrieving receipt with invalid trace_id format."""
        invalid_trace_id = "invalid_trace_id"

        response = self.client.get(f"/receipts/{invalid_trace_id}")
        assert response.status_code == 400


class TestWeaveClient:
    """Test Weave blockchain client functionality."""

    def test_store_receipt_success(self):
        """Test successful receipt storage."""
        weave_client = WeaveClient()

        receipt = weave_client.store_receipt(
            trace_id="txn_1234567890abcdef", receipt_hash="sha256:test_hash", event_type="decision"
        )

        assert isinstance(receipt, WeaveReceipt)
        assert receipt.trace_id == "txn_1234567890abcdef"
        assert receipt.receipt_hash == "sha256:test_hash"
        assert receipt.event_type == "decision"
        assert receipt.status == "success"
        assert receipt.block_height > 0
        assert receipt.transaction_hash.startswith("0x")

    def test_store_receipt_different_event_types(self):
        """Test storing receipts for different event types."""
        weave_client = WeaveClient()

        # Store decision receipt
        decision_receipt = weave_client.store_receipt(
            trace_id="txn_decision123", receipt_hash="sha256:decision_hash", event_type="decision"
        )
        assert decision_receipt.event_type == "decision"

        # Store explanation receipt
        explanation_receipt = weave_client.store_receipt(
            trace_id="txn_explanation123",
            receipt_hash="sha256:explanation_hash",
            event_type="explanation",
        )
        assert explanation_receipt.event_type == "explanation"

        # Block heights should be different
        assert decision_receipt.block_height != explanation_receipt.block_height


class TestSchemaValidator:
    """Test CloudEvent schema validation."""

    def test_valid_decision_event(self):
        """Test validation of valid decision CloudEvent."""
        validator = SchemaValidator()

        valid_ce_data = {
            "specversion": "1.0",
            "id": "test-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_1234567890abcdef",
            "time": datetime.now(UTC).isoformat(),
            "datacontenttype": "application/json",
            "dataschema": "https://schemas.ocn.ai/ap2/v1/decision.schema.json",
            "data": {
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
            },
        }

        # Create mock CloudEventRequest
        from weave.subscriber import CloudEventRequest

        ce = CloudEventRequest(**valid_ce_data)

        assert validator.validate_cloud_event(ce) is True

    def test_invalid_specversion(self):
        """Test validation with invalid specversion."""
        validator = SchemaValidator()

        invalid_ce_data = {
            "specversion": "2.0",  # Invalid version
            "id": "test-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_1234567890abcdef",
            "time": datetime.now(UTC).isoformat(),
            "data": {},
        }

        from weave.subscriber import CloudEventRequest

        ce = CloudEventRequest(**invalid_ce_data)

        assert validator.validate_cloud_event(ce) is False

    def test_invalid_timestamp_format(self):
        """Test validation with invalid timestamp format."""
        validator = SchemaValidator()

        invalid_ce_data = {
            "specversion": "1.0",
            "id": "test-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_1234567890abcdef",
            "time": "invalid-timestamp",  # Invalid format
            "data": {},
        }

        from weave.subscriber import CloudEventRequest

        ce = CloudEventRequest(**invalid_ce_data)

        assert validator.validate_cloud_event(ce) is False


class TestRoundTripIntegration:
    """Test round-trip integration: Orca → CloudEvent → Weave."""

    @patch("httpx.Client.post")
    def test_orca_to_weave_round_trip(self, mock_post):
        """Test complete round-trip from Orca to Weave."""
        from src.orca.core.ce import CloudEventEmitter

        # Mock successful HTTP response from Weave
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "message": "CloudEvent processed successfully",
            "receipt": {
                "trace_id": "txn_1234567890abcdef",
                "receipt_hash": "sha256:test_hash",
                "event_type": "decision",
                "block_height": 1000001,
                "transaction_hash": "0x1234567890abcdef",
                "status": "success",
            },
        }
        mock_post.return_value = mock_response

        # Create decision data
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": {"id": "customer_123"},
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

        # Emit CloudEvent
        emitter = CloudEventEmitter(subscriber_url="http://localhost:8080/events")
        ce = emitter.emit_decision_event(
            decision_data, "txn_1234567890abcdef", emit_to_subscriber=True
        )

        # Verify CloudEvent was created
        assert ce is not None
        assert ce.type == "ocn.orca.decision.v1"
        assert ce.subject == "txn_1234567890abcdef"

        # Verify HTTP request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8080/events"

        # Verify request body contains CloudEvent
        request_body = json.loads(call_args[1]["content"])
        assert request_body["type"] == "ocn.orca.decision.v1"
        assert request_body["subject"] == "txn_1234567890abcdef"
        assert request_body["data"] == decision_data


if __name__ == "__main__":
    pytest.main([__file__])
