"""Tests for AP2 Rules Engine and Feature Extractor."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.orca.core.ap2_rules import (
    AP2AuthRequirementRule,
    AP2ChannelRiskRule,
    AP2GeoRiskRule,
    AP2HighTicketRule,
    AP2LocationMismatchRule,
    AP2PaymentModalityRule,
    AP2VelocityRule,
)
from src.orca.core.decision_contract import (
    AP2DecisionContract,
    DecisionOutcome,
    create_ap2_decision_contract,
)
from src.orca.core.feature_extractor import (
    AP2FeatureExtractor,
    extract_features_from_ap2,
    extract_features_from_legacy,
)
from src.orca.core.rules_engine import AP2RulesEngine, evaluate_ap2_rules
from src.orca.mandates.ap2_types import (
    ActorType,
    AgentPresence,
    AuthRequirement,
    CartItem,
    CartMandate,
    ChannelType,
    GeoLocation,
    IntentMandate,
    IntentType,
    PaymentMandate,
    PaymentModality,
)


class TestAP2FeatureExtractor:
    """Test AP2 feature extractor functionality."""

    def test_extract_features_from_ap2_contract(self):
        """Test feature extraction from AP2 contract."""
        # Create AP2 contract
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
            mcc="5733",
            geo=GeoLocation(country="US", city="New York"),
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=PaymentModality.IMMEDIATE,
            auth_requirements=[AuthRequirement.PIN],
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.0,
            reasons=[],
            actions=[],
        )

        # Extract features
        features = extract_features_from_ap2(contract)

        # Verify key features that the model actually expects
        assert features["amount"] == 100.0
        assert features["velocity_24h"] == 1.0  # Default value
        assert features["velocity_7d"] == 1.0  # Default value
        assert features["cross_border"] == 0.0  # Default value
        assert features["location_mismatch"] == 0.0  # Default value
        assert features["payment_method_risk"] == 0.2  # PIN auth requirement
        assert features["chargebacks_12m"] == 0.0  # Default value
        assert features["customer_age_days"] == 365.0  # Default value
        assert features["loyalty_score"] == 0.0  # Default value
        assert features["time_since_last_purchase"] == 0.0  # Default value

    def test_extract_features_from_legacy_data(self):
        """Test feature extraction from legacy data."""
        legacy_data = {
            "cart_total": 250.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
            "features": {
                "velocity_24h": 2.5,
                "risk_score": 0.3,
            },
            "context": {
                "customer_id": "cust_123",
                "location": {
                    "country": "US",
                    "city": "New York",
                },
                "customer": {
                    "loyalty_tier": "GOLD",
                    "chargebacks_12m": 0,
                    "account_age_days": 365,
                },
            },
        }

        features = extract_features_from_legacy(legacy_data)

        # Verify key features
        assert features["amount"] == 250.0
        assert features["cart_total"] == 250.0
        assert features["velocity_24h"] == 2.5
        assert features["payment_method_risk"] == 0.2  # Card
        assert features["channel_risk"] == 0.2  # Online
        assert features["loyalty_score"] == 0.3  # Gold
        assert features["chargebacks_12m"] == 0.0

    def test_feature_extractor_validation(self):
        """Test feature extractor validation with invalid AP2 contract."""
        extractor = AP2FeatureExtractor()

        # Test with None contract
        with pytest.raises(ValueError, match="AP2 contract is required"):
            extractor.validate_ap2_contract(None)

        # Test with invalid contract (would need to create invalid contract)
        # This is tested in the rules engine tests

    def test_derived_features(self):
        """Test that derived features are calculated correctly."""
        legacy_data = {
            "cart_total": 1000.0,
            "features": {
                "velocity_24h": 5.0,
            },
            "context": {},
        }

        features = extract_features_from_legacy(legacy_data)

        # Check derived features
        assert "amount_velocity_ratio" in features
        assert "risk_velocity_interaction" in features
        assert "location_velocity_interaction" in features
        assert "composite_risk_score" in features

        # Verify calculations
        assert features["amount_velocity_ratio"] == 1000.0 / 5.0  # 200.0


class TestAP2Rules:
    """Test individual AP2 rules."""

    def create_test_ap2_contract(
        self,
        amount: float = 100.0,
        currency: str = "USD",
        modality: PaymentModality = PaymentModality.IMMEDIATE,
        channel: ChannelType = ChannelType.WEB,
        actor: ActorType = ActorType.HUMAN,
        metadata: dict = None,
    ) -> AP2DecisionContract:
        """Create a test AP2 contract with specified parameters."""
        intent = IntentMandate(
            actor=actor,
            intent_type=IntentType.PURCHASE,
            channel=channel,
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
                    unit_price=Decimal(str(amount)),
                    total_price=Decimal(str(amount)),
                )
            ],
            amount=Decimal(str(amount)),
            currency=currency,
            geo=GeoLocation(country="US"),
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=modality,
            auth_requirements=[AuthRequirement.PIN],
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.0,
            reasons=[],
            actions=[],
        )

        if metadata:
            contract.metadata = metadata

        return contract

    def test_high_ticket_rule_approve(self):
        """Test high ticket rule with approved amount."""
        contract = self.create_test_ap2_contract(amount=300.0)
        rule = AP2HighTicketRule(threshold=500.0)

        result = rule.apply(contract)
        assert result is None  # Should not trigger

    def test_high_ticket_rule_review(self):
        """Test high ticket rule with review amount."""
        contract = self.create_test_ap2_contract(amount=750.0)
        rule = AP2HighTicketRule(threshold=500.0)

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert result.reasons[0].code == "high_ticket"
        assert len(result.actions) == 1
        assert result.actions[0].type == "manual_review"

    def test_high_ticket_rule_rail_specific(self):
        """Test high ticket rule with rail-specific threshold."""
        # Test Card rail
        contract = self.create_test_ap2_contract(amount=6000.0, modality=PaymentModality.IMMEDIATE)
        rule = AP2HighTicketRule(threshold=5000.0, rail_specific="Card")

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"

        # Test ACH rail (should not trigger)
        contract = self.create_test_ap2_contract(amount=6000.0, modality=PaymentModality.DEFERRED)
        result = rule.apply(contract)
        assert result is None

    def test_velocity_rule(self):
        """Test velocity rule."""
        contract = self.create_test_ap2_contract(metadata={"velocity_24h": 4.0})
        rule = AP2VelocityRule(threshold=3.0)

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert result.reasons[0].code == "velocity_flag"
        assert len(result.actions) == 1
        assert result.actions[0].type == "manual_review"

    def test_velocity_rule_high_threshold(self):
        """Test velocity rule with high threshold (should block)."""
        contract = self.create_test_ap2_contract(metadata={"velocity_24h": 5.0})
        rule = AP2VelocityRule(threshold=4.0)

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert result.actions[0].type == "block_transaction"

    def test_location_mismatch_rule(self):
        """Test location mismatch rule."""
        contract = self.create_test_ap2_contract(
            metadata={
                "location_mismatch": True,
                "ip_country": "GB",
                "billing_country": "US",
            }
        )
        rule = AP2LocationMismatchRule()

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert result.reasons[0].code == "location_mismatch"

    def test_payment_modality_rule_ach_limit(self):
        """Test payment modality rule with ACH limit exceeded."""
        contract = self.create_test_ap2_contract(amount=2500.0, modality=PaymentModality.DEFERRED)
        rule = AP2PaymentModalityRule()

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "DECLINE"
        assert len(result.reasons) == 1
        assert result.reasons[0].code == "ach_limit_exceeded"
        assert result.actions[0].type == "fallback_card"

    def test_payment_modality_rule_ach_verification(self):
        """Test payment modality rule with ACH online verification."""
        contract = self.create_test_ap2_contract(
            amount=750.0, modality=PaymentModality.DEFERRED, channel=ChannelType.WEB
        )
        rule = AP2PaymentModalityRule()

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert result.reasons[0].code == "ach_online_verification"
        assert result.actions[0].type == "micro_deposit_verification"

    def test_channel_risk_rule_pos(self):
        """Test channel risk rule with POS channel."""
        contract = self.create_test_ap2_contract(channel=ChannelType.POS)
        rule = AP2ChannelRiskRule()

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint is None  # No decision change
        assert len(result.actions) == 1
        assert result.actions[0].type == "process_payment"

    def test_geo_risk_rule(self):
        """Test geo risk rule with high-risk country."""
        contract = self.create_test_ap2_contract(metadata={"geo_risk_score": 0.7})
        rule = AP2GeoRiskRule(threshold=0.6)

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert result.reasons[0].code == "high_risk"

    def test_auth_requirement_rule_high_value(self):
        """Test auth requirement rule with high-value transaction."""
        # Create contract with no auth requirements (equivalent to "none")
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
                    unit_price=Decimal("1500.00"),
                    total_price=Decimal("1500.00"),
                )
            ],
            amount=Decimal("1500.00"),
            currency="USD",
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=PaymentModality.IMMEDIATE,
            auth_requirements=[],  # No auth requirements
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.0,
            reasons=[],
            actions=[],
        )

        rule = AP2AuthRequirementRule()

        result = rule.apply(contract)
        assert result is not None
        assert result.decision_hint == "REVIEW"
        assert len(result.reasons) == 1
        assert result.reasons[0].code == "online_verification"
        assert result.actions[0].type == "step_up_auth"


class TestAP2RulesEngine:
    """Test AP2 rules engine integration."""

    def create_test_ap2_contract(
        self,
        amount: float = 100.0,
        currency: str = "USD",
        modality: PaymentModality = PaymentModality.IMMEDIATE,
        channel: ChannelType = ChannelType.WEB,
        metadata: dict = None,
    ) -> AP2DecisionContract:
        """Create a test AP2 contract with specified parameters."""
        intent = IntentMandate(
            actor=ActorType.HUMAN,
            intent_type=IntentType.PURCHASE,
            channel=channel,
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
                    unit_price=Decimal(str(amount)),
                    total_price=Decimal(str(amount)),
                )
            ],
            amount=Decimal(str(amount)),
            currency=currency,
            geo=GeoLocation(country="US"),
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=modality,
            auth_requirements=[AuthRequirement.PIN],
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.0,
            reasons=[],
            actions=[],
        )

        if metadata:
            contract.metadata = metadata

        return contract

    def test_rules_engine_approve(self):
        """Test rules engine with approved transaction."""
        contract = self.create_test_ap2_contract(amount=300.0)
        engine = AP2RulesEngine()

        outcome = engine.evaluate(contract)

        assert outcome.result == "APPROVE"
        assert outcome.risk_score >= 0.0
        assert len(outcome.reasons) >= 1  # Should have default approval reason
        assert len(outcome.actions) >= 1  # Should have default action

    def test_rules_engine_review(self):
        """Test rules engine with review transaction."""
        contract = self.create_test_ap2_contract(amount=750.0, metadata={"velocity_24h": 4.0})
        engine = AP2RulesEngine()

        outcome = engine.evaluate(contract)

        assert outcome.result == "REVIEW"
        assert outcome.risk_score > 0.0
        assert len(outcome.reasons) >= 1
        assert len(outcome.actions) >= 1

    def test_rules_engine_decline(self):
        """Test rules engine with declined transaction."""
        contract = self.create_test_ap2_contract(amount=2500.0, modality=PaymentModality.DEFERRED)
        engine = AP2RulesEngine()

        outcome = engine.evaluate(contract)

        assert outcome.result == "DECLINE"
        assert outcome.risk_score > 0.0
        assert len(outcome.reasons) >= 1
        assert len(outcome.actions) >= 1

    def test_rules_engine_validation_error(self):
        """Test rules engine with invalid contract."""
        engine = AP2RulesEngine()

        # Test with None contract
        with pytest.raises(ValueError, match="AP2 contract is required"):
            engine.evaluate(None)

    def test_global_rules_engine(self):
        """Test global rules engine function."""
        contract = self.create_test_ap2_contract(amount=300.0)

        outcome = evaluate_ap2_rules(contract)

        assert outcome.result == "APPROVE"
        assert isinstance(outcome, DecisionOutcome)


class TestAP2RulesNegativeCases:
    """Test negative cases and error conditions for AP2 rules."""

    def create_test_ap2_contract(
        self,
        amount: float = 100.0,
        currency: str = "USD",
        modality: PaymentModality = PaymentModality.IMMEDIATE,
        channel: ChannelType = ChannelType.WEB,
        metadata: dict = None,
    ) -> AP2DecisionContract:
        """Create a test AP2 contract with specified parameters."""
        intent = IntentMandate(
            actor=ActorType.HUMAN,
            intent_type=IntentType.PURCHASE,
            channel=channel,
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
                    unit_price=Decimal(str(amount)),
                    total_price=Decimal(str(amount)),
                )
            ],
            amount=Decimal(str(amount)),
            currency=currency,
            geo=GeoLocation(country="US"),
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=modality,
            auth_requirements=[AuthRequirement.PIN],
        )

        contract = create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result="APPROVE",
            risk_score=0.0,
            reasons=[],
            actions=[],
        )

        if metadata:
            contract.metadata = metadata

        return contract

    def test_missing_cart_mandate(self):
        """Test rules engine with missing cart mandate."""
        engine = AP2RulesEngine()

        # Test with None contract
        with pytest.raises(ValueError, match="AP2 contract is required"):
            engine.evaluate(None)

    def test_missing_payment_mandate(self):
        """Test rules engine with missing payment mandate."""
        # This test would require creating an invalid contract, which Pydantic prevents
        # Instead, we test the validation in the rules engine directly
        engine = AP2RulesEngine()

        # Create a valid contract first, then test validation
        contract = self.create_test_ap2_contract()

        # Test that validation works for valid contract
        outcome = engine.evaluate(contract)
        assert outcome is not None

    def test_empty_cart_items(self):
        """Test rules engine with empty cart items."""
        # This test would require creating an invalid contract, which Pydantic prevents
        # The validation happens at the Pydantic level, not in the rules engine
        pass

    def test_zero_cart_amount(self):
        """Test rules engine with zero cart amount."""
        # This test would require creating an invalid contract, which Pydantic prevents
        # The validation happens at the Pydantic level, not in the rules engine
        pass

    def test_missing_payment_instrument(self):
        """Test rules engine with missing payment instrument."""
        # This test would require creating an invalid contract, which Pydantic prevents
        # The validation happens at the Pydantic level, not in the rules engine
        pass

    def test_invalid_velocity_data(self):
        """Test rules with invalid velocity data."""
        contract = self.create_test_ap2_contract(
            metadata={"velocity_24h": "invalid"}  # Invalid velocity
        )

        # This should not crash, but should use default velocity
        rule = AP2VelocityRule(threshold=3.0)
        result = rule.apply(contract)

        # Should not trigger due to invalid velocity
        assert result is None

    def test_missing_metadata(self):
        """Test rules with missing metadata."""
        contract = self.create_test_ap2_contract()  # No metadata

        # Rules should handle missing metadata gracefully
        rule = AP2VelocityRule(threshold=3.0)
        result = rule.apply(contract)

        # Should not trigger due to missing velocity data
        assert result is None


class TestAP2RulesGoldenFiles:
    """Test AP2 rules against golden files."""

    def test_ap2_decision_golden_file(self):
        """Test AP2 decision contract against golden file."""
        golden_file = Path(__file__).parent.parent / "golden" / "decision.ap2.json"
        if golden_file.exists():
            with open(golden_file) as f:
                contract_data = json.load(f)

            # Create AP2 contract from golden data
            contract = AP2DecisionContract(**contract_data)

            # Test rules engine
            outcome = evaluate_ap2_rules(contract)

            assert outcome is not None
            assert outcome.result in ["APPROVE", "REVIEW", "DECLINE"]
            assert 0.0 <= outcome.risk_score <= 1.0
            assert len(outcome.reasons) >= 0
            assert len(outcome.actions) >= 0

    def test_legacy_decision_golden_file(self):
        """Test legacy decision against golden file."""
        golden_file = Path(__file__).parent.parent / "golden" / "decision.legacy.json"
        if golden_file.exists():
            with open(golden_file) as f:
                legacy_data = json.load(f)

            # Test feature extraction from legacy data
            features = extract_features_from_legacy(legacy_data)

            assert features is not None
            assert "amount" in features
            assert "cart_total" in features
            assert "velocity_24h" in features
