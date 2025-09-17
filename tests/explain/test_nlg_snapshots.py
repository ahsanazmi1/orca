"""Snapshot tests for AP2 NLG explanations using golden AP2 payloads."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.orca.core.decision_contract import AP2DecisionContract, create_ap2_decision_contract
from src.orca.explain.nlg import AP2NLGExplainer
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


class TestAP2NLGSnapshots:
    """Snapshot tests for AP2 NLG explanations."""

    def setup_method(self):
        """Set up test environment."""
        self.explainer = AP2NLGExplainer()

    def create_test_ap2_contract(
        self,
        result: str = "APPROVE",
        risk_score: float = 0.1,
        reasons: list = None,
        actions: list = None,
        amount: float = 100.0,
        currency: str = "USD",
        modality: PaymentModality = PaymentModality.IMMEDIATE,
        channel: ChannelType = ChannelType.WEB,
        actor: ActorType = ActorType.HUMAN,
        mcc: str = None,
        country: str = "US",
    ) -> AP2DecisionContract:
        """Create a test AP2 contract with specified parameters."""
        intent = IntentMandate(
            actor=actor,
            intent_type=IntentType.PURCHASE,
            channel=channel,
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
                    unit_price=Decimal(str(amount)),
                    total_price=Decimal(str(amount)),
                )
            ],
            amount=Decimal(str(amount)),
            currency=currency,
            mcc=mcc,
            geo=GeoLocation(country=country),
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=modality,
            auth_requirements=[AuthRequirement.PIN],
        )

        return create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result=result,
            risk_score=risk_score,
            reasons=reasons or [],
            actions=actions or [],
        )

    def test_approve_decision_snapshot(self):
        """Test snapshot for approved decision."""
        contract = self.create_test_ap2_contract(
            result="APPROVE",
            risk_score=0.1,
            amount=100.0,
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: APPROVE" in explanation
        assert "Risk score: 0.100" in explanation
        assert "AP2 context:" in explanation
        assert "IntentMandate.channel=web" in explanation
        assert "CartMandate.amount=100.0" in explanation
        assert "PaymentMandate.modality=immediate" in explanation

    def test_review_decision_high_ticket_snapshot(self):
        """Test snapshot for review decision due to high ticket."""
        from src.orca.core.decision_contract import create_decision_action, create_decision_reason

        contract = self.create_test_ap2_contract(
            result="REVIEW",
            risk_score=0.3,
            amount=750.0,
            reasons=[
                create_decision_reason(
                    "high_ticket", "Transaction amount $750.00 exceeds $500.00 threshold"
                )
            ],
            actions=[
                create_decision_action(
                    "manual_review", detail="High-value transaction requires manual review"
                )
            ],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: REVIEW" in explanation
        assert "Risk score: 0.300" in explanation
        assert "Reason 'high_ticket':" in explanation
        assert "CartMandate.amount=750.0" in explanation
        assert "CartMandate.currency=USD" in explanation
        assert "Action 'manual_review':" in explanation
        assert "DecisionOutcome.result=REVIEW" in explanation

    def test_decline_decision_ach_limit_snapshot(self):
        """Test snapshot for decline decision due to ACH limit."""
        from src.orca.core.decision_contract import create_decision_action, create_decision_reason

        contract = self.create_test_ap2_contract(
            result="DECLINE",
            risk_score=0.8,
            amount=2500.0,
            modality=PaymentModality.DEFERRED,
            reasons=[
                create_decision_reason(
                    "ach_limit_exceeded", "ACH transaction amount $2500.00 exceeds $2000 limit"
                )
            ],
            actions=[create_decision_action("fallback_card", detail="ACH limit exceeded")],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: DECLINE" in explanation
        assert "Risk score: 0.800" in explanation
        assert "Reason 'ach_limit_exceeded':" in explanation
        assert "PaymentMandate.modality=deferred" in explanation
        assert "CartMandate.amount=2500.0" in explanation
        assert "Action 'fallback_card':" in explanation

    def test_review_decision_location_mismatch_snapshot(self):
        """Test snapshot for review decision due to location mismatch."""
        from src.orca.core.decision_contract import create_decision_action, create_decision_reason

        contract = self.create_test_ap2_contract(
            result="REVIEW",
            risk_score=0.4,
            country="GB",
            reasons=[
                create_decision_reason(
                    "location_mismatch", "IP country 'GB' differs from billing country 'US'"
                )
            ],
            actions=[
                create_decision_action("manual_review", detail="Location verification required")
            ],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: REVIEW" in explanation
        assert "Reason 'location_mismatch':" in explanation
        assert "CartMandate.geo.country=GB" in explanation
        assert "IntentMandate.channel=web" in explanation
        assert "Action 'manual_review':" in explanation

    def test_review_decision_velocity_snapshot(self):
        """Test snapshot for review decision due to velocity."""
        from src.orca.core.decision_contract import create_decision_action, create_decision_reason

        contract = self.create_test_ap2_contract(
            result="REVIEW",
            risk_score=0.5,
            reasons=[
                create_decision_reason("velocity_flag", "24h velocity 4.5 exceeds 3.0 threshold")
            ],
            actions=[create_decision_action("manual_review", detail="Velocity review required")],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: REVIEW" in explanation
        assert "Reason 'velocity_flag':" in explanation
        assert "IntentMandate.channel=web" in explanation
        assert "IntentMandate.actor=human" in explanation
        assert "Action 'manual_review':" in explanation

    def test_review_decision_online_verification_snapshot(self):
        """Test snapshot for review decision due to online verification."""
        from src.orca.core.decision_contract import create_decision_action, create_decision_reason

        contract = self.create_test_ap2_contract(
            result="REVIEW",
            risk_score=0.3,
            amount=1500.0,
            reasons=[
                create_decision_reason(
                    "online_verification", "Online transaction requires additional verification"
                )
            ],
            actions=[
                create_decision_action("step_up_auth", detail="Strong authentication required")
            ],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: REVIEW" in explanation
        assert "Reason 'online_verification':" in explanation
        assert "IntentMandate.channel=web" in explanation
        assert "PaymentMandate.modality=immediate" in explanation
        assert "Action 'step_up_auth':" in explanation
        assert "PaymentMandate.auth_requirements" in explanation

    def test_decline_decision_high_risk_snapshot(self):
        """Test snapshot for decline decision due to high risk."""
        from src.orca.core.decision_contract import create_decision_action, create_decision_reason

        contract = self.create_test_ap2_contract(
            result="DECLINE",
            risk_score=0.9,
            reasons=[
                create_decision_reason("high_risk", "ML risk score 0.900 exceeds 0.800 threshold")
            ],
            actions=[create_decision_action("block_transaction", detail="High risk detected")],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: DECLINE" in explanation
        assert "Risk score: 0.900" in explanation
        assert "Reason 'high_risk':" in explanation
        assert "DecisionOutcome.risk_score=0.9" in explanation
        assert "DecisionOutcome.result=DECLINE" in explanation
        assert "Action 'block_transaction':" in explanation

    def test_multiple_reasons_snapshot(self):
        """Test snapshot for decision with multiple reasons."""
        from src.orca.core.decision_contract import create_decision_action, create_decision_reason

        contract = self.create_test_ap2_contract(
            result="REVIEW",
            risk_score=0.6,
            amount=800.0,
            reasons=[
                create_decision_reason(
                    "high_ticket", "Transaction amount $800.00 exceeds $500.00 threshold"
                ),
                create_decision_reason("velocity_flag", "24h velocity 3.5 exceeds 3.0 threshold"),
            ],
            actions=[
                create_decision_action("manual_review", detail="Multiple risk factors detected")
            ],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: REVIEW" in explanation
        assert "Reason 'high_ticket':" in explanation
        assert "Reason 'velocity_flag':" in explanation
        assert "CartMandate.amount=800.0" in explanation
        assert "IntentMandate.channel=web" in explanation
        assert "Action 'manual_review':" in explanation

    def test_pos_channel_snapshot(self):
        """Test snapshot for POS channel decision."""
        from src.orca.core.decision_contract import create_decision_action

        contract = self.create_test_ap2_contract(
            result="APPROVE",
            risk_score=0.1,
            channel=ChannelType.POS,
            actions=[
                create_decision_action("process_payment", detail="POS transaction processing")
            ],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: APPROVE" in explanation
        assert "IntentMandate.channel=pos" in explanation
        assert "Action 'process_payment':" in explanation

    def test_ach_modality_snapshot(self):
        """Test snapshot for ACH modality decision."""
        from src.orca.core.decision_contract import create_decision_action

        contract = self.create_test_ap2_contract(
            result="APPROVE",
            risk_score=0.2,
            modality=PaymentModality.DEFERRED,
            actions=[create_decision_action("process_payment", detail="ACH processing")],
        )

        explanation = self.explainer.explain_decision(contract)

        # Verify explanation contains expected elements
        assert "Decision: APPROVE" in explanation
        assert "PaymentMandate.modality=deferred" in explanation
        assert "Action 'process_payment':" in explanation

    def test_golden_file_snapshot(self):
        """Test snapshot using golden AP2 file."""
        golden_file = Path(__file__).parent.parent / "golden" / "decision.ap2.json"
        if golden_file.exists():
            with open(golden_file) as f:
                contract_data = json.load(f)

            contract = AP2DecisionContract(**contract_data)
            explanation = self.explainer.explain_decision(contract)

            # Verify explanation contains expected elements
            assert "Decision:" in explanation
            assert "AP2 context:" in explanation
            assert "IntentMandate.channel=" in explanation
            assert "CartMandate.amount=" in explanation
            assert "PaymentMandate.modality=" in explanation

    def test_legacy_decision_snapshot(self):
        """Test snapshot for legacy decision format."""
        explanation = self.explainer.explain_decision_legacy(
            decision_result="REVIEW",
            reasons=["high_ticket", "velocity_flag"],
            actions=["manual_review"],
            context={
                "cart_total": 750.0,
                "currency": "USD",
                "rail": "Card",
                "channel": "online",
            },
        )

        # Verify explanation contains expected elements
        assert "Decision: REVIEW" in explanation
        assert "Reason: high_ticket" in explanation
        assert "Reason: velocity_flag" in explanation
        assert "Action: manual_review" in explanation
        assert "Context: cart_total=750.0" in explanation
        assert "currency=USD" in explanation
        assert "rail=Card" in explanation
        assert "channel=online" in explanation


class TestAP2NLGGuardrails:
    """Test guardrails to prevent hallucinating fields."""

    def setup_method(self):
        """Set up test environment."""
        self.explainer = AP2NLGExplainer()

    def create_test_ap2_contract(self, **kwargs):
        """Helper method to create test AP2 contract."""
        # Use the same method as in the main test class
        intent = IntentMandate(
            actor=kwargs.get("actor", ActorType.HUMAN),
            intent_type=IntentType.PURCHASE,
            channel=kwargs.get("channel", ChannelType.WEB),
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
                    unit_price=Decimal(str(kwargs.get("amount", 100.0))),
                    total_price=Decimal(str(kwargs.get("amount", 100.0))),
                )
            ],
            amount=Decimal(str(kwargs.get("amount", 100.0))),
            currency=kwargs.get("currency", "USD"),
            mcc=kwargs.get("mcc"),
            geo=GeoLocation(country=kwargs.get("country", "US")),
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=kwargs.get("modality", PaymentModality.IMMEDIATE),
            auth_requirements=[AuthRequirement.PIN],
        )

        return create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result=kwargs.get("result", "APPROVE"),
            risk_score=kwargs.get("risk_score", 0.1),
            reasons=kwargs.get("reasons", []),
            actions=kwargs.get("actions", []),
        )

    def test_field_validation_valid_fields(self):
        """Test that valid AP2 fields pass validation."""
        valid_citations = [
            "CartMandate.amount=100.00",
            "IntentMandate.channel=web",
            "PaymentMandate.modality=immediate",
            "DecisionOutcome.result=APPROVE",
            "CartMandate.geo.country=US",
        ]

        for citation in valid_citations:
            assert self.explainer._validate_field_citation(
                citation
            ), f"Failed to validate: {citation}"

    def test_field_validation_invalid_fields(self):
        """Test that invalid fields fail validation."""
        invalid_citations = [
            "LegacyField.cart_total=100.00",
            "OldField.rail=Card",
            "CustomField.unknown=value",
            "NonExistentField.path=value",
        ]

        for citation in invalid_citations:
            assert not self.explainer._validate_field_citation(
                citation
            ), f"Should have failed: {citation}"

    def test_field_guardrails_coverage(self):
        """Test that field guardrails cover all expected AP2 fields."""
        expected_fields = {
            "intent.actor",
            "intent.channel",
            "intent.agent_presence",
            "cart.amount",
            "cart.currency",
            "cart.mcc",
            "cart.geo.country",
            "payment.modality",
            "payment.auth_requirements",
            "decision.result",
            "decision.risk_score",
        }

        for field in expected_fields:
            assert field in self.explainer.field_guardrails, f"Missing field in guardrails: {field}"

    def test_citation_filtering(self):
        """Test that invalid citations are filtered out."""
        # Test the validation function directly
        valid_citations = [
            "CartMandate.amount=100.00",
            "IntentMandate.channel=web",
            "PaymentMandate.modality=immediate",
        ]

        invalid_citations = [
            "LegacyField.cart_total=100.00",
            "CustomField.unknown=value",
            "NonExistentField.path=value",
        ]

        # Test valid citations
        for citation in valid_citations:
            assert self.explainer._validate_field_citation(citation), f"Should validate: {citation}"

        # Test invalid citations
        for citation in invalid_citations:
            assert not self.explainer._validate_field_citation(
                citation
            ), f"Should not validate: {citation}"


class TestAP2NLGGlobalFunctions:
    """Test global NLG functions."""

    def test_explain_ap2_decision_global(self):
        """Test global explain_ap2_decision function."""
        from src.orca.explain.nlg import explain_ap2_decision

        contract = self.create_test_ap2_contract()
        explanation = explain_ap2_decision(contract)

        assert "Decision: APPROVE" in explanation
        assert "AP2 context:" in explanation

    def test_explain_legacy_decision_global(self):
        """Test global explain_legacy_decision function."""
        from src.orca.explain.nlg import explain_legacy_decision

        explanation = explain_legacy_decision(
            decision_result="REVIEW",
            reasons=["high_ticket"],
            actions=["manual_review"],
            context={"cart_total": 500.0},
        )

        assert "Decision: REVIEW" in explanation
        assert "Reason: high_ticket" in explanation
        assert "Action: manual_review" in explanation
        assert "cart_total=500.0" in explanation

    def create_test_ap2_contract(self, **kwargs):
        """Helper method to create test AP2 contract."""
        # Use the same method as in the main test class
        intent = IntentMandate(
            actor=kwargs.get("actor", ActorType.HUMAN),
            intent_type=IntentType.PURCHASE,
            channel=kwargs.get("channel", ChannelType.WEB),
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
                    unit_price=Decimal(str(kwargs.get("amount", 100.0))),
                    total_price=Decimal(str(kwargs.get("amount", 100.0))),
                )
            ],
            amount=Decimal(str(kwargs.get("amount", 100.0))),
            currency=kwargs.get("currency", "USD"),
            mcc=kwargs.get("mcc"),
            geo=GeoLocation(country=kwargs.get("country", "US")),
        )

        payment = PaymentMandate(
            instrument_ref="card_123456789",
            modality=kwargs.get("modality", PaymentModality.IMMEDIATE),
            auth_requirements=[AuthRequirement.PIN],
        )

        return create_ap2_decision_contract(
            intent=intent,
            cart=cart,
            payment=payment,
            result=kwargs.get("result", "APPROVE"),
            risk_score=kwargs.get("risk_score", 0.1),
            reasons=kwargs.get("reasons", []),
            actions=kwargs.get("actions", []),
        )
