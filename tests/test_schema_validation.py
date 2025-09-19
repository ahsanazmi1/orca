"""Schema validation tests for Week 2 enhanced decision contract."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.orca_core.models import DecisionRequest, DecisionResponse


class TestDecisionRequestValidation:
    """Test DecisionRequest schema validation."""

    def test_valid_request(self):
        """Test valid DecisionRequest passes validation."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            features={"velocity_24h": 2.0},
            context={"channel": "ecom"},
        )
        assert request.cart_total == 100.0
        assert request.currency == "USD"

    def test_invalid_cart_total_zero(self):
        """Test that cart_total must be > 0."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionRequest(cart_total=0.0)
        assert "greater than 0" in str(exc_info.value)

    def test_invalid_cart_total_negative(self):
        """Test that cart_total cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionRequest(cart_total=-50.0)
        assert "greater than 0" in str(exc_info.value)

    def test_default_currency(self):
        """Test default currency is USD."""
        request = DecisionRequest(cart_total=100.0)
        assert request.currency == "USD"

    def test_empty_features_and_context(self):
        """Test empty features and context are allowed."""
        request = DecisionRequest(cart_total=100.0)
        assert request.features == {}
        assert request.context == {}


class TestDecisionResponseValidation:
    """Test DecisionResponse schema validation."""

    def test_valid_response_legacy(self):
        """Test valid legacy DecisionResponse passes validation."""
        response = DecisionResponse(
            decision="APPROVE",
            reasons=["Low risk"],
            actions=["Process payment"],
            meta={"risk_score": 0.1},
        )
        assert response.decision == "APPROVE"
        assert response.status is None  # Legacy mode

    def test_valid_response_enhanced(self):
        """Test valid enhanced DecisionResponse with Week 2 fields."""
        response = DecisionResponse(
            decision="APPROVE",
            reasons=["Low risk"],
            actions=["Process payment"],
            meta={"risk_score": 0.1},
            status="APPROVE",
            signals_triggered=["LOW_RISK"],
            explanation="Transaction approved",
            routing_hint="PROCESS_NORMALLY",
            transaction_id="txn_123",
            cart_total=100.0,
            timestamp=datetime.now(),
        )
        assert response.status == "APPROVE"
        assert response.transaction_id == "txn_123"
        assert response.cart_total == 100.0
        assert response.timestamp is not None

    def test_invalid_status(self):
        """Test that status only accepts APPROVE/DECLINE/ROUTE."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionResponse(decision="APPROVE", status="INVALID_STATUS")
        assert "Input should be 'APPROVE', 'DECLINE' or 'ROUTE'" in str(exc_info.value)

    def test_required_legacy_fields(self):
        """Test that legacy fields are still required."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionResponse()  # Missing required fields
        assert "Field required" in str(exc_info.value)

    def test_optional_enhanced_fields(self):
        """Test that enhanced fields are optional."""
        response = DecisionResponse(
            decision="APPROVE",
            # All enhanced fields are None/empty by default
        )
        assert response.status is None
        assert response.signals_triggered == []
        assert response.explanation is None
        assert response.routing_hint is None
        assert response.transaction_id is None
        assert response.cart_total is None
        assert response.timestamp is None


class TestJSONSchemaValidation:
    """Test JSON schema validation against sample files."""

    def test_valid_json_samples(self):
        """Test that valid JSON samples pass validation."""
        sample_files = ["sample.json", "cart_scenario.json", "high_risk_sample.json"]

        for sample_file in sample_files:
            if Path(sample_file).exists():
                with open(sample_file) as f:
                    data = json.load(f)

                # Should create valid DecisionRequest
                request = DecisionRequest(**data)
                assert request.cart_total > 0
                assert request.currency == "USD"

    def test_invalid_json_fails_gracefully(self):
        """Test that invalid JSON fails gracefully."""
        invalid_data = {
            "cart_total": -100.0,  # Invalid: negative
            "currency": "USD",
        }

        with pytest.raises(ValidationError):
            DecisionRequest(**invalid_data)

    def test_malformed_json_handling(self):
        """Test handling of malformed JSON input."""
        malformed_json = '{"cart_total": 100.0, "currency": "USD"'  # Missing closing brace

        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed_json)

    def test_missing_required_fields(self):
        """Test that missing required fields fail validation."""
        incomplete_data = {
            "currency": "USD"
            # Missing cart_total
        }

        with pytest.raises(ValidationError) as exc_info:
            DecisionRequest(**incomplete_data)
        assert "cart_total" in str(exc_info.value)

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored gracefully."""
        data_with_extra = {
            "cart_total": 100.0,
            "currency": "USD",
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }

        # Should not raise ValidationError
        request = DecisionRequest(**data_with_extra)
        assert request.cart_total == 100.0
        assert request.currency == "USD"
        # Extra fields should not be accessible
        assert not hasattr(request, "extra_field")
