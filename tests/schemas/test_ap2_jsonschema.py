"""Tests for AP2 JSON Schema validation."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.orca.mandates.ap2_types import (
    CartMandate,
    IntentMandate,
    PaymentMandate,
    cart_from_json,
    cart_to_json,
    intent_from_json,
    intent_to_json,
    payment_from_json,
    payment_to_json,
    validate_cart,
    validate_intent,
    validate_payment,
)


class TestIntentMandateValidation:
    """Test IntentMandate validation against JSON schema."""

    def test_valid_intent_mandate(self):
        """Test that a valid intent mandate passes validation."""
        now = datetime.now(UTC)
        intent_data = {
            "actor": "human",
            "intent_type": "purchase",
            "channel": "web",
            "agent_presence": "assisted",
            "timestamps": {
                "created": now.isoformat(),
                "expires": (now + timedelta(hours=1)).isoformat(),
            },
        }

        intent = validate_intent(intent_data)
        assert intent.actor == "human"
        assert intent.intent_type == "purchase"
        assert intent.channel == "web"
        assert intent.agent_presence == "assisted"

    def test_intent_mandate_with_nonce(self):
        """Test intent mandate with explicit nonce."""
        now = datetime.now(UTC)
        intent_data = {
            "actor": "agent",
            "intent_type": "refund",
            "channel": "api",
            "agent_presence": "autonomous",
            "timestamps": {
                "created": now.isoformat(),
                "expires": (now + timedelta(hours=2)).isoformat(),
            },
            "nonce": "123e4567-e89b-12d3-a456-426614174000",
        }

        intent = validate_intent(intent_data)
        assert str(intent.nonce) == "123e4567-e89b-12d3-a456-426614174000"

    def test_intent_mandate_invalid_enum(self):
        """Test that invalid enum values are rejected."""
        now = datetime.now(UTC)
        intent_data = {
            "actor": "invalid_actor",
            "intent_type": "purchase",
            "channel": "web",
            "agent_presence": "assisted",
            "timestamps": {
                "created": now.isoformat(),
                "expires": (now + timedelta(hours=1)).isoformat(),
            },
        }

        with pytest.raises(ValueError):
            validate_intent(intent_data)

    def test_intent_mandate_missing_timestamps(self):
        """Test that missing required timestamps are rejected."""
        intent_data = {
            "actor": "human",
            "intent_type": "purchase",
            "channel": "web",
            "agent_presence": "assisted",
            "timestamps": {
                "created": datetime.now(UTC).isoformat(),
            },
        }

        with pytest.raises(ValueError):
            validate_intent(intent_data)

    def test_intent_mandate_invalid_timestamp_order(self):
        """Test that invalid timestamp order is rejected."""
        now = datetime.now(UTC)
        intent_data = {
            "actor": "human",
            "intent_type": "purchase",
            "channel": "web",
            "agent_presence": "assisted",
            "timestamps": {
                "created": now.isoformat(),
                "expires": (now - timedelta(hours=1)).isoformat(),
            },
        }

        with pytest.raises(ValueError):
            validate_intent(intent_data)


class TestCartMandateValidation:
    """Test CartMandate validation against JSON schema."""

    def test_valid_cart_mandate(self):
        """Test that a valid cart mandate passes validation."""
        cart_data = {
            "items": [
                {
                    "id": "item1",
                    "name": "Test Product",
                    "quantity": 2,
                    "unit_price": 10.50,
                    "total_price": 21.00,
                }
            ],
            "amount": 21.00,
            "currency": "USD",
        }

        cart = validate_cart(cart_data)
        assert len(cart.items) == 1
        assert cart.amount == Decimal("21.00")
        assert cart.currency == "USD"

    def test_cart_mandate_with_geo(self):
        """Test cart mandate with geographic information."""
        cart_data = {
            "items": [
                {
                    "id": "item1",
                    "name": "Test Product",
                    "quantity": 1,
                    "unit_price": 15.00,
                    "total_price": 15.00,
                }
            ],
            "amount": 15.00,
            "currency": "EUR",
            "geo": {
                "country": "DE",
                "city": "Berlin",
                "latitude": 52.5200,
                "longitude": 13.4050,
            },
        }

        cart = validate_cart(cart_data)
        assert cart.geo.country == "DE"
        assert cart.geo.city == "Berlin"

    def test_cart_mandate_amount_validation(self):
        """Test that cart amount must equal sum of item prices."""
        cart_data = {
            "items": [
                {
                    "id": "item1",
                    "name": "Test Product",
                    "quantity": 2,
                    "unit_price": 10.00,
                    "total_price": 20.00,
                }
            ],
            "amount": 25.00,  # Incorrect amount
            "currency": "USD",
        }

        with pytest.raises(ValueError):
            validate_cart(cart_data)

    def test_cart_mandate_invalid_currency(self):
        """Test that invalid currency format is rejected."""
        cart_data = {
            "items": [
                {
                    "id": "item1",
                    "name": "Test Product",
                    "quantity": 1,
                    "unit_price": 10.00,
                    "total_price": 10.00,
                }
            ],
            "amount": 10.00,
            "currency": "usd",  # Should be uppercase
        }

        with pytest.raises(ValueError):
            validate_cart(cart_data)

    def test_cart_mandate_empty_items(self):
        """Test that empty items list is rejected."""
        cart_data = {
            "items": [],
            "amount": 0.00,
            "currency": "USD",
        }

        with pytest.raises(ValueError):
            validate_cart(cart_data)


class TestPaymentMandateValidation:
    """Test PaymentMandate validation against JSON schema."""

    def test_valid_payment_mandate_with_ref(self):
        """Test that a valid payment mandate with instrument_ref passes validation."""
        payment_data = {
            "instrument_ref": "card_123456789",
            "modality": "immediate",
            "auth_requirements": ["pin"],
        }

        payment = validate_payment(payment_data)
        assert payment.instrument_ref == "card_123456789"
        assert payment.modality == "immediate"
        assert "pin" in payment.auth_requirements

    def test_valid_payment_mandate_with_token(self):
        """Test that a valid payment mandate with instrument_token passes validation."""
        payment_data = {
            "instrument_token": "tok_123456789",
            "modality": "deferred",
            "routing_hints": [
                {
                    "processor": "stripe",
                    "priority": 1,
                }
            ],
        }

        payment = validate_payment(payment_data)
        assert payment.instrument_token == "tok_123456789"
        assert payment.modality == "deferred"
        assert len(payment.routing_hints) == 1

    def test_payment_mandate_missing_instrument(self):
        """Test that payment mandate without instrument identifier is rejected."""
        payment_data = {
            "modality": "immediate",
        }

        with pytest.raises(ValueError):
            validate_payment(payment_data)

    def test_payment_mandate_invalid_modality(self):
        """Test that invalid modality is rejected."""
        payment_data = {
            "instrument_ref": "card_123456789",
            "modality": "invalid_modality",
        }

        with pytest.raises(ValueError):
            validate_payment(payment_data)


class TestJSONSerialization:
    """Test JSON serialization and deserialization."""

    def test_intent_json_roundtrip(self):
        """Test intent mandate JSON roundtrip."""
        now = datetime.now(UTC)
        original_intent = IntentMandate(
            actor="human",
            intent_type="purchase",
            channel="web",
            agent_presence="assisted",
            timestamps={
                "created": now,
                "expires": now + timedelta(hours=1),
            },
        )

        json_str = intent_to_json(original_intent)
        restored_intent = intent_from_json(json_str)

        assert restored_intent.actor == original_intent.actor
        assert restored_intent.intent_type == original_intent.intent_type
        assert restored_intent.channel == original_intent.channel
        assert restored_intent.agent_presence == original_intent.agent_presence

    def test_cart_json_roundtrip(self):
        """Test cart mandate JSON roundtrip."""
        from src.orca.mandates.ap2_types import CartItem

        original_cart = CartMandate(
            items=[
                CartItem(
                    id="item1",
                    name="Test Product",
                    quantity=2,
                    unit_price=Decimal("10.50"),
                    total_price=Decimal("21.00"),
                )
            ],
            amount=Decimal("21.00"),
            currency="USD",
        )

        json_str = cart_to_json(original_cart)
        restored_cart = cart_from_json(json_str)

        assert restored_cart.amount == original_cart.amount
        assert restored_cart.currency == original_cart.currency
        assert len(restored_cart.items) == len(original_cart.items)

    def test_payment_json_roundtrip(self):
        """Test payment mandate JSON roundtrip."""
        original_payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality="immediate",
            auth_requirements=["pin", "biometric"],
        )

        json_str = payment_to_json(original_payment)
        restored_payment = payment_from_json(json_str)

        assert restored_payment.instrument_ref == original_payment.instrument_ref
        assert restored_payment.modality == original_payment.modality
        assert restored_payment.auth_requirements == original_payment.auth_requirements


class TestGoldenFileValidation:
    """Test validation against golden files."""

    def test_intent_golden_file(self):
        """Test intent mandate against golden file."""
        golden_file = Path(__file__).parent.parent / "golden" / "ap2_intent_ok.json"
        if golden_file.exists():
            with open(golden_file) as f:
                intent_data = json.load(f)

            intent = validate_intent(intent_data)
            assert intent is not None

    def test_cart_golden_file(self):
        """Test cart mandate against golden file."""
        golden_file = Path(__file__).parent.parent / "golden" / "ap2_cart_ok.json"
        if golden_file.exists():
            with open(golden_file) as f:
                cart_data = json.load(f)

            cart = validate_cart(cart_data)
            assert cart is not None

    def test_payment_golden_file(self):
        """Test payment mandate against golden file."""
        golden_file = Path(__file__).parent.parent / "golden" / "ap2_payment_ok.json"
        if golden_file.exists():
            with open(golden_file) as f:
                payment_data = json.load(f)

            payment = validate_payment(payment_data)
            assert payment is not None
