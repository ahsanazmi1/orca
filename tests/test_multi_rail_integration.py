"""
Integration tests for multi-rail and multi-instrument functionality in Orca Phase 7.

Tests comprehensive multi-rail negotiation, evaluation, and selection
across ACH, RTP, FedNow, SEPA, and various payment instruments.
"""

import json
import pytest
from pathlib import Path

from src.orca_core.multi_rail_engine import (
    get_multi_rail_negotiation_engine,
    get_multi_rail_evaluator,
    get_capability_registry
)
from src.orca_core.models import (
    MultiRailNegotiationRequest,
    MultiRailNegotiationResponse,
    MultiRailEvaluation,
    RailType,
    InstrumentType
)


class TestMultiRailIntegration:
    """Integration tests for multi-rail functionality."""
    
    @pytest.fixture
    def negotiation_engine(self):
        """Get multi-rail negotiation engine."""
        return get_multi_rail_negotiation_engine()
    
    @pytest.fixture
    def evaluator(self):
        """Get multi-rail evaluator."""
        return get_multi_rail_evaluator()
    
    @pytest.fixture
    def capability_registry(self):
        """Get capability registry."""
        return get_capability_registry()
    
    @pytest.fixture
    def fednow_fixture(self):
        """Load FedNow test fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "multi_rail" / "fednow_example.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def sepa_fixture(self):
        """Load SEPA test fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "multi_rail" / "sepa_example.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def stablecoin_fixture(self):
        """Load stablecoin test fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "multi_rail" / "stablecoin_example.json"
        with open(fixture_path) as f:
            return json.load(f)
    
    def test_capability_registry_initialization(self, capability_registry):
        """Test that capability registry is properly initialized."""
        # Test rail capabilities
        assert "ACH" in capability_registry.rail_capabilities
        assert "RTP" in capability_registry.rail_capabilities
        assert "FedNow" in capability_registry.rail_capabilities
        assert "SEPA" in capability_registry.rail_capabilities
        assert "Wire" in capability_registry.rail_capabilities
        assert "Crypto" in capability_registry.rail_capabilities
        assert "Card" in capability_registry.rail_capabilities
        
        # Test instrument capabilities
        assert "credit_card" in capability_registry.instrument_capabilities
        assert "debit_card" in capability_registry.instrument_capabilities
        assert "prepaid_card" in capability_registry.instrument_capabilities
        assert "bank_transfer" in capability_registry.instrument_capabilities
        assert "stablecoin" in capability_registry.instrument_capabilities
        assert "digital_wallet" in capability_registry.instrument_capabilities
        assert "bnpl" in capability_registry.instrument_capabilities
        assert "cash" in capability_registry.instrument_capabilities
        
        # Test valid combinations
        valid_combinations = capability_registry.get_valid_combinations()
        assert len(valid_combinations) > 0
        
        # Verify specific combinations exist
        assert ("FedNow", "debit_card") in valid_combinations
        assert ("SEPA", "bank_transfer") in valid_combinations
        assert ("Crypto", "stablecoin") in valid_combinations
    
    def test_fednow_rail_evaluation(self, evaluator, fednow_fixture):
        """Test FedNow rail evaluation matches expected results."""
        # Create negotiation request from fixture
        request_data = fednow_fixture
        request = MultiRailNegotiationRequest(**{
            k: v for k, v in request_data.items() 
            if k not in ["expected_rail_capability", "expected_instrument_capability", "expected_evaluation"]
        })
        
        # Evaluate FedNow + debit_card combination
        evaluation = evaluator.evaluate_combination("FedNow", "debit_card", request)
        
        assert evaluation is not None
        assert evaluation.rail_type == "FedNow"
        assert evaluation.instrument_type == "debit_card"
        assert evaluation.is_real_time == True
        assert evaluation.is_cross_border == False
        assert evaluation.settlement_time_hours == 0  # Real-time
        
        # Verify scoring includes FedNow characteristics
        assert evaluation.speed_score > 0.9  # Real-time should have high speed score
        assert evaluation.availability_score > 0.8  # 24/7 availability
        assert evaluation.cost_score > 0.7  # Reasonable cost
        
        # Verify expected values match fixture
        expected = fednow_fixture["expected_evaluation"]
        assert abs(evaluation.total_score - expected["total_score"]) < 0.1
        assert abs(evaluation.effective_cost_bps - expected["effective_cost_bps"]) < 1.0
        assert evaluation.risk_level == expected["risk_level"]
        assert evaluation.compliance_status == expected["compliance_status"]
    
    def test_sepa_rail_evaluation(self, evaluator, sepa_fixture):
        """Test SEPA rail evaluation matches expected results."""
        # Create negotiation request from fixture
        request_data = sepa_fixture
        request = MultiRailNegotiationRequest(**{
            k: v for k, v in request_data.items() 
            if k not in ["expected_rail_capability", "expected_instrument_capability", "expected_evaluation"]
        })
        
        # Evaluate SEPA + bank_transfer combination
        evaluation = evaluator.evaluate_combination("SEPA", "bank_transfer", request)
        
        assert evaluation is not None
        assert evaluation.rail_type == "SEPA"
        assert evaluation.instrument_type == "bank_transfer"
        assert evaluation.is_real_time == False
        assert evaluation.is_cross_border == True
        assert evaluation.settlement_time_hours == 24
        
        # Verify scoring includes SEPA characteristics
        assert evaluation.cost_score > 0.9  # Very low cost
        assert evaluation.speed_score > 0.8  # Fast settlement
        assert evaluation.risk_score > 0.8  # Low risk
        
        # Verify expected values match fixture
        expected = sepa_fixture["expected_evaluation"]
        assert abs(evaluation.total_score - expected["total_score"]) < 0.1
        assert abs(evaluation.effective_cost_bps - expected["effective_cost_bps"]) < 1.0
        assert evaluation.risk_level == expected["risk_level"]
    
    def test_stablecoin_evaluation(self, evaluator, stablecoin_fixture):
        """Test stablecoin evaluation matches expected results."""
        # Create negotiation request from fixture
        request_data = stablecoin_fixture
        request = MultiRailNegotiationRequest(**{
            k: v for k, v in request_data.items() 
            if k not in ["expected_rail_capability", "expected_instrument_capability", "expected_evaluation"]
        })
        
        # Evaluate Crypto + stablecoin combination
        evaluation = evaluator.evaluate_combination("Crypto", "stablecoin", request)
        
        assert evaluation is not None
        assert evaluation.rail_type == "Crypto"
        assert evaluation.instrument_type == "stablecoin"
        assert evaluation.is_real_time == True
        assert evaluation.is_cross_border == True
        assert evaluation.settlement_time_hours == 1
        
        # Verify scoring includes stablecoin characteristics
        assert evaluation.cost_score > 0.95  # Very low cost
        assert evaluation.speed_score > 0.9  # Very fast
        assert evaluation.availability_score > 0.9  # 24/7
        
        # Verify expected values match fixture
        expected = stablecoin_fixture["expected_evaluation"]
        assert abs(evaluation.total_score - expected["total_score"]) < 0.1
        assert abs(evaluation.effective_cost_bps - expected["effective_cost_bps"]) < 1.0
        assert evaluation.risk_level == expected["risk_level"]
    
    def test_multi_rail_negotiation_fednow(self, negotiation_engine, fednow_fixture):
        """Test complete multi-rail negotiation with FedNow preference."""
        # Create negotiation request from fixture
        request_data = fednow_fixture
        request = MultiRailNegotiationRequest(**{
            k: v for k, v in request_data.items() 
            if k not in ["expected_rail_capability", "expected_instrument_capability", "expected_evaluation"]
        })
        
        # Run negotiation
        response = negotiation_engine.negotiate(request)
        
        assert isinstance(response, MultiRailNegotiationResponse)
        assert response.trace_id == request.trace_id
        assert response.total_combinations_evaluated > 0
        assert response.available_combinations > 0
        assert len(response.all_evaluations) > 0
        
        # Verify FedNow appears in candidate set
        fednow_evaluations = [e for e in response.all_evaluations if e.rail_type == "FedNow"]
        assert len(fednow_evaluations) > 0
        
        # Verify optimal combination is selected based on preferences
        optimal = response.optimal_combination
        assert optimal.rail_type in request.preferred_rails or optimal.rail_type == "FedNow"
        assert optimal.instrument_type in request.preferred_instruments or optimal.instrument_type == "debit_card"
        
        # Verify scoring includes all factors
        assert 0.0 <= optimal.total_score <= 1.0
        assert 0.0 <= optimal.cost_score <= 1.0
        assert 0.0 <= optimal.speed_score <= 1.0
        assert 0.0 <= optimal.risk_score <= 1.0
        assert 0.0 <= optimal.availability_score <= 1.0
        
        # Verify alternatives are provided
        assert len(response.top_alternatives) > 0
        assert response.confidence > 0.0
    
    def test_multi_rail_negotiation_sepa(self, negotiation_engine, sepa_fixture):
        """Test complete multi-rail negotiation with SEPA preference."""
        # Create negotiation request from fixture
        request_data = sepa_fixture
        request = MultiRailNegotiationRequest(**{
            k: v for k, v in request_data.items() 
            if k not in ["expected_rail_capability", "expected_instrument_capability", "expected_evaluation"]
        })
        
        # Run negotiation
        response = negotiation_engine.negotiate(request)
        
        assert isinstance(response, MultiRailNegotiationResponse)
        assert response.trace_id == request.trace_id
        
        # Verify SEPA appears in candidate set
        sepa_evaluations = [e for e in response.all_evaluations if e.rail_type == "SEPA"]
        assert len(sepa_evaluations) > 0
        
        # Verify cross-border capability is considered
        cross_border_evaluations = [e for e in response.all_evaluations if e.is_cross_border]
        assert len(cross_border_evaluations) > 0
        
        # Verify optimal combination meets cross-border requirement
        optimal = response.optimal_combination
        assert optimal.is_cross_border == True
    
    def test_multi_rail_negotiation_stablecoin(self, negotiation_engine, stablecoin_fixture):
        """Test complete multi-rail negotiation with stablecoin preference."""
        # Create negotiation request from fixture
        request_data = stablecoin_fixture
        request = MultiRailNegotiationRequest(**{
            k: v for k, v in request_data.items() 
            if k not in ["expected_rail_capability", "expected_instrument_capability", "expected_evaluation"]
        })
        
        # Run negotiation
        response = negotiation_engine.negotiate(request)
        
        assert isinstance(response, MultiRailNegotiationResponse)
        assert response.trace_id == request.trace_id
        
        # Verify Crypto/stablecoin appears in candidate set
        crypto_evaluations = [e for e in response.all_evaluations if e.rail_type == "Crypto"]
        assert len(crypto_evaluations) > 0
        
        stablecoin_evaluations = [e for e in response.all_evaluations if e.instrument_type == "stablecoin"]
        assert len(stablecoin_evaluations) > 0
        
        # Verify real-time requirement is met
        real_time_evaluations = [e for e in response.all_evaluations if e.is_real_time]
        assert len(real_time_evaluations) > 0
        
        # Verify optimal combination meets real-time requirement
        optimal = response.optimal_combination
        assert optimal.is_real_time == True
    
    def test_rail_constraints_filtering(self, negotiation_engine):
        """Test that rail constraints properly filter candidates."""
        # Create request with strict constraints
        request = MultiRailNegotiationRequest(
            trace_id="test_constraints_001",
            amount=1000.0,
            currency="USD",
            merchant_id="test_merchant",
            preferred_rails=["FedNow"],
            max_settlement_hours=1,
            max_cost_bps=25.0,
            require_real_time=True,
            cross_border=False
        )
        
        response = negotiation_engine.negotiate(request)
        
        # Verify all evaluations meet constraints
        for evaluation in response.all_evaluations:
            assert evaluation.settlement_time_hours <= request.max_settlement_hours
            assert evaluation.effective_cost_bps <= request.max_cost_bps
            assert evaluation.is_real_time == True  # Required
            assert evaluation.is_cross_border == False  # Required
    
    def test_instrument_constraints_filtering(self, negotiation_engine):
        """Test that instrument constraints properly filter candidates."""
        # Create request with instrument constraints
        request = MultiRailNegotiationRequest(
            trace_id="test_instrument_constraints_001",
            amount=5000.0,
            currency="USD",
            merchant_id="test_merchant",
            preferred_instruments=["stablecoin"],
            excluded_instruments=["cash", "bnpl"],
            max_amount=100000.0
        )
        
        response = negotiation_engine.negotiate(request)
        
        # Verify excluded instruments are not present
        for evaluation in response.all_evaluations:
            assert evaluation.instrument_type not in request.excluded_instruments
        
        # Verify stablecoin is prioritized if available
        stablecoin_evaluations = [e for e in response.all_evaluations if e.instrument_type == "stablecoin"]
        if stablecoin_evaluations:
            assert response.optimal_combination.instrument_type == "stablecoin"
    
    def test_multi_rail_scoring_consistency(self, evaluator):
        """Test that scoring is consistent and deterministic."""
        request = MultiRailNegotiationRequest(
            trace_id="test_scoring_001",
            amount=2000.0,
            currency="USD",
            merchant_id="test_merchant"
        )
        
        # Evaluate same combination multiple times
        evaluation1 = evaluator.evaluate_combination("FedNow", "debit_card", request)
        evaluation2 = evaluator.evaluate_combination("FedNow", "debit_card", request)
        
        assert evaluation1 is not None
        assert evaluation2 is not None
        
        # Scores should be identical (deterministic)
        assert abs(evaluation1.total_score - evaluation2.total_score) < 0.001
        assert abs(evaluation1.cost_score - evaluation2.cost_score) < 0.001
        assert abs(evaluation1.speed_score - evaluation2.speed_score) < 0.001
        assert abs(evaluation1.risk_score - evaluation2.risk_score) < 0.001
        assert abs(evaluation1.availability_score - evaluation2.availability_score) < 0.001
    
    def test_rail_instrument_combination_coverage(self, capability_registry, evaluator):
        """Test that all valid rail-instrument combinations are evaluated."""
        request = MultiRailNegotiationRequest(
            trace_id="test_coverage_001",
            amount=1000.0,
            currency="USD",
            merchant_id="test_merchant"
        )
        
        # Get all valid combinations
        valid_combinations = capability_registry.get_valid_combinations()
        
        # Evaluate each combination
        evaluated_combinations = []
        for rail_type, instrument_type in valid_combinations:
            evaluation = evaluator.evaluate_combination(rail_type, instrument_type, request)
            if evaluation:
                evaluated_combinations.append((rail_type, instrument_type))
        
        # Verify high coverage
        coverage_ratio = len(evaluated_combinations) / len(valid_combinations)
        assert coverage_ratio > 0.8, f"Only {coverage_ratio:.1%} of combinations were evaluated"
        
        # Verify specific important combinations are covered
        important_combinations = [
            ("FedNow", "debit_card"),
            ("SEPA", "bank_transfer"),
            ("Crypto", "stablecoin"),
            ("Card", "credit_card"),
            ("ACH", "bank_transfer")
        ]
        
        for rail_type, instrument_type in important_combinations:
            assert (rail_type, instrument_type) in evaluated_combinations, \
                f"Important combination {rail_type}/{instrument_type} not evaluated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








