"""
Integration tests for ocn-common schema validation.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.orca.core.ce import CloudEventEmitter, emit_decision_event, emit_explanation_event
from src.orca.core.contract_validation import get_contract_validator


class TestOcnCommonIntegration:
    """Test complete integration with ocn-common schemas."""

    def test_contract_validator_with_ocn_common(self):
        """Test contract validator with ocn-common schemas."""
        validator = get_contract_validator()

        # Test that validator can be initialized
        assert validator is not None
        assert validator.ocn_common_path is not None

        # Test that schemas are loaded (even if empty)
        assert isinstance(validator.schemas, dict)

    def test_decision_contract_validation_integration(self):
        """Test decision contract validation integration."""
        validator = get_contract_validator()

        # Valid AP2 decision data
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

        # Should validate successfully (using basic validation if schemas not available)
        result = validator.validate_ap2_decision(decision_data)
        assert result is True

    def test_explanation_contract_validation_integration(self):
        """Test explanation contract validation integration."""
        validator = get_contract_validator()

        # Valid AP2 explanation data
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

        # Should validate successfully (using basic validation if schemas not available)
        result = validator.validate_ap2_explanation(explanation_data)
        assert result is True

    def test_cloud_event_validation_integration(self):
        """Test CloudEvent validation integration."""
        validator = get_contract_validator()

        # Valid CloudEvent data
        ce_data = {
            "specversion": "1.0",
            "id": "test-event-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_1234567890abcdef",
            "time": datetime.now(UTC).isoformat(),
            "datacontenttype": "application/json",
            "dataschema": "https://schemas.ocn.ai/ap2/v1/decision.schema.json",
            "data": {
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
            },
        }

        # Should validate successfully
        result = validator.validate_cloud_event(ce_data, "orca.decision.v1")
        assert result is True

    def test_cloud_events_emitter_integration(self):
        """Test CloudEvents emitter with contract validation."""
        emitter = CloudEventEmitter()

        # Valid decision data
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

        # Should emit successfully (without subscriber)
        ce = emitter.emit_decision_event(decision_data, "txn_test123", emit_to_subscriber=False)
        assert ce is not None
        assert ce.type == "ocn.orca.decision.v1"
        assert ce.subject == "txn_test123"

    def test_cloud_events_emitter_with_invalid_data(self):
        """Test CloudEvents emitter with invalid data."""
        emitter = CloudEventEmitter()

        # Invalid decision data (missing required fields)
        invalid_decision_data = {
            "ap2_version": "0.1.0",
            # Missing required fields
        }

        # Should fail validation and return None
        ce = emitter.emit_decision_event(
            invalid_decision_data, "txn_test123", emit_to_subscriber=False
        )
        assert ce is None

    def test_convenience_functions_integration(self):
        """Test convenience functions with contract validation."""
        # Valid decision data
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

        # Should emit successfully
        ce = emit_decision_event(decision_data, "txn_test123")
        assert ce is not None
        assert ce.type == "ocn.orca.decision.v1"

        # Valid explanation data
        explanation_data = {
            "trace_id": "txn_test123",
            "decision_result": "APPROVE",
            "explanation": "Test explanation",
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

        # Should emit successfully
        ce = emit_explanation_event(explanation_data, "txn_test123")
        assert ce is not None
        assert ce.type == "ocn.orca.explanation.v1"

    def test_file_validation_integration(self):
        """Test file validation integration."""
        validator = get_contract_validator()

        # Create temporary test files
        test_decision_file = Path("test_decision_integration.json")
        test_explanation_file = Path("test_explanation_integration.json")

        try:
            # Valid decision file
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
                "signing": {"vc_proof": None, "receipt_hash": "sha256:test"},
            }

            with open(test_decision_file, "w") as f:
                json.dump(decision_data, f)

            # Valid explanation file
            explanation_data = {
                "trace_id": "txn_test123",
                "decision_result": "APPROVE",
                "explanation": "Test explanation",
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

            with open(test_explanation_file, "w") as f:
                json.dump(explanation_data, f)

            # Validate files
            decision_result = validator.validate_file(test_decision_file, "ap2_decision")
            explanation_result = validator.validate_file(test_explanation_file, "ap2_explanation")

            assert decision_result is True
            assert explanation_result is True

        finally:
            # Clean up
            for file_path in [test_decision_file, test_explanation_file]:
                if file_path.exists():
                    file_path.unlink()

    def test_ocn_common_directory_structure(self):
        """Test that ocn-common directory structure is correct."""
        ocn_common_path = Path("external/ocn-common")

        # Check if ocn-common directory exists
        assert ocn_common_path.exists(), "external/ocn-common directory should exist"

        # Check CloudEvents schemas directory
        events_path = ocn_common_path / "common/events/v1"
        if events_path.exists():
            # Check for schema files
            schema_files = list(events_path.glob("*.schema.json"))
            assert len(schema_files) > 0, "Should have CloudEvents schema files"

            # Validate schema file structure
            for schema_file in schema_files:
                with open(schema_file) as f:
                    schema = json.load(f)

                # Check required fields
                required_fields = ["$schema", "$id", "title", "description", "type", "properties"]
                for field in required_fields:
                    assert (
                        field in schema
                    ), f"Schema {schema_file.name} missing required field: {field}"

        # Check AP2 schemas directory
        ap2_path = ocn_common_path / "common/mandates/ap2/v1"
        if ap2_path.exists():
            # Should have README
            readme_file = ap2_path / "README.md"
            assert readme_file.exists(), "AP2 directory should have README.md"

    def test_error_handling(self):
        """Test error handling in contract validation."""
        validator = get_contract_validator()

        # Test with None data
        result = validator.validate_ap2_decision(None)
        assert result is False

        # Test with empty data
        result = validator.validate_ap2_decision({})
        assert result is False

        # Test with invalid trace_id format
        invalid_ce_data = {
            "specversion": "1.0",
            "id": "test-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "invalid_trace_id",
            "time": "2024-01-01T12:00:00Z",
            "data": {},
        }

        result = validator.validate_cloud_event(invalid_ce_data, "orca.decision.v1")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
