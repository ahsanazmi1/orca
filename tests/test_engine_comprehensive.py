"""
Comprehensive tests for engine (dispatcher) functionality.

This module tests the decision engine that orchestrates rules evaluation,
ML inference, and decision generation.
"""

from unittest.mock import MagicMock, patch

from orca_core.engine import determine_routing_hint, evaluate_rules, generate_explanation
from orca_core.models import DecisionRequest


class TestDetermineRoutingHint:
    """Test suite for routing hint determination."""

    def test_routing_hint_decline(self):
        """Test routing hint for decline decision."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        meta = {}

        hint = determine_routing_hint("DECLINE", request, meta)
        assert hint == "BLOCK_TRANSACTION"

    def test_routing_hint_route(self):
        """Test routing hint for route decision."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        meta = {}

        hint = determine_routing_hint("ROUTE", request, meta)
        assert hint == "ROUTE_TO_MANUAL_REVIEW"

    def test_routing_hint_visa_payment(self):
        """Test routing hint for Visa payment."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},
            context={"payment_method": {"type": "visa"}},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "ROUTE_TO_VISA_NETWORK"

    def test_routing_hint_mastercard_payment(self):
        """Test routing hint for Mastercard payment."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},
            context={"payment_method": {"type": "mastercard"}},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "ROUTE_TO_VISA_NETWORK"

    def test_routing_hint_amex_payment(self):
        """Test routing hint for Amex payment."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},
            context={"payment_method": {"type": "amex"}},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "ROUTE_TO_VISA_NETWORK"

    def test_routing_hint_ach_payment(self):
        """Test routing hint for ACH payment."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="ACH",
            channel="online",
            features={},
            context={"payment_method": {"type": "ach"}},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "ROUTE_TO_ACH_NETWORK"

    def test_routing_hint_bank_transfer_payment(self):
        """Test routing hint for bank transfer payment."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="ACH",
            channel="online",
            features={},
            context={"payment_method": {"type": "bank_transfer"}},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "ROUTE_TO_ACH_NETWORK"

    def test_routing_hint_unknown_payment(self):
        """Test routing hint for unknown payment method."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},
            context={"payment_method": {"type": "unknown"}},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "PROCESS_NORMALLY"

    def test_routing_hint_string_payment_method(self):
        """Test routing hint with string payment method."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},
            context={"payment_method": "visa"},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "ROUTE_TO_VISA_NETWORK"

    def test_routing_hint_missing_payment_method(self):
        """Test routing hint with missing payment method."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "PROCESS_NORMALLY"

    def test_routing_hint_case_insensitive(self):
        """Test routing hint with case insensitive payment method."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},
            context={"payment_method": {"type": "VISA"}},
        )
        meta = {}

        hint = determine_routing_hint("APPROVE", request, meta)
        assert hint == "ROUTE_TO_VISA_NETWORK"


class TestGenerateExplanation:
    """Test suite for explanation generation."""

    def test_generate_explanation_approve(self):
        """Test explanation generation for approve decision."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        reasons = []
        meta = {}

        explanation = generate_explanation("APPROVE", reasons, request, meta)

        assert "approved" in explanation.lower()
        assert "100.00" in explanation

    def test_generate_explanation_decline_high_risk(self):
        """Test explanation generation for decline with high risk."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        reasons = []
        meta = {"risk_score": 0.85}

        explanation = generate_explanation("DECLINE", reasons, request, meta)

        assert "declined" in explanation.lower()
        assert "0.850" in explanation

    def test_generate_explanation_decline_with_reasons(self):
        """Test explanation generation for decline with reasons."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        reasons = ["HIGH_VELOCITY", "CROSS_BORDER"]
        meta = {"risk_score": 0.5}

        explanation = generate_explanation("DECLINE", reasons, request, meta)

        assert "declined" in explanation.lower()
        assert "HIGH_VELOCITY" in explanation
        assert "CROSS_BORDER" in explanation

    def test_generate_explanation_route(self):
        """Test explanation generation for route decision."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        reasons = ["HIGH_AMOUNT", "UNUSUAL_LOCATION"]
        meta = {}

        explanation = generate_explanation("ROUTE", reasons, request, meta)

        assert "flagged" in explanation.lower()
        assert "manual review" in explanation.lower()
        assert "HIGH_AMOUNT" in explanation
        assert "UNUSUAL_LOCATION" in explanation

    def test_generate_explanation_unknown_decision(self):
        """Test explanation generation for unknown decision."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        reasons = []
        meta = {}

        explanation = generate_explanation("UNKNOWN", reasons, request, meta)

        assert "UNKNOWN" in explanation

    def test_generate_explanation_multiple_reasons(self):
        """Test explanation generation with multiple reasons."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        reasons = ["REASON1", "REASON2", "REASON3", "REASON4"]
        meta = {}

        explanation = generate_explanation("ROUTE", reasons, request, meta)

        # Should only include first 2 reasons
        assert "REASON1" in explanation
        assert "REASON2" in explanation
        assert "REASON3" not in explanation
        assert "REASON4" not in explanation

    def test_generate_explanation_empty_reasons(self):
        """Test explanation generation with empty reasons."""
        request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )
        reasons = []
        meta = {}

        explanation = generate_explanation("ROUTE", reasons, request, meta)

        assert "flagged" in explanation.lower()
        assert "manual review" in explanation.lower()


class TestEvaluateRules:
    """Test suite for rules evaluation engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.request = DecisionRequest(
            cart_total=100.0, currency="USD", rail="Card", channel="online", features={}, context={}
        )

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_approve_basic(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test basic approve decision."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction approved"

        response = evaluate_rules(self.request)

        assert response.decision == "APPROVE"
        assert response.status == "APPROVE"
        assert len(response.reasons) > 0
        assert len(response.actions) > 0
        assert response.meta.get("risk_score") == 0.3
        assert response.cart_total == 100.0
        assert response.rail == "Card"

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_decline_high_risk(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test decline decision due to high risk."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock high risk prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.85,
            "reason_codes": ["HIGH_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction declined"

        response = evaluate_rules(self.request)

        assert response.decision == "DECLINE"
        assert response.status == "DECLINE"
        assert any("HIGH_RISK" in reason for reason in response.reasons)
        assert "BLOCK" in response.actions
        assert response.meta.get("risk_score") == 0.85

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_route_review_hint(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test route decision due to review hint."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.4,
            "reason_codes": ["MEDIUM_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation with review hint
        mock_run_rules.return_value = ("REVIEW", ["HIGH_AMOUNT"], ["REVIEW"], ["HIGH_AMOUNT_RULE"])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction flagged for review"

        response = evaluate_rules(self.request)

        assert response.decision == "REVIEW"
        assert response.status == "ROUTE"
        assert "HIGH_AMOUNT" in response.reasons
        assert "REVIEW" in response.actions

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_with_llm_explanation(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test evaluation with LLM explanation."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_PLUS_AI")
        mock_ai_enabled.return_value = True

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "xgboost",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM explanation
        mock_llm_configured.return_value = True
        mock_llm_explanation = MagicMock()
        mock_llm_explanation.explanation = "AI-generated explanation"
        mock_llm_explanation.confidence = 0.95
        mock_llm_explanation.model_provenance = "gpt-4"
        mock_llm_explanation.processing_time_ms = 150
        mock_llm_explanation.tokens_used = 50
        mock_llm_explain.return_value = mock_llm_explanation

        mock_human_explanation.return_value = "Human explanation"

        response = evaluate_rules(self.request)

        assert response.decision == "APPROVE"
        assert "ai" in response.meta
        assert "llm_explanation" in response.meta["ai"]
        assert response.meta["ai"]["llm_explanation"]["explanation"] == "AI-generated explanation"
        assert response.meta["ai"]["llm_explanation"]["confidence"] == 0.95

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_llm_explanation_error(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test evaluation when LLM explanation fails."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_PLUS_AI")
        mock_ai_enabled.return_value = True

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "xgboost",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM failure
        mock_llm_configured.return_value = True
        mock_llm_explain.side_effect = Exception("LLM failed")

        mock_human_explanation.return_value = "Human explanation"

        # Should not raise exception
        response = evaluate_rules(self.request)

        assert response.decision == "APPROVE"
        assert "ai" in response.meta
        assert "llm_explanation" not in response.meta["ai"]

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_duplicate_reasons_removal(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test that duplicate reasons are removed."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation with duplicate reasons
        mock_run_rules.return_value = ("APPROVE", ["REASON1", "REASON2", "REASON1"], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction approved"

        response = evaluate_rules(self.request)

        # Should remove duplicates
        assert response.reasons.count("REASON1") == 1
        assert response.reasons.count("REASON2") == 1

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_no_reasons_default(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test evaluation with no reasons triggers default approval."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation with no reasons
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction approved"

        response = evaluate_rules(self.request)

        # Should have default approval reasons
        assert len(response.reasons) > 0
        assert "100.00" in response.reasons[0]  # Cart total in reason
        assert "Process payment" in response.actions
        assert "Send confirmation" in response.actions
        assert response.meta_structured.approved_amount == 100.0

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_metadata_structure(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test that metadata is properly structured."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], ["RULE1", "RULE2"])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction approved"

        response = evaluate_rules(self.request)

        # Check metadata structure
        assert "risk_score" in response.meta
        assert "rules_evaluated" in response.meta
        assert "timestamp" in response.meta
        assert "transaction_id" in response.meta
        assert "rail" in response.meta
        assert "channel" in response.meta
        assert "cart_total" in response.meta

        # Check structured metadata
        assert response.meta_structured is not None
        assert response.meta_structured.risk_score == 0.3
        assert response.meta_structured.rules_evaluated == ["RULE1", "RULE2"]
        assert response.meta_structured.rail == "Card"
        assert response.meta_structured.channel == "online"
        assert response.meta_structured.cart_total == 100.0

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_signals_triggered(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test that signals are properly tracked."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], ["RULE1", "RULE2"])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction approved"

        response = evaluate_rules(self.request)

        # Check signals triggered
        assert "RULE1" in response.signals_triggered
        assert "RULE2" in response.signals_triggered

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_high_risk_signals(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test that high risk adds HIGH_RISK signal."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock high risk prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.85,
            "reason_codes": ["HIGH_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], ["RULE1"])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction declined"

        response = evaluate_rules(self.request)

        # Check that HIGH_RISK is added to signals
        assert "RULE1" in response.signals_triggered
        assert "HIGH_RISK" in response.signals_triggered

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_routing_hint(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test that routing hint is properly set."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction approved"

        # Set up request with Visa payment
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},
            context={"payment_method": {"type": "visa"}},
        )

        response = evaluate_rules(request)

        assert response.routing_hint == "ROUTE_TO_VISA_NETWORK"

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_explanations(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test that explanations are properly generated."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Human explanation"

        response = evaluate_rules(self.request)

        assert response.explanation is not None
        assert response.explanation_human == "Human explanation"

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_backward_compatibility(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test backward compatibility fields."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Transaction approved"

        response = evaluate_rules(self.request)

        # Check backward compatibility fields
        assert response.transaction_id is not None
        assert response.cart_total == 100.0
        assert response.timestamp is not None
        assert response.rail == "Card"

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_ai_mode(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test evaluation in AI mode."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_PLUS_AI")
        mock_ai_enabled.return_value = True

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "xgboost",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "AI-enhanced explanation"

        response = evaluate_rules(self.request)

        assert response.decision == "APPROVE"
        assert "ai" in response.meta
        assert response.meta["ai"]["model_type"] == "xgboost"
        assert response.meta["ai"]["version"] == "1.0.0"

    @patch("orca_core.engine.get_settings")
    @patch("orca_core.engine.decision_mode")
    @patch("orca_core.engine.is_ai_enabled")
    @patch("orca_core.engine.predict_risk")
    @patch("orca_core.engine.run_rules")
    @patch("orca_core.engine.is_llm_configured")
    @patch("orca_core.engine.explain_decision_llm")
    @patch("orca_core.engine.generate_human_explanation")
    def test_evaluate_rules_rules_only_mode(
        self,
        mock_human_explanation,
        mock_llm_explain,
        mock_llm_configured,
        mock_run_rules,
        mock_predict_risk,
        mock_ai_enabled,
        mock_decision_mode,
        mock_get_settings,
    ):
        """Test evaluation in rules-only mode."""
        # Mock settings
        mock_get_settings.return_value = MagicMock()
        mock_decision_mode.return_value = MagicMock(value="RULES_ONLY")
        mock_ai_enabled.return_value = False

        # Mock ML prediction
        mock_predict_risk.return_value = {
            "risk_score": 0.3,
            "reason_codes": ["LOW_RISK"],
            "version": "1.0.0",
            "model_type": "stub",
        }

        # Mock rules evaluation
        mock_run_rules.return_value = ("APPROVE", [], [], [])

        # Mock LLM
        mock_llm_configured.return_value = False
        mock_human_explanation.return_value = "Rules-based explanation"

        response = evaluate_rules(self.request)

        assert response.decision == "APPROVE"
        assert "ai" in response.meta
        assert response.meta["ai"]["model_type"] == "stub"
