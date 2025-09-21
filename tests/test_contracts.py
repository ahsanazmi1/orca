"""
Tests for OCN Common Contracts validation.
"""

import json
from pathlib import Path

import pytest

from src.ocn_common.contracts import (
    CONTENT_TYPE,
    SCHEMA_VERSION,
    ContractValidationError,
    ContractValidator,
    get_contract_validator,
    list_available_schemas,
    validate_cloudevent,
    validate_json,
)


class TestConstants:
    """Test exported constants."""

    def test_content_type(self):
        """Test CONTENT_TYPE constant."""
        assert CONTENT_TYPE == "application/vnd.ocn.ap2+json; version=1"

    def test_schema_version(self):
        """Test SCHEMA_VERSION constant."""
        assert SCHEMA_VERSION == "v1"


class TestSchemaLoader:
    """Test schema loading functionality."""

    def test_schema_loader_init(self):
        """Test schema loader initialization."""
        validator = ContractValidator()
        assert validator.schema_loader is not None

    def test_list_available_schemas(self):
        """Test listing available schemas."""
        schemas = list_available_schemas()
        assert "mandates" in schemas
        assert "events" in schemas

        # Check that we have expected mandate schemas
        expected_mandates = [
            "intent_mandate",
            "cart_mandate",
            "payment_mandate",
            "actor_profile",
            "agent_presence",
            "modality",
        ]
        for mandate in expected_mandates:
            assert mandate in schemas["mandates"]

        # Check that we have expected event schemas
        expected_events = ["orca.decision.v1", "orca.explanation.v1", "weave.audit.v1"]
        for event in expected_events:
            assert event in schemas["events"]


class TestContractValidator:
    """Test contract validation functionality."""

    @pytest.fixture
    def validator(self):
        """Create a contract validator instance."""
        return ContractValidator()

    def test_validate_json_valid_intent(self, validator):
        """Test validating a valid intent mandate."""
        intent_data = {
            "actor": {"id": "user_123", "type": "user"},
            "channel": "web",
            "geo": {"country": "US", "region": "CA", "city": "San Francisco"},
            "metadata": {},
        }

        assert validator.validate_json(intent_data, "intent_mandate") is True

    def test_validate_json_invalid_intent(self, validator):
        """Test validating an invalid intent mandate."""
        invalid_intent = {
            "actor": {
                "id": "user_123"
                # Missing required fields
            },
            "channel": "invalid_channel",  # Invalid enum value
            "geo": {},
            "metadata": {},
        }

        with pytest.raises(ContractValidationError):
            validator.validate_json(invalid_intent, "intent_mandate")

    def test_validate_json_valid_cart(self, validator):
        """Test validating a valid cart mandate."""
        cart_data = {
            "amount": "99.99",
            "currency": "USD",
            "items": [
                {
                    "id": "item_001",
                    "name": "Test Item",
                    "amount": "99.99",
                    "quantity": 1,
                    "category": "Test",
                }
            ],
            "geo": {"country": "US", "region": "CA", "city": "San Francisco"},
            "metadata": {},
        }

        assert validator.validate_json(cart_data, "cart_mandate") is True

    def test_validate_json_string_payload(self, validator):
        """Test validating JSON string payload."""
        intent_json = json.dumps(
            {
                "actor": {"id": "user_123", "type": "user"},
                "channel": "web",
                "geo": {"country": "US"},
                "metadata": {},
            }
        )

        assert validator.validate_json(intent_json, "intent_mandate") is True

    def test_validate_cloudevent_valid_decision(self, validator):
        """Test validating a valid decision CloudEvent."""
        decision_ce = {
            "specversion": "1.0",
            "id": "evt_123",
            "source": "https://orca.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_456",
            "time": "2024-01-21T12:00:00Z",
            "data": {
                "ap2_version": "0.1.0",
                "intent": {
                    "actor": {"id": "user_123", "type": "user"},
                    "channel": "web",
                    "geo": {"country": "US"},
                    "metadata": {},
                },
                "cart": {
                    "amount": "99.99",
                    "currency": "USD",
                    "items": [
                        {
                            "id": "item_001",
                            "name": "Test",
                            "amount": "99.99",
                            "quantity": 1,
                            "category": "Test",
                        }
                    ],
                    "geo": {"country": "US"},
                    "metadata": {},
                },
                "payment": {
                    "method": "card",
                    "modality": {"type": "immediate", "description": "Test"},
                    "auth_requirements": ["pin"],
                    "metadata": {},
                },
                "decision": {
                    "result": "APPROVE",
                    "risk_score": 0.15,
                    "reasons": ["Test reason"],
                    "actions": ["Test action"],
                    "meta": {},
                },
                "signing": {"vc_proof": None, "receipt_hash": "sha256:test"},
            },
        }

        assert validator.validate_cloudevent(decision_ce, "ocn.orca.decision.v1") is True

    def test_validate_cloudevent_invalid_type(self, validator):
        """Test validating CloudEvent with invalid type."""
        invalid_ce = {
            "specversion": "1.0",
            "id": "evt_123",
            "source": "https://test.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_456",
            "time": "2024-01-21T12:00:00Z",
            "data": {},
        }

        with pytest.raises(ContractValidationError):
            validator.validate_cloudevent(invalid_ce, "ocn.orca.decision.v1")

    def test_validate_cloudevent_unknown_type(self, validator):
        """Test validating CloudEvent with unknown type."""
        ce_data = {"test": "data"}

        with pytest.raises(ContractValidationError):
            validator.validate_cloudevent(ce_data, "unknown.event.type")

    def test_get_validation_errors(self, validator):
        """Test getting detailed validation errors."""
        invalid_intent = {
            "actor": {
                "id": "user_123"
                # Missing required fields
            },
            "channel": "invalid_channel",
            "geo": {},
            "metadata": {},
        }

        errors = validator.get_validation_errors(invalid_intent, "intent_mandate")
        assert len(errors) > 0
        assert all("message" in error for error in errors)
        assert all("path" in error for error in errors)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_validate_json_function(self):
        """Test validate_json convenience function."""
        intent_data = {
            "actor": {"id": "user_123", "type": "user"},
            "channel": "web",
            "geo": {"country": "US"},
            "metadata": {},
        }

        assert validate_json(intent_data, "intent_mandate") is True

    def test_validate_cloudevent_function(self):
        """Test validate_cloudevent convenience function."""
        decision_ce = {
            "specversion": "1.0",
            "id": "evt_123",
            "source": "https://orca.ocn.ai/v1",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_456",
            "time": "2024-01-21T12:00:00Z",
            "data": {
                "ap2_version": "0.1.0",
                "intent": {
                    "actor": {"id": "user_123", "type": "user"},
                    "channel": "web",
                    "geo": {"country": "US"},
                    "metadata": {},
                },
                "cart": {
                    "amount": "99.99",
                    "currency": "USD",
                    "items": [
                        {
                            "id": "item_001",
                            "name": "Test",
                            "amount": "99.99",
                            "quantity": 1,
                            "category": "Test",
                        }
                    ],
                    "geo": {"country": "US"},
                    "metadata": {},
                },
                "payment": {
                    "method": "card",
                    "modality": {"type": "immediate", "description": "Test"},
                    "auth_requirements": ["pin"],
                    "metadata": {},
                },
                "decision": {
                    "result": "APPROVE",
                    "risk_score": 0.15,
                    "reasons": ["Test"],
                    "actions": ["Test"],
                    "meta": {},
                },
                "signing": {"vc_proof": None, "receipt_hash": "sha256:test"},
            },
        }

        assert validate_cloudevent(decision_ce, "ocn.orca.decision.v1") is True

    def test_get_contract_validator_singleton(self):
        """Test that get_contract_validator returns singleton."""
        validator1 = get_contract_validator()
        validator2 = get_contract_validator()
        assert validator1 is validator2


class TestExampleValidation:
    """Test validation of example files."""

    @pytest.fixture
    def validator(self):
        """Create a contract validator instance."""
        return ContractValidator()

    def test_validate_ap2_examples(self, validator):
        """Test validating AP2 example files."""
        examples_dir = Path(__file__).parent.parent / "examples" / "ap2"

        if not examples_dir.exists():
            pytest.skip("Examples directory not found")

        # Test each AP2 example
        for example_file in examples_dir.glob("*.json"):
            with open(example_file) as f:
                data = json.load(f)

            # Validate the entire AP2 payload structure
            # This is a simplified validation - in practice you'd validate against a full AP2 schema
            assert "ap2_version" in data
            assert "intent" in data
            assert "cart" in data
            assert "payment" in data
            assert "decision" in data
            assert "signing" in data

    def test_validate_cloudevent_examples(self, validator):
        """Test validating CloudEvent example files."""
        examples_dir = Path(__file__).parent.parent / "examples" / "events"

        if not examples_dir.exists():
            pytest.skip("Examples directory not found")

        # Test decision CloudEvent
        decision_file = examples_dir / "decision_approve.json"
        if decision_file.exists():
            with open(decision_file) as f:
                decision_ce = json.load(f)

            assert validate_cloudevent(decision_ce, "ocn.orca.decision.v1") is True

        # Test explanation CloudEvent
        explanation_file = examples_dir / "explanation_approve.json"
        if explanation_file.exists():
            with open(explanation_file) as f:
                explanation_ce = json.load(f)

            assert validate_cloudevent(explanation_ce, "ocn.orca.explanation.v1") is True

        # Test audit CloudEvent
        audit_file = examples_dir / "audit_approve.json"
        if audit_file.exists():
            with open(audit_file) as f:
                audit_ce = json.load(f)

            assert validate_cloudevent(audit_ce, "ocn.weave.audit.v1") is True


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def validator(self):
        """Create a contract validator instance."""
        return ContractValidator()

    def test_invalid_json_string(self, validator):
        """Test handling of invalid JSON string."""
        invalid_json = '{"invalid": json}'

        with pytest.raises(ContractValidationError):
            validator.validate_json(invalid_json, "intent_mandate")

    def test_nonexistent_schema(self, validator):
        """Test handling of nonexistent schema."""
        data = {"test": "data"}

        with pytest.raises(ContractValidationError):
            validator.validate_json(data, "nonexistent_schema")

    def test_malformed_schema_file(self, validator):
        """Test handling of malformed schema file."""
        # This test would require creating a malformed schema file
        # For now, we'll test the error handling in get_validation_errors
        invalid_data = "not a dict"

        errors = validator.get_validation_errors(invalid_data, "intent_mandate")
        assert len(errors) > 0
        assert "Invalid JSON" in errors[0]["message"]
