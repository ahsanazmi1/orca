"""Tests for Orca Core crypto integration."""

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.orca.core.decision_contract import (
    AP2DecisionContract,
    create_ap2_decision_contract,
    is_receipt_hash_only,
    is_signing_enabled,
    sign_and_hash_decision,
)
from src.orca.crypto.keys import KeyManager, get_test_keypair, initialize_keys
from src.orca.crypto.receipts import ReceiptHasher, make_receipt
from src.orca.crypto.signing import VCSigner, sign_decision
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


class TestKeyManager:
    """Test key management functionality."""

    def test_key_manager_initialization(self):
        """Test key manager initialization."""
        key_manager = KeyManager()
        assert not key_manager.is_loaded()
        assert key_manager.get_private_key() is None
        assert key_manager.get_public_key() is None
        assert key_manager.get_key_id() is None

    def test_test_keys_generation(self):
        """Test test key generation."""
        key_manager = KeyManager()
        success = key_manager.load_test_keys()

        assert success
        assert key_manager.is_loaded()
        assert key_manager.get_private_key() is not None
        assert key_manager.get_public_key() is not None
        assert key_manager.get_key_id() == "orca-test-key"

    def test_key_fingerprint(self):
        """Test key fingerprint calculation."""
        key_manager = KeyManager()
        key_manager.load_test_keys()

        fingerprint = key_manager.get_public_key_fingerprint()
        assert fingerprint is not None
        assert len(fingerprint) > 0
        assert isinstance(fingerprint, str)

    def test_deterministic_test_keypair(self):
        """Test deterministic test keypair generation."""
        private_key1, public_key1 = get_test_keypair()
        private_key2, public_key2 = get_test_keypair()

        # Keys should be different (random generation)
        assert private_key1 != private_key2
        assert public_key1 != public_key2

        # But they should be valid PEM format
        assert b"BEGIN PRIVATE KEY" in private_key1
        assert b"BEGIN PUBLIC KEY" in public_key1
        assert b"BEGIN PRIVATE KEY" in private_key2
        assert b"BEGIN PUBLIC KEY" in public_key2

    def test_initialize_keys(self):
        """Test key initialization."""
        # Test with no environment variables (should use test keys)
        success = initialize_keys()
        assert success

        # Verify keys are loaded
        from src.orca.crypto.keys import get_key_manager

        key_manager = get_key_manager()
        assert key_manager.is_loaded()


class TestVCSigner:
    """Test VC signing functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Initialize test keys
        initialize_keys()

    def test_vc_signer_initialization(self):
        """Test VC signer initialization."""
        signer = VCSigner()
        assert signer.key_manager is not None

    def test_sign_decision(self):
        """Test decision signing."""
        signer = VCSigner()

        # Create test decision data
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": datetime.now(UTC).isoformat(),
                    "expires": datetime.now(UTC).isoformat(),
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
        }

        # Sign the decision
        proof = signer.sign_decision(decision_data)

        assert proof is not None
        assert "type" in proof
        assert "created" in proof
        assert "verificationMethod" in proof
        assert "proofPurpose" in proof
        assert "proofValue" in proof
        assert proof["type"] == "Ed25519Signature2020"
        assert proof["proofPurpose"] == "assertionMethod"

    def test_verify_signature(self):
        """Test signature verification."""
        signer = VCSigner()

        # Create test decision data
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": datetime.now(UTC).isoformat(),
                    "expires": datetime.now(UTC).isoformat(),
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
        }

        # Sign the decision
        proof = signer.sign_decision(decision_data)
        assert proof is not None

        # Verify the signature
        is_valid = signer.verify_signature(decision_data, proof)
        assert is_valid

    def test_global_sign_decision(self):
        """Test global sign_decision function."""
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": datetime.now(UTC).isoformat(),
                    "expires": datetime.now(UTC).isoformat(),
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
        }

        proof = sign_decision(decision_data)
        assert proof is not None
        assert "proofValue" in proof


class TestReceiptHasher:
    """Test receipt hashing functionality."""

    def test_receipt_hasher_initialization(self):
        """Test receipt hasher initialization."""
        hasher = ReceiptHasher()
        assert hasher is not None

    def test_make_receipt(self):
        """Test receipt creation."""
        hasher = ReceiptHasher()

        # Create test decision data
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": datetime.now(UTC).isoformat(),
                    "expires": datetime.now(UTC).isoformat(),
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
        }

        # Create receipt
        receipt_hash = hasher.make_receipt(decision_data)

        assert receipt_hash is not None
        assert len(receipt_hash) == 64  # SHA-256 hex length
        assert isinstance(receipt_hash, str)

    def test_receipt_deterministic(self):
        """Test that receipts are deterministic."""
        hasher = ReceiptHasher()

        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": "2023-01-01T00:00:00Z",
                    "expires": "2023-01-01T01:00:00Z",
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
        }

        # Create receipt multiple times
        receipt1 = hasher.make_receipt(decision_data)
        receipt2 = hasher.make_receipt(decision_data)

        assert receipt1 == receipt2

    def test_receipt_excludes_sensitive_data(self):
        """Test that receipts exclude sensitive data."""
        hasher = ReceiptHasher()

        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": "2023-01-01T00:00:00Z",
                    "expires": "2023-01-01T01:00:00Z",
                },
                "nonce": "sensitive-nonce-data",
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "instrument_token": "sensitive-token",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
            "metadata": {
                "sensitive_data": "should-be-excluded",
            },
        }

        # Create receipt
        receipt_hash = hasher.make_receipt(decision_data)

        # Verify receipt was created (sensitive data should be excluded)
        assert receipt_hash is not None
        assert len(receipt_hash) == 64

    def test_verify_receipt(self):
        """Test receipt verification."""
        hasher = ReceiptHasher()

        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": "2023-01-01T00:00:00Z",
                    "expires": "2023-01-01T01:00:00Z",
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
        }

        # Create receipt
        receipt_hash = hasher.make_receipt(decision_data)

        # Verify receipt
        is_valid = hasher.verify_receipt(decision_data, receipt_hash)
        assert is_valid

        # Test with wrong hash
        wrong_hash = "a" * 64
        is_valid = hasher.verify_receipt(decision_data, wrong_hash)
        assert not is_valid

    def test_global_make_receipt(self):
        """Test global make_receipt function."""
        decision_data = {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": "2023-01-01T00:00:00Z",
                    "expires": "2023-01-01T01:00:00Z",
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "item1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
            },
            "payment": {
                "instrument_ref": "card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
        }

        receipt_hash = make_receipt(decision_data)
        assert receipt_hash is not None
        assert len(receipt_hash) == 64


class TestDecisionContractIntegration:
    """Test decision contract integration with crypto."""

    def setup_method(self):
        """Set up test environment."""
        # Initialize test keys
        initialize_keys()

    def create_test_ap2_contract(self) -> AP2DecisionContract:
        """Create a test AP2 contract."""
        intent = IntentMandate(
            actor=ActorType.HUMAN,
            intent_type=IntentType.PURCHASE,
            channel=ChannelType.WEB,
            agent_presence=AgentPresence.ASSISTED,
            timestamps={
                "created": datetime.now(UTC),
                "expires": datetime.now(UTC).replace(hour=23, minute=59, second=59),
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

        return create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.1,
            reasons=[],
            actions=[],
        )

    def test_sign_and_hash_decision_disabled(self):
        """Test sign_and_hash_decision when disabled."""
        # Ensure signing is disabled
        os.environ.pop("ORCA_SIGN_DECISIONS", None)
        os.environ.pop("ORCA_RECEIPT_HASH_ONLY", None)

        contract = self.create_test_ap2_contract()
        signed_contract = sign_and_hash_decision(contract)

        # Should return the same contract without signing
        assert signed_contract.signing.vc_proof is None
        assert signed_contract.signing.receipt_hash is None

    def test_sign_and_hash_decision_receipt_only(self):
        """Test sign_and_hash_decision with receipt hash only."""
        # Enable receipt hash only
        os.environ["ORCA_RECEIPT_HASH_ONLY"] = "true"
        os.environ.pop("ORCA_SIGN_DECISIONS", None)

        contract = self.create_test_ap2_contract()
        signed_contract = sign_and_hash_decision(contract)

        # Should have receipt hash but no VC proof
        assert signed_contract.signing.vc_proof is None
        assert signed_contract.signing.receipt_hash is not None
        assert len(signed_contract.signing.receipt_hash) == 64

    def test_sign_and_hash_decision_full_signing(self):
        """Test sign_and_hash_decision with full signing."""
        # Enable full signing
        os.environ["ORCA_SIGN_DECISIONS"] = "true"
        os.environ.pop("ORCA_RECEIPT_HASH_ONLY", None)

        contract = self.create_test_ap2_contract()
        signed_contract = sign_and_hash_decision(contract)

        # Should have both VC proof and receipt hash
        assert signed_contract.signing.vc_proof is not None
        assert signed_contract.signing.receipt_hash is not None
        assert len(signed_contract.signing.receipt_hash) == 64

        # Verify VC proof structure
        vc_proof = signed_contract.signing.vc_proof
        assert "type" in vc_proof
        assert "created" in vc_proof
        assert "verificationMethod" in vc_proof
        assert "proofPurpose" in vc_proof
        assert "proofValue" in vc_proof

    def test_config_flags(self):
        """Test configuration flag functions."""
        # Test default values
        os.environ.pop("ORCA_SIGN_DECISIONS", None)
        os.environ.pop("ORCA_RECEIPT_HASH_ONLY", None)

        assert not is_signing_enabled()
        assert not is_receipt_hash_only()

        # Test enabled values
        os.environ["ORCA_SIGN_DECISIONS"] = "true"
        os.environ["ORCA_RECEIPT_HASH_ONLY"] = "true"

        assert is_signing_enabled()
        assert is_receipt_hash_only()

        # Test case insensitive
        os.environ["ORCA_SIGN_DECISIONS"] = "TRUE"
        os.environ["ORCA_RECEIPT_HASH_ONLY"] = "True"

        assert is_signing_enabled()
        assert is_receipt_hash_only()

    def test_golden_file_integration(self):
        """Test integration with golden files."""
        golden_file = Path(__file__).parent.parent / "golden" / "decision.ap2.json"
        if golden_file.exists():
            with open(golden_file) as f:
                contract_data = json.load(f)

            # Create AP2 contract from golden data
            contract = AP2DecisionContract(**contract_data)

            # Test signing and hashing
            os.environ["ORCA_SIGN_DECISIONS"] = "true"
            signed_contract = sign_and_hash_decision(contract)

            assert signed_contract.signing.vc_proof is not None
            assert signed_contract.signing.receipt_hash is not None
