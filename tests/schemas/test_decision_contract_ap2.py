"""Tests for AP2 Decision Contract and Legacy Adapter."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.orca.core.decision_contract import (
    AP2DecisionContract,
    DecisionMeta,
    DecisionOutcome,
    LegacyDecisionRequest,
    LegacyDecisionResponse,
    ap2_contract_from_json,
    ap2_contract_to_json,
    create_ap2_decision_contract,
    create_decision_action,
    create_decision_reason,
    validate_ap2_contract,
)
from src.orca.core.decision_legacy_adapter import (
    DecisionLegacyAdapter,
    roundtrip_legacy_to_ap2_to_legacy,
)
from src.orca.mandates.ap2_types import (
    ActorType,
    AgentPresence,
    AuthRequirement,
    CartItem,
    CartMandate,
    ChannelType,
    IntentMandate,
    IntentType,
    PaymentMandate,
    PaymentModality,
)


class TestAP2DecisionContract:
    """Test AP2 Decision Contract creation and validation."""

    def test_create_ap2_decision_contract(self):
        """Test creating an AP2 decision contract."""
        # Create AP2 mandates
        intent = IntentMandate(
            actor=ActorType.HUMAN,
            intent_type=IntentType.PURCHASE,
            channel=ChannelType.WEB,
            agent_presence=AgentPresence.ASSISTED,
            timestamps={
                "created": datetime.now(UTC),
                "expires": datetime.now(UTC) + timedelta(hours=1),
            },
        )

        cart = CartMandate(
            items=[
                CartItem(
                    id="item1",
                    name="Test Product",
                    quantity=1,
                    unit_price=Decimal("100.00"),
                    total_price=Decimal("100.00"),
                )
            ],
            amount=Decimal("100.00"),
            currency="USD",
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=PaymentModality.IMMEDIATE,
            auth_requirements=[AuthRequirement.PIN],
        )

        # Create decision reasons and actions
        reasons = [
            create_decision_reason("high_ticket", "Transaction amount exceeds threshold"),
        ]
        actions = [
            create_decision_action("manual_review", detail="Route to human reviewer"),
        ]

        # Create contract
        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="REVIEW",
            risk_score=0.75,
            reasons=reasons,
            actions=actions,
            model="rules_only",
        )

        assert contract.ap2_version == "0.1.0"
        assert contract.intent.actor == ActorType.HUMAN
        assert contract.cart.amount == Decimal("100.00")
        assert contract.payment.instrument_ref == "card_123456789"
        assert contract.decision.result == "REVIEW"
        assert contract.decision.risk_score == 0.75
        assert len(contract.decision.reasons) == 1
        assert len(contract.decision.actions) == 1

    def test_decision_contract_validation(self):
        """Test AP2 decision contract validation."""
        contract_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": datetime.now(UTC).isoformat(),
                    "expires": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": 100.00,
                        "total_price": 100.00,
                    }
                ],
                "amount": 100.00,
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.25,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "123e4567-e89b-12d3-a456-426614174000",
                    "version": "0.1.0",
                },
            },
            "signing": {
                "vc_proof": None,
                "receipt_hash": None,
            },
        }

        contract = validate_ap2_contract(contract_data)
        assert contract.ap2_version == "0.1.0"
        assert contract.decision.result == "APPROVE"
        assert contract.decision.risk_score == 0.25

    def test_decision_contract_json_roundtrip(self):
        """Test JSON serialization and deserialization."""
        # Create a contract
        intent = IntentMandate(
            actor=ActorType.AGENT,
            intent_type=IntentType.REFUND,
            channel=ChannelType.API,
            agent_presence=AgentPresence.AUTONOMOUS,
            timestamps={
                "created": datetime.now(UTC),
                "expires": datetime.now(UTC) + timedelta(hours=2),
            },
        )

        cart = CartMandate(
            items=[
                CartItem(
                    id="item2",
                    name="Refund Item",
                    quantity=1,
                    unit_price=Decimal("50.00"),
                    total_price=Decimal("50.00"),
                )
            ],
            amount=Decimal("50.00"),
            currency="EUR",
        )

        payment = PaymentMandate(
            instrument_token="tok_987654321",
            modality=PaymentModality.DEFERRED,
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.15,
            reasons=[],
            actions=[],
        )

        # Test JSON roundtrip
        json_str = ap2_contract_to_json(contract)
        restored_contract = ap2_contract_from_json(json_str)

        assert restored_contract.ap2_version == contract.ap2_version
        assert restored_contract.intent.actor == contract.intent.actor
        assert restored_contract.cart.amount == contract.cart.amount
        assert restored_contract.payment.instrument_token == contract.payment.instrument_token
        assert restored_contract.decision.result == contract.decision.result


class TestDecisionLegacyAdapter:
    """Test legacy decision adapter functionality."""

    def test_legacy_request_to_ap2_contract(self):
        """Test converting legacy request to AP2 contract."""
        legacy_request = LegacyDecisionRequest(
            cart_total=250.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"velocity_24h": 2.5, "risk_score": 0.3},
            context={"customer_id": "cust_123", "merchant_id": "merch_456"},
        )

        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_request)

        assert ap2_contract.ap2_version == "0.1.0"
        assert ap2_contract.intent.actor == ActorType.HUMAN
        assert ap2_contract.intent.intent_type == IntentType.PURCHASE
        assert ap2_contract.cart.amount == Decimal("250.0")
        assert ap2_contract.cart.currency == "USD"
        assert ap2_contract.payment.modality == PaymentModality.IMMEDIATE
        assert ap2_contract.payment.instrument_ref is not None

    def test_ap2_contract_to_legacy_response(self):
        """Test converting AP2 contract to legacy response."""
        # Create AP2 contract
        intent = IntentMandate(
            actor=ActorType.HUMAN,
            intent_type=IntentType.PURCHASE,
            channel=ChannelType.WEB,
            agent_presence=AgentPresence.NONE,
            timestamps={
                "created": datetime.now(UTC),
                "expires": datetime.now(UTC) + timedelta(hours=1),
            },
        )

        cart = CartMandate(
            items=[
                CartItem(
                    id="item1",
                    name="Test Product",
                    quantity=1,
                    unit_price=Decimal("150.00"),
                    total_price=Decimal("150.00"),
                )
            ],
            amount=Decimal("150.00"),
            currency="USD",
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=PaymentModality.IMMEDIATE,
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="REVIEW",
            risk_score=0.65,
            reasons=[
                create_decision_reason("high_ticket", "Amount exceeds $100 threshold"),
                create_decision_reason("velocity_flag", "High transaction velocity detected"),
            ],
            actions=[
                create_decision_action("manual_review", detail="Route to human reviewer"),
            ],
        )

        legacy_response = DecisionLegacyAdapter.ap2_contract_to_legacy_response(contract)

        assert legacy_response.decision == "REVIEW"
        assert legacy_response.reasons == ["high_ticket", "velocity_flag"]
        assert legacy_response.actions == ["manual_review"]
        assert legacy_response.meta["cart_total"] == 150.0
        assert legacy_response.meta["risk_score"] == 0.65
        assert legacy_response.meta["rail"] == "Card"
        assert legacy_response.meta["channel"] == "online"

    def test_update_ap2_contract_with_legacy_response(self):
        """Test updating AP2 contract with legacy response data."""
        # Create initial AP2 contract
        intent = IntentMandate(
            actor=ActorType.HUMAN,
            intent_type=IntentType.PURCHASE,
            channel=ChannelType.WEB,
            agent_presence=AgentPresence.NONE,
            timestamps={
                "created": datetime.now(UTC),
                "expires": datetime.now(UTC) + timedelta(hours=1),
            },
        )

        cart = CartMandate(
            items=[
                CartItem(
                    id="item1",
                    name="Test Product",
                    quantity=1,
                    unit_price=Decimal("200.00"),
                    total_price=Decimal("200.00"),
                )
            ],
            amount=Decimal("200.00"),
            currency="USD",
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=PaymentModality.IMMEDIATE,
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",  # Initial result
            risk_score=0.0,  # Initial risk score
            reasons=[],
            actions=[],
        )

        # Create legacy response with decision results
        legacy_response = LegacyDecisionResponse(
            decision="DECLINE",
            reasons=["high_risk", "velocity_flag"],
            actions=["block_transaction"],
            meta={
                "risk_score": 0.85,
                "timestamp": datetime.now(UTC).isoformat(),
                "transaction_id": "txn_123",
            },
        )

        # Update AP2 contract with legacy response
        updated_contract = DecisionLegacyAdapter.update_ap2_contract_with_legacy_response(
            contract, legacy_response
        )

        assert updated_contract.decision.result == "DECLINE"
        assert updated_contract.decision.risk_score == 0.85
        assert len(updated_contract.decision.reasons) == 2
        assert len(updated_contract.decision.actions) == 1
        assert updated_contract.decision.reasons[0].code == "high_risk"
        assert updated_contract.decision.actions[0].type == "block_transaction"

    def test_legacy_json_roundtrip(self):
        """Test JSON roundtrip through legacy adapter."""
        legacy_request_json = json.dumps(
            {
                "cart_total": 300.0,
                "currency": "USD",
                "rail": "ACH",
                "channel": "online",
                "features": {"velocity_24h": 1.0},
                "context": {"customer_id": "cust_789"},
            }
        )

        legacy_response_json = json.dumps(
            {
                "decision": "APPROVE",
                "reasons": [],
                "actions": ["process_payment"],
                "meta": {
                    "risk_score": 0.2,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "transaction_id": "txn_456",
                },
            }
        )

        # Test roundtrip conversion
        result_json = roundtrip_legacy_to_ap2_to_legacy(legacy_request_json, legacy_response_json)

        result = json.loads(result_json)
        assert result["decision"] == "APPROVE"
        assert result["actions"] == ["process_payment"]
        assert result["meta"]["risk_score"] == 0.2


class TestDecisionContractHelpers:
    """Test helper functions for decision contracts."""

    def test_create_decision_reason(self):
        """Test creating decision reasons."""
        reason = create_decision_reason("high_ticket", "Amount exceeds threshold")
        assert reason.code == "high_ticket"
        assert reason.detail == "Amount exceeds threshold"

    def test_create_decision_action(self):
        """Test creating decision actions."""
        action = create_decision_action("manual_review", "review_queue", "Route to human reviewer")
        assert action.type == "manual_review"
        assert action.to == "review_queue"
        assert action.detail == "Route to human reviewer"

    def test_create_decision_action_minimal(self):
        """Test creating decision actions with minimal parameters."""
        action = create_decision_action("process_payment")
        assert action.type == "process_payment"
        assert action.to is None
        assert action.detail is None


class TestGoldenFileValidation:
    """Test validation against golden files."""

    def test_ap2_decision_golden_file(self):
        """Test AP2 decision contract against golden file."""
        golden_file = Path(__file__).parent.parent / "golden" / "decision.ap2.json"
        if golden_file.exists():
            with open(golden_file) as f:
                contract_data = json.load(f)

            contract = validate_ap2_contract(contract_data)
            assert contract is not None
            assert contract.ap2_version == "0.1.0"

    def test_legacy_decision_golden_file(self):
        """Test legacy decision against golden file."""
        golden_file = Path(__file__).parent.parent / "golden" / "decision.legacy.json"
        if golden_file.exists():
            with open(golden_file) as f:
                legacy_data = json.load(f)

            # Test that it can be converted to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_data)
            assert ap2_contract is not None

            # Test that it can be converted back to legacy
            legacy_response = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)
            assert legacy_response is not None


class TestDecisionContractEdgeCases:
    """Test edge cases and error conditions."""

    def test_invalid_risk_score(self):
        """Test that invalid risk scores are rejected."""
        with pytest.raises(ValueError):
            DecisionOutcome(
                result="APPROVE",
                risk_score=1.5,  # Invalid: > 1.0
                reasons=[],
                actions=[],
                meta=DecisionMeta(model="rules_only", trace_id="test"),
            )

    def test_invalid_decision_result(self):
        """Test that invalid decision results are rejected."""
        with pytest.raises(ValueError):
            DecisionOutcome(
                result="INVALID",  # Invalid result
                risk_score=0.5,
                reasons=[],
                actions=[],
                meta=DecisionMeta(model="rules_only", trace_id="test"),
            )

    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        with pytest.raises(ValueError):
            AP2DecisionContract(
                # Missing required fields
                intent=None,
                cart=None,
                payment=None,
                decision=None,
            )

    def test_legacy_adapter_with_invalid_data(self):
        """Test legacy adapter with invalid data."""
        with pytest.raises(ValueError):
            DecisionLegacyAdapter.legacy_request_to_ap2_contract(
                {
                    "cart_total": -100.0,  # Invalid: negative amount
                    "currency": "USD",
                    "rail": "Card",
                    "channel": "online",
                }
            )
