"""
Tests for contract validation using ocn-common schemas.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.orca.core.contract_validation import (
    ContractValidator,
    validate_cloud_event_contract,
    validate_decision_contract,
    validate_explanation_contract,
)


class TestContractValidator:
    """Test ContractValidator functionality."""

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = ContractValidator()
        assert validator.ocn_common_path is not None
        assert isinstance(validator.schemas, dict)

    def test_validate_ap2_decision_success(self):
        """Test successful AP2 decision validation."""
        validator = ContractValidator()

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
                "reasons": ["low_risk"],
                "actions": ["process_payment"],
                "meta": {},
            },
            "signing": {"vc_proof": None, "receipt_hash": "sha256:abc123"},
        }

        # Should use basic validation when schema not available
        result = validator.validate_ap2_decision(decision_data)
        assert result is True

    def test_validate_ap2_decision_failure(self):
        """Test AP2 decision validation failure."""
        validator = ContractValidator()

        # Missing required fields
        invalid_decision = {
            "ap2_version": "0.1.0",
            "intent": {},
            # Missing cart, payment, decision, signing
        }

        result = validator.validate_ap2_decision(invalid_decision)
        assert result is False

    def test_validate_ap2_explanation_success(self):
        """Test successful AP2 explanation validation."""
        validator = ContractValidator()

        explanation_data = {
            "trace_id": "txn_1234567890abcdef",
            "decision_result": "APPROVE",
            "explanation": "Low risk transaction approved.",
            "confidence": 0.85,
            "model_provenance": {
                "model_name": "gpt-4o-mini",
                "provider": "azure_openai",
                "version": "1.0.0",
                "timestamp": "2024-01-01T12:00:00Z",
                "processing_time_ms": 250,
                "tokens_used": 150,
            },
        }

        # Should use basic validation when schema not available
        result = validator.validate_ap2_explanation(explanation_data)
        assert result is True

    def test_validate_ap2_explanation_failure(self):
        """Test AP2 explanation validation failure."""
        validator = ContractValidator()

        # Missing required fields
        invalid_explanation = {
            "trace_id": "txn_1234567890abcdef",
            "explanation": "Test explanation",
            # Missing decision_result, confidence, model_provenance
        }

        result = validator.validate_ap2_explanation(invalid_explanation)
        assert result is False

    def test_validate_cloud_event_success(self):
        """Test successful CloudEvent validation."""
        validator = ContractValidator()

        ce_data = {
            "specversion": "1.0",
            "id": "test-event-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_1234567890abcdef",
            "time": "2024-01-01T12:00:00Z",
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

        # Should pass basic validation
        result = validator.validate_cloud_event(ce_data, "orca.decision.v1")
        assert result is True

    def test_validate_cloud_event_failure(self):
        """Test CloudEvent validation failure."""
        validator = ContractValidator()

        # Invalid CloudEvent structure
        invalid_ce = {
            "specversion": "2.0",  # Invalid version
            "id": "test-id",
            "type": "ocn.orca.decision.v1",
            "subject": "invalid_trace_id",  # Invalid format
            "time": "invalid-time",
            "data": {},
        }

        result = validator.validate_cloud_event(invalid_ce, "orca.decision.v1")
        assert result is False

    def test_validate_file_success(self):
        """Test successful file validation."""
        validator = ContractValidator()

        # Create temporary test file
        test_file = Path("test_decision.json")
        test_data = {
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

        try:
            with open(test_file, "w") as f:
                json.dump(test_data, f)

            result = validator.validate_file(test_file, "ap2_decision")
            assert result is True

        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def test_validate_file_not_found(self):
        """Test file validation with non-existent file."""
        validator = ContractValidator()

        result = validator.validate_file("non_existent_file.json", "ap2_decision")
        assert result is False

    def test_get_validation_errors(self):
        """Test getting detailed validation errors."""
        validator = ContractValidator()

        # Invalid decision data
        invalid_data = {
            "ap2_version": "0.1.0",
            # Missing required fields
        }

        errors = validator.get_validation_errors(invalid_data, "ap2_decision")
        assert isinstance(errors, list)
        assert len(errors) > 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("src.orca.core.contract_validation.get_contract_validator")
    def test_validate_decision_contract(self, mock_get_validator):
        """Test validate_decision_contract convenience function."""
        mock_validator = MagicMock()
        mock_validator.validate_ap2_decision.return_value = True
        mock_get_validator.return_value = mock_validator

        decision_data = {"ap2_version": "0.1.0", "decision": {"result": "APPROVE"}}
        result = validate_decision_contract(decision_data)

        assert result is True
        mock_validator.validate_ap2_decision.assert_called_once_with(decision_data)

    @patch("src.orca.core.contract_validation.get_contract_validator")
    def test_validate_explanation_contract(self, mock_get_validator):
        """Test validate_explanation_contract convenience function."""
        mock_validator = MagicMock()
        mock_validator.validate_ap2_explanation.return_value = True
        mock_get_validator.return_value = mock_validator

        explanation_data = {
            "trace_id": "txn_test",
            "decision_result": "APPROVE",
            "explanation": "Test explanation",
            "confidence": 0.85,
            "model_provenance": {"model_name": "test"},
        }

        result = validate_explanation_contract(explanation_data)

        assert result is True
        mock_validator.validate_ap2_explanation.assert_called_once_with(explanation_data)

    @patch("src.orca.core.contract_validation.get_contract_validator")
    def test_validate_cloud_event_contract(self, mock_get_validator):
        """Test validate_cloud_event_contract convenience function."""
        mock_validator = MagicMock()
        mock_validator.validate_cloud_event.return_value = True
        mock_get_validator.return_value = mock_validator

        ce_data = {
            "specversion": "1.0",
            "id": "test-id",
            "source": "https://orca.ocn.ai/decision-engine",
            "type": "ocn.orca.decision.v1",
            "subject": "txn_test123",
            "time": "2024-01-01T12:00:00Z",
            "data": {},
        }

        result = validate_cloud_event_contract(ce_data, "orca.decision.v1")

        assert result is True
        mock_validator.validate_cloud_event.assert_called_once_with(ce_data, "orca.decision.v1")


class TestOcnCommonIntegration:
    """Test integration with ocn-common schemas."""

    def test_ocn_common_path_resolution(self):
        """Test ocn-common path resolution."""
        # Test default path resolution
        validator = ContractValidator()
        # The ContractValidator calculates path from its own location
        # We need to resolve to absolute paths to avoid path comparison issues
        expected_path = (
            Path("src/orca/core/contract_validation.py").parent.parent.parent.parent
            / "external"
            / "ocn-common"
        )
        assert validator.ocn_common_path.resolve() == expected_path.resolve()

        # Test custom path
        custom_path = Path("/custom/ocn-common")
        validator = ContractValidator(ocn_common_path=custom_path)
        assert validator.ocn_common_path == custom_path

    def test_schema_loading(self):
        """Test schema loading from ocn-common."""
        validator = ContractValidator()

        # Should load schemas if they exist
        if validator.ocn_common_path.exists():
            assert isinstance(validator.schemas, dict)
        else:
            # Should handle missing ocn-common gracefully
            assert isinstance(validator.schemas, dict)
            assert len(validator.schemas) == 0

    def test_basic_validation_fallback(self):
        """Test that basic validation is used when schemas are not available."""
        validator = ContractValidator()

        # Test decision validation fallback
        valid_decision = {
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

        result = validator._basic_decision_validation(valid_decision)
        assert result is True

        # Test explanation validation fallback
        valid_explanation = {
            "trace_id": "txn_test123",
            "decision_result": "APPROVE",
            "explanation": "Test explanation",
            "confidence": 0.85,
            "model_provenance": {"model_name": "test"},
        }

        result = validator._basic_explanation_validation(valid_explanation)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
