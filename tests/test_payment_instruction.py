"""
Unit tests for Orca Phase 4 Payment Instruction functionality.

Tests deterministic selection, explainability, counterfactuals, and golden fixtures.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path

from src.orca_core.models import (
    NegotiationRequest,
    NegotiationResponse,
    RailEvaluation,
    PolicyConstraint,
    TrustSignal,
    TreasuryConstraint,
    PaymentInstruction,
    CounterfactualAnalysis,
    RailType
)
from src.orca_core.payment_instruction import PaymentInstructionFinalizer


class TestPaymentInstructionFinalizer:
    """Test the PaymentInstructionFinalizer class."""

    @pytest.fixture
    def finalizer(self):
        """Create a PaymentInstructionFinalizer instance."""
        with patch('src.orca_core.payment_instruction.XGBoostInference'):
            return PaymentInstructionFinalizer()

    @pytest.fixture
    def sample_negotiation_response(self):
        """Create a sample negotiation response."""
        rail_evaluations = [
            RailEvaluation(
                rail_type="Card",
                score=0.85,
                cost=2.50,
                settlement_time_hours=24,
                confidence=0.9,
                risk_adjusted_cost=2.75,
                factors={"cost": 0.3, "speed": 0.4, "risk": 0.3},
                explanation="Card rail offers good balance of cost and speed"
            ),
            RailEvaluation(
                rail_type="ACH",
                score=0.75,
                cost=0.50,
                settlement_time_hours=72,
                confidence=0.8,
                risk_adjusted_cost=0.55,
                factors={"cost": 0.8, "speed": 0.2, "risk": 0.0},
                explanation="ACH rail offers lowest cost but slower settlement"
            )
        ]
        
        return NegotiationResponse(
            optimal_rail="Card",
            rail_evaluations=rail_evaluations,
            explanation="Card rail selected for optimal balance",
            confidence=0.85,
            trace_id="test_trace_123",
            negotiation_metadata={"test": "data"}
        )

    @pytest.fixture
    def sample_policy_constraints(self):
        """Create sample policy constraints."""
        return [
            PolicyConstraint(
                policy_type="max_cost",
                constraint_value=5.0,
                weight=0.8,
                description="Maximum cost per transaction"
            ),
            PolicyConstraint(
                policy_type="min_trust",
                constraint_value=0.7,
                weight=0.6,
                description="Minimum trust score requirement"
            )
        ]

    @pytest.fixture
    def sample_trust_signal(self):
        """Create a sample trust signal."""
        return TrustSignal(
            trust_score=0.8,
            risk_level="low",
            signals=[{"type": "device_fingerprint", "score": 0.9}],
            confidence=0.85
        )

    @pytest.fixture
    def sample_treasury_constraints(self):
        """Create sample treasury constraints."""
        return [
            TreasuryConstraint(
                constraint_type="available_balance",
                status="passed",
                available_balance=10000.0,
                constraint_value=100.0
            )
        ]

    def test_finalize_payment_instruction_deterministic(
        self,
        finalizer,
        sample_negotiation_response,
        sample_policy_constraints,
        sample_trust_signal,
        sample_treasury_constraints
    ):
        """Test deterministic payment instruction generation."""
        
        # Test with same inputs multiple times
        results = []
        for _ in range(5):
            instruction = finalizer.finalize_payment_instruction(
                negotiation_response=sample_negotiation_response,
                policy_constraints=sample_policy_constraints,
                trust_signal=sample_trust_signal,
                treasury_constraints=sample_treasury_constraints,
                trace_id="test_trace_123"
            )
            results.append(instruction)
        
        # All results should be identical (deterministic)
        first_result = results[0]
        for result in results[1:]:
            assert result.selected_rail == first_result.selected_rail
            assert result.selected_processor == first_result.selected_processor
            assert result.effective_cost == first_result.effective_cost
            assert result.confidence == first_result.confidence
            assert result.explanation == first_result.explanation

    def test_risk_adjusted_cost_calculation(
        self,
        finalizer,
        sample_negotiation_response,
        sample_trust_signal
    ):
        """Test risk-adjusted cost calculation with ML integration."""
        
        # Mock ML inference to return predictable risk score
        with patch.object(finalizer.ml_inference, 'predict_risk', return_value=0.3):
            instruction = finalizer.finalize_payment_instruction(
                negotiation_response=sample_negotiation_response,
                policy_constraints=[],
                trust_signal=sample_trust_signal,
                treasury_constraints=[],
                trace_id="test_trace_123"
            )
        
        # Risk-adjusted cost should be higher than base cost
        base_cost = sample_negotiation_response.rail_evaluations[0].cost
        assert instruction.effective_cost > base_cost
        
        # Should include ML risk score in metadata
        assert "ml_risk_score" in instruction.metadata
        assert instruction.metadata["ml_risk_score"] == 0.3

    def test_explanation_generation(
        self,
        finalizer,
        sample_negotiation_response,
        sample_policy_constraints,
        sample_trust_signal,
        sample_treasury_constraints
    ):
        """Test explanation generation for payment instruction."""
        
        instruction = finalizer.finalize_payment_instruction(
            negotiation_response=sample_negotiation_response,
            policy_constraints=sample_policy_constraints,
            trust_signal=sample_trust_signal,
            treasury_constraints=sample_treasury_constraints,
            trace_id="test_trace_123"
        )
        
        # Explanation should contain key information
        explanation = instruction.explanation
        assert "Card" in explanation
        assert "stripe" in explanation or "default" in explanation
        assert "Effective cost" in explanation
        assert "Settlement time" in explanation
        assert "Trust assessment" in explanation
        assert "policy constraints" in explanation.lower()
        assert "treasury constraints" in explanation.lower()

    def test_alternatives_generation(
        self,
        finalizer,
        sample_negotiation_response,
        sample_trust_signal
    ):
        """Test generation of top-k alternatives."""
        
        instruction = finalizer.finalize_payment_instruction(
            negotiation_response=sample_negotiation_response,
            policy_constraints=[],
            trust_signal=sample_trust_signal,
            treasury_constraints=[],
            trace_id="test_trace_123"
        )
        
        # Should have alternatives (ACH should be the alternative to Card)
        assert len(instruction.alternatives) > 0
        
        # Alternative should have required fields
        alt = instruction.alternatives[0]
        assert "rank" in alt
        assert "rail_type" in alt
        assert "score" in alt
        assert "cost" in alt
        assert "settlement_time_hours" in alt
        assert "confidence" in alt
        assert "explanation" in alt
        assert "why_not_selected" in alt

    def test_counterfactual_analysis(
        self,
        finalizer,
        sample_negotiation_response,
        sample_trust_signal
    ):
        """Test counterfactual analysis generation."""
        
        with patch.object(finalizer, '_generate_counterfactual_analysis') as mock_counterfactual:
            mock_analysis = CounterfactualAnalysis(
                trace_id="test_trace_123",
                original_instruction=PaymentInstruction(
                    instruction_id="test_instruction",
                    trace_id="test_trace_123",
                    selected_rail="Card",
                    selected_processor="stripe",
                    selected_instrument="visa_card",
                    amount=100.0,
                    currency="USD",
                    effective_cost=2.75,
                    settlement_time_hours=24,
                    confidence=0.85,
                    explanation="Test explanation",
                    alternatives=[],
                    constraints_applied=[],
                    metadata={}
                ),
                alternatives=[],
                scenario_differences=[],
                sensitivity_analysis={}
            )
            mock_counterfactual.return_value = mock_analysis
            
            instruction = finalizer.finalize_payment_instruction(
                negotiation_response=sample_negotiation_response,
                policy_constraints=[],
                trust_signal=sample_trust_signal,
                treasury_constraints=[],
                trace_id="test_trace_123"
            )
        
        # Should have called counterfactual analysis
        assert mock_counterfactual.called

    def test_constraints_formatting(
        self,
        finalizer,
        sample_negotiation_response,
        sample_policy_constraints,
        sample_trust_signal,
        sample_treasury_constraints
    ):
        """Test constraints formatting in payment instruction."""
        
        instruction = finalizer.finalize_payment_instruction(
            negotiation_response=sample_negotiation_response,
            policy_constraints=sample_policy_constraints,
            trust_signal=sample_trust_signal,
            treasury_constraints=sample_treasury_constraints,
            trace_id="test_trace_123"
        )
        
        constraints = instruction.constraints_applied
        
        # Should have policy, trust, and treasury constraints
        constraint_types = [c["type"] for c in constraints]
        assert "policy" in constraint_types
        assert "trust" in constraint_types
        assert "treasury" in constraint_types
        
        # Each constraint should have required fields
        for constraint in constraints:
            assert "type" in constraint
            assert "name" in constraint
            assert "description" in constraint

    def test_golden_fixture_consistency(self, finalizer):
        """Test consistency with golden fixture data."""
        
        # Load golden fixture data
        fixture_dir = Path(__file__).parent / "fixtures" / "payment_instruction"
        
        if not fixture_dir.exists():
            pytest.skip("Golden fixtures not available")
        
        # Test with golden fixture inputs
        golden_input = fixture_dir / "input.json"
        golden_output = fixture_dir / "expected_output.json"
        
        if golden_input.exists() and golden_output.exists():
            with open(golden_input) as f:
                input_data = json.load(f)
            
            with open(golden_output) as f:
                expected_output = json.load(f)
            
            # Create objects from input data
            negotiation_response = NegotiationRequest(**input_data["negotiation_response"])
            policy_constraints = [PolicyConstraint(**c) for c in input_data.get("policy_constraints", [])]
            trust_signal = TrustSignal(**input_data["trust_signal"])
            treasury_constraints = [TreasuryConstraint(**c) for c in input_data.get("treasury_constraints", [])]
            
            # Generate instruction
            instruction = finalizer.finalize_payment_instruction(
                negotiation_response=negotiation_response,
                policy_constraints=policy_constraints,
                trust_signal=trust_signal,
                treasury_constraints=treasury_constraints,
                trace_id=input_data["trace_id"]
            )
            
            # Compare with expected output (excluding dynamic fields)
            instruction_dict = instruction.dict()
            for key in ["instruction_id", "trace_id", "metadata"]:
                if key in instruction_dict:
                    del instruction_dict[key]
            
            # Check key fields match
            assert instruction_dict["selected_rail"] == expected_output["selected_rail"]
            assert instruction_dict["selected_processor"] == expected_output["selected_processor"]
            assert abs(instruction_dict["effective_cost"] - expected_output["effective_cost"]) < 0.01
            assert instruction_dict["settlement_time_hours"] == expected_output["settlement_time_hours"]

    def test_error_handling_missing_optimal_rail(self, finalizer, sample_trust_signal):
        """Test error handling when optimal rail is missing from evaluations."""
        
        # Create negotiation response with mismatched optimal rail
        rail_evaluations = [
            RailEvaluation(
                rail_type="Card",
                score=0.85,
                cost=2.50,
                settlement_time_hours=24,
                confidence=0.9,
                risk_adjusted_cost=2.75,
                factors={},
                explanation="Card rail evaluation"
            )
        ]
        
        negotiation_response = NegotiationResponse(
            optimal_rail="ACH",  # Not in rail_evaluations
            rail_evaluations=rail_evaluations,
            explanation="Test",
            confidence=0.85,
            trace_id="test_trace_123",
            negotiation_metadata={}
        )
        
        with pytest.raises(ValueError, match="No evaluation found for optimal rail"):
            finalizer.finalize_payment_instruction(
                negotiation_response=negotiation_response,
                policy_constraints=[],
                trust_signal=sample_trust_signal,
                treasury_constraints=[],
                trace_id="test_trace_123"
            )

    def test_ml_fallback_behavior(self, finalizer, sample_negotiation_response, sample_trust_signal):
        """Test ML inference fallback behavior."""
        
        # Mock ML inference to raise exception
        with patch.object(finalizer.ml_inference, 'predict_risk', side_effect=Exception("ML model error")):
            instruction = finalizer.finalize_payment_instruction(
                negotiation_response=sample_negotiation_response,
                policy_constraints=[],
                trust_signal=sample_trust_signal,
                treasury_constraints=[],
                trace_id="test_trace_123"
            )
        
        # Should still generate instruction with fallback risk score
        assert instruction is not None
        assert "ml_risk_score" in instruction.metadata
        # Fallback should be 1.0 - trust_score = 1.0 - 0.8 = 0.2
        assert instruction.metadata["ml_risk_score"] == 0.2

    def test_processor_selection_defaults(self, finalizer, sample_negotiation_response, sample_trust_signal):
        """Test default processor selection when no auction results provided."""
        
        instruction = finalizer.finalize_payment_instruction(
            negotiation_response=sample_negotiation_response,
            policy_constraints=[],
            trust_signal=sample_trust_signal,
            treasury_constraints=[],
            processor_auction_results=None,
            trace_id="test_trace_123"
        )
        
        # Should use default processor for Card rail
        assert instruction.selected_processor == "stripe"
        assert instruction.selected_instrument == "visa_card"

    def test_processor_selection_with_auction(self, finalizer, sample_negotiation_response, sample_trust_signal):
        """Test processor selection with auction results."""
        
        auction_results = {
            "winning_processor": {
                "processor_id": "custom_processor",
                "instrument": "custom_instrument",
                "cost": 1.50
            }
        }
        
        instruction = finalizer.finalize_payment_instruction(
            negotiation_response=sample_negotiation_response,
            policy_constraints=[],
            trust_signal=sample_trust_signal,
            treasury_constraints=[],
            processor_auction_results=auction_results,
            trace_id="test_trace_123"
        )
        
        # Should use auction results
        assert instruction.selected_processor == "custom_processor"
        assert instruction.selected_instrument == "custom_instrument"


class TestPaymentInstructionModels:
    """Test the payment instruction models."""

    def test_payment_instruction_model_validation(self):
        """Test PaymentInstruction model validation."""
        
        instruction = PaymentInstruction(
            instruction_id="test_instruction_123",
            trace_id="test_trace_123",
            selected_rail="Card",
            selected_processor="stripe",
            selected_instrument="visa_card",
            amount=100.0,
            currency="USD",
            effective_cost=2.75,
            settlement_time_hours=24,
            confidence=0.85,
            explanation="Test explanation",
            alternatives=[],
            constraints_applied=[],
            metadata={"test": "data"}
        )
        
        # Should create successfully
        assert instruction.instruction_id == "test_instruction_123"
        assert instruction.selected_rail == "Card"
        assert instruction.confidence == 0.85

    def test_negotiation_request_model_validation(self):
        """Test NegotiationRequest model validation."""
        
        request = NegotiationRequest(
            amount=100.0,
            currency="USD",
            merchant_id="merchant_123",
            customer_context={"customer_id": "cust_123"},
            available_rails=["Card", "ACH"],
            preferences={"prefer_fast": True},
            trace_id="test_trace_123"
        )
        
        assert request.amount == 100.0
        assert request.currency == "USD"
        assert "Card" in request.available_rails

    def test_rail_evaluation_model_validation(self):
        """Test RailEvaluation model validation."""
        
        evaluation = RailEvaluation(
            rail_type="Card",
            score=0.85,
            cost=2.50,
            settlement_time_hours=24,
            confidence=0.9,
            risk_adjusted_cost=2.75,
            factors={"cost": 0.3, "speed": 0.4},
            explanation="Good balance of cost and speed"
        )
        
        assert evaluation.rail_type == "Card"
        assert evaluation.score == 0.85
        assert evaluation.cost == 2.50

    def test_constraint_models_validation(self):
        """Test constraint models validation."""
        
        policy_constraint = PolicyConstraint(
            policy_type="max_cost",
            constraint_value=5.0,
            weight=0.8,
            description="Maximum cost constraint"
        )
        
        trust_signal = TrustSignal(
            trust_score=0.8,
            risk_level="low",
            signals=[{"type": "device", "score": 0.9}],
            confidence=0.85
        )
        
        treasury_constraint = TreasuryConstraint(
            constraint_type="balance_check",
            status="passed",
            available_balance=1000.0,
            constraint_value=100.0
        )
        
        assert policy_constraint.policy_type == "max_cost"
        assert trust_signal.trust_score == 0.8
        assert treasury_constraint.status == "passed"


@pytest.fixture
def golden_fixtures():
    """Create golden fixture data for testing."""
    fixture_dir = Path(__file__).parent / "fixtures" / "payment_instruction"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    
    # Create input fixture
    input_data = {
        "negotiation_response": {
            "amount": 100.0,
            "currency": "USD",
            "merchant_id": "merchant_123",
            "customer_context": {"customer_id": "cust_123"},
            "available_rails": ["Card", "ACH"],
            "preferences": {"prefer_fast": True},
            "trace_id": "golden_trace_123"
        },
        "policy_constraints": [
            {
                "policy_type": "max_cost",
                "constraint_value": 5.0,
                "weight": 0.8,
                "description": "Maximum cost constraint"
            }
        ],
        "trust_signal": {
            "trust_score": 0.8,
            "risk_level": "low",
            "signals": [{"type": "device", "score": 0.9}],
            "confidence": 0.85
        },
        "treasury_constraints": [
            {
                "constraint_type": "balance_check",
                "status": "passed",
                "available_balance": 1000.0,
                "constraint_value": 100.0
            }
        ],
        "trace_id": "golden_trace_123"
    }
    
    with open(fixture_dir / "input.json", "w") as f:
        json.dump(input_data, f, indent=2)
    
    # Create expected output fixture (simplified)
    expected_output = {
        "selected_rail": "Card",
        "selected_processor": "stripe",
        "selected_instrument": "visa_card",
        "amount": 100.0,
        "currency": "USD",
        "effective_cost": 2.75,
        "settlement_time_hours": 24,
        "confidence": 0.85
    }
    
    with open(fixture_dir / "expected_output.json", "w") as f:
        json.dump(expected_output, f, indent=2)
    
    return fixture_dir








