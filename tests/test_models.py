"""Tests for Pydantic models."""

import pytest
from orca_core.models import DecisionRequest, DecisionResponse
from pydantic import ValidationError


class TestDecisionRequest:
    """Test cases for DecisionRequest model."""

    def test_valid_request(self) -> None:
        """Test valid request creation."""
        request = DecisionRequest(cart_total=100.0)
        assert request.cart_total == 100.0
        assert request.currency == "USD"
        assert request.features == {}
        assert request.context == {}

    def test_request_with_all_fields(self) -> None:
        """Test request with all fields provided."""
        request = DecisionRequest(
            cart_total=250.0,
            currency="EUR",
            features={"risk_score": 0.5},
            context={"user_id": "123"},
        )
        assert request.cart_total == 250.0
        assert request.currency == "EUR"
        assert request.features == {"risk_score": 0.5}
        assert request.context == {"user_id": "123"}

    def test_invalid_cart_total(self) -> None:
        """Test validation for invalid cart total."""
        with pytest.raises(ValidationError):
            DecisionRequest(cart_total=-100.0)

    def test_zero_cart_total(self) -> None:
        """Test validation for zero cart total."""
        with pytest.raises(ValidationError):
            DecisionRequest(cart_total=0.0)


class TestDecisionResponse:
    """Test cases for DecisionResponse model."""

    def test_valid_response(self) -> None:
        """Test valid response creation."""
        response = DecisionResponse(decision="APPROVE")
        assert response.decision == "APPROVE"
        assert response.reasons == []
        assert response.actions == []
        assert response.meta == {}

    def test_response_with_all_fields(self) -> None:
        """Test response with all fields provided."""
        response = DecisionResponse(
            decision="REVIEW",
            reasons=["High amount"],
            actions=["Manual review"],
            meta={"rule": "HIGH_TICKET"},
        )
        assert response.decision == "REVIEW"
        assert response.reasons == ["High amount"]
        assert response.actions == ["Manual review"]
        assert response.meta == {"rule": "HIGH_TICKET"}

    def test_missing_decision(self) -> None:
        """Test validation for missing decision."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionResponse()
        assert "decision" in str(exc_info.value)
