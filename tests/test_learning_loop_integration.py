"""
Integration tests for Orca Learning Loop Phase 9.

Tests counterfactuals, reward functions, epsilon-greedy bandit,
and explainability diffs with comprehensive scenarios.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

from src.orca_core.learning_loop import (
    get_learning_loop,
    RewardFunction,
    CounterfactualGenerator,
    EpsilonGreedyBandit
)
from src.orca_core.explainability_diffs import get_explainability_diff_analyzer
from src.orca_core.models import (
    PaymentInstruction, NegotiationResponse, PolicyConstraint,
    TrustSignal, TreasuryConstraint, CounterfactualAnalysis
)


class TestLearningLoopIntegration:
    """Integration tests for the complete learning loop system."""
    
    @pytest.fixture
    def learning_loop(self):
        """Get learning loop orchestrator instance."""
        return get_learning_loop()
    
    @pytest.fixture
    def reward_function(self):
        """Get reward function instance."""
        return RewardFunction()
    
    @pytest.fixture
    def counterfactual_generator(self):
        """Get counterfactual generator instance."""
        return CounterfactualGenerator()
    
    @pytest.fixture
    def epsilon_greedy_bandit(self):
        """Get epsilon-greedy bandit instance."""
        return EpsilonGreedyBandit(epsilon=0.1, min_samples=5)
    
    @pytest.fixture
    def explainability_analyzer(self):
        """Get explainability diff analyzer instance."""
        return get_explainability_diff_analyzer()
    
    @pytest.fixture
    def sample_payment_instruction(self):
        """Create sample payment instruction."""
        return PaymentInstruction(
            instruction_id="test_instruction_001",
            trace_id="test_trace_001",
            selected_rail="ACH",
            selected_processor="carat",
            selected_instrument="bank_transfer",
            amount=1000.0,
            currency="USD",
            effective_cost=15.0,
            settlement_time_hours=24,
            confidence=0.95,
            explanation="Selected ACH rail for optimal cost efficiency",
            alternatives=[],
            constraints_applied=[],
            metadata={
                "risk_score": 0.3,
                "merchant_id": "merchant_001"
            }
        )
    
    @pytest.fixture
    def sample_outcome_data(self):
        """Create sample outcome data."""
        return {
            "actual_cost": 14.5,
            "settlement_time_hours": 22,
            "approval_status": "approved",
            "customer_rating": 0.9,
            "risk_events": 0,
            "processor_fee": 14.5
        }
    
    @pytest.fixture
    def sample_alternatives(self):
        """Create sample alternatives for counterfactual analysis."""
        return [
            {
                "id": "alt_001",
                "rail_type": "Card",
                "instrument_type": "credit_card",
                "processor_id": "stripe",
                "cost_bps": 200.0,
                "settlement_days": 2,
                "risk_score": 0.4,
                "score": 0.75
            },
            {
                "id": "alt_002",
                "rail_type": "RTP",
                "instrument_type": "bank_transfer",
                "processor_id": "carat",
                "cost_bps": 18.0,
                "settlement_days": 0,
                "risk_score": 0.3,
                "score": 0.82
            }
        ]
    
    def test_reward_function_calculation(self, reward_function, sample_payment_instruction, sample_outcome_data):
        """Test reward function calculation with various scenarios."""
        # Test with good outcome
        reward_data = reward_function.calculate_reward(
            sample_payment_instruction,
            sample_outcome_data,
            baseline_performance={
                "avg_cost": 25.0,
                "avg_settlement_time": 36.0,
                "avg_approval_rate": 0.95,
                "avg_customer_rating": 0.8,
                "avg_risk_events": 0.1
            }
        )
        
        assert "total_reward" in reward_data
        assert "components" in reward_data
        assert reward_data["total_reward"] > 0.0
        assert reward_data["components"]["cost_efficiency"] > 0.0
        assert reward_data["components"]["approval_rate"] == 1.0  # Approved
        assert reward_data["components"]["customer_satisfaction"] == 0.9
        
        # Test with poor outcome
        poor_outcome = sample_outcome_data.copy()
        poor_outcome.update({
            "actual_cost": 50.0,
            "approval_status": "declined",
            "customer_rating": 0.3,
            "risk_events": 2
        })
        
        poor_reward_data = reward_function.calculate_reward(
            sample_payment_instruction,
            poor_outcome
        )
        
        assert poor_reward_data["total_reward"] < reward_data["total_reward"]
        assert poor_reward_data["components"]["approval_rate"] == 0.0  # Declined
        assert poor_reward_data["components"]["customer_satisfaction"] == 0.3
    
    def test_counterfactual_generation(self, counterfactual_generator, sample_payment_instruction, sample_alternatives):
        """Test counterfactual analysis generation."""
        counterfactual = counterfactual_generator.generate_counterfactuals(
            sample_payment_instruction,
            sample_alternatives,
            max_alternatives=2
        )
        
        assert isinstance(counterfactual, CounterfactualAnalysis)
        assert counterfactual.trace_id == sample_payment_instruction.trace_id
        assert len(counterfactual.alternatives) <= 2
        assert len(counterfactual.scenario_differences) > 0
        assert "cost_sensitivity" in counterfactual.sensitivity_analysis
        assert "speed_sensitivity" in counterfactual.sensitivity_analysis
        assert "risk_sensitivity" in counterfactual.sensitivity_analysis
        
        # Verify scenario differences are calculated
        for diff in counterfactual.scenario_differences:
            assert "cost_difference" in diff
            assert "settlement_time_difference" in diff
            assert "risk_difference" in diff
    
    def test_epsilon_greedy_bandit_selection(self, epsilon_greedy_bandit, sample_alternatives):
        """Test epsilon-greedy bandit action selection."""
        # Test exploration vs exploitation
        selected_actions = []
        selection_metadatas = []
        
        for _ in range(10):
            action, metadata = epsilon_greedy_bandit.select_action(
                sample_alternatives, shadow_mode=True
            )
            selected_actions.append(action)
            selection_metadatas.append(metadata)
        
        # Should have selected actions
        assert len(selected_actions) == 10
        assert all(action in sample_alternatives for action in selected_actions)
        
        # Should have metadata
        assert all("selection_strategy" in metadata for metadata in selection_metadatas)
        assert all("shadow_mode" in metadata for metadata in selection_metadatas)
        
        # Test action reward update
        action_to_update = sample_alternatives[0]
        epsilon_greedy_bandit.update_action_reward(action_to_update, 0.8)
        
        stats = epsilon_greedy_bandit.get_statistics()
        assert action_to_update["rail_type"] + "_" + action_to_update["instrument_type"] + "_" + action_to_update["processor_id"] in stats["action_values"]
    
    def test_learning_loop_orchestration(self, learning_loop, sample_payment_instruction, sample_alternatives):
        """Test complete learning loop orchestration."""
        # Test payment processing with learning
        learning_result = learning_loop.process_payment_with_learning(
            sample_payment_instruction,
            sample_alternatives,
            shadow_mode=True
        )
        
        assert "trace_id" in learning_result
        assert "counterfactuals" in learning_result
        assert "shadow_mode" in learning_result
        assert learning_result["shadow_mode"] == True
        
        # Test outcome update
        outcome_data = {
            "actual_cost": 14.5,
            "settlement_time_hours": 22,
            "approval_status": "approved",
            "customer_rating": 0.9,
            "risk_events": 0
        }
        
        update_result = learning_loop.update_with_outcome(
            sample_payment_instruction.trace_id,
            outcome_data,
            sample_payment_instruction
        )
        
        assert "reward_data" in update_result
        assert "outcome_data" in update_result
        assert update_result["reward_data"]["total_reward"] > 0.0
    
    def test_explainability_diff_analysis(self, explainability_analyzer, sample_payment_instruction):
        """Test explainability difference analysis."""
        # Create a previous instruction for comparison
        previous_instruction = PaymentInstruction(
            instruction_id="test_instruction_000",
            trace_id="test_trace_000",
            selected_rail="Card",
            selected_processor="stripe",
            selected_instrument="credit_card",
            amount=1000.0,
            currency="USD",
            effective_cost=25.0,
            settlement_time_hours=48,
            confidence=0.9,
            explanation="Selected Card rail for global reach",
            alternatives=[],
            constraints_applied=[],
            metadata={"risk_score": 0.4}
        )
        
        # Analyze explanation diff
        diff_analysis = explainability_analyzer.analyze_explanation_diff(
            sample_payment_instruction,
            previous_instruction=previous_instruction
        )
        
        assert "trace_id" in diff_analysis
        assert "current_explanation" in diff_analysis
        assert "previous_comparison" in diff_analysis
        assert "decision_factors" in diff_analysis
        assert "explanation_confidence" in diff_analysis
        
        # Verify previous comparison
        prev_comp = diff_analysis["previous_comparison"]
        assert prev_comp["rail_changed"] == True  # ACH vs Card
        assert prev_comp["instrument_changed"] == True  # bank_transfer vs credit_card
        assert prev_comp["cost_change"] < 0  # 15.0 - 25.0 = -10.0
        assert prev_comp["settlement_time_change"] < 0  # 24 - 48 = -24
        
        # Verify decision factors
        decision_factors = diff_analysis["decision_factors"]
        assert "primary_factors" in decision_factors
        assert "constraint_impacts" in decision_factors
        assert "risk_assessment" in decision_factors
        assert "cost_optimization" in decision_factors
    
    def test_learning_loop_with_fixtures(self, learning_loop):
        """Test learning loop with golden fixtures."""
        # Load reward function fixture
        reward_fixture_path = Path(__file__).parent / "fixtures" / "learning_loop" / "reward_function_example.json"
        with open(reward_fixture_path) as f:
            reward_fixture = json.load(f)
        
        # Create payment instruction from fixture
        payment_instruction = PaymentInstruction(**reward_fixture["payment_instruction"])
        
        # Test reward calculation
        reward_data = learning_loop.reward_function.calculate_reward(
            payment_instruction,
            reward_fixture["outcome_data"],
            reward_fixture["baseline_performance"]
        )
        
        # Verify reward components are within expected ranges
        expected_components = reward_fixture["expected_reward_components"]
        for component, expected_value in expected_components.items():
            assert abs(reward_data["components"][component] - expected_value) < 0.2
        
        # Verify total reward is reasonable
        expected_total = reward_fixture["expected_total_reward"]
        assert abs(reward_data["total_reward"] - expected_total) < 0.2
    
    def test_counterfactual_with_fixtures(self, counterfactual_generator):
        """Test counterfactual generation with golden fixtures."""
        # Load counterfactual fixture
        counterfactual_fixture_path = Path(__file__).parent / "fixtures" / "learning_loop" / "counterfactual_example.json"
        with open(counterfactual_fixture_path) as f:
            counterfactual_fixture = json.load(f)
        
        # Create payment instruction from fixture
        original_instruction = PaymentInstruction(**counterfactual_fixture["original_instruction"])
        available_alternatives = counterfactual_fixture["available_alternatives"]
        
        # Generate counterfactual
        counterfactual = counterfactual_generator.generate_counterfactuals(
            original_instruction,
            available_alternatives
        )
        
        # Verify counterfactual structure
        expected = counterfactual_fixture["expected_counterfactual"]
        assert counterfactual.trace_id == expected["trace_id"]
        assert len(counterfactual.alternatives) == expected["alternatives_count"]
        assert len(counterfactual.scenario_differences) == expected["scenario_differences_count"]
        
        for key in expected["sensitivity_analysis_keys"]:
            assert key in counterfactual.sensitivity_analysis
    
    def test_epsilon_greedy_with_fixtures(self, epsilon_greedy_bandit):
        """Test epsilon-greedy bandit with golden fixtures."""
        # Load epsilon-greedy fixture
        bandit_fixture_path = Path(__file__).parent / "fixtures" / "learning_loop" / "epsilon_greedy_example.json"
        with open(bandit_fixture_path) as f:
            bandit_fixture = json.load(f)
        
        available_actions = bandit_fixture["available_actions"]
        
        # Test action selection
        selected_action, selection_metadata = epsilon_greedy_bandit.select_action(
            available_actions, shadow_mode=True
        )
        
        # Verify selection metadata
        expected_metadata = bandit_fixture["expected_selection_metadata"]
        assert selection_metadata["shadow_mode"] == expected_metadata["shadow_mode"]
        assert selection_metadata["safe_actions_count"] == expected_metadata["safe_actions_count"]
        assert selection_metadata["total_actions_count"] == expected_metadata["total_actions_count"]
        assert selection_metadata["selection_strategy"] in ["exploration", "exploitation"]
        
        # Verify selected action is from available actions
        assert selected_action in available_actions
    
    def test_learning_loop_deterministic_behavior(self, learning_loop, sample_payment_instruction, sample_alternatives):
        """Test that learning loop produces deterministic results."""
        # Run the same scenario multiple times
        results = []
        for _ in range(3):
            result = learning_loop.process_payment_with_learning(
                sample_payment_instruction,
                sample_alternatives,
                shadow_mode=True
            )
            results.append(result)
        
        # Results should be identical (deterministic)
        assert all(r["trace_id"] == results[0]["trace_id"] for r in results)
        assert all(r["shadow_mode"] == results[0]["shadow_mode"] for r in results)
        
        # Counterfactuals should be identical
        for i in range(1, len(results)):
            assert results[i]["counterfactuals"]["trace_id"] == results[0]["counterfactuals"]["trace_id"]
            assert len(results[i]["counterfactuals"]["alternatives"]) == len(results[0]["counterfactuals"]["alternatives"])
    
    def test_learning_loop_error_handling(self, learning_loop):
        """Test learning loop error handling."""
        # Test with invalid payment instruction
        invalid_instruction = PaymentInstruction(
            instruction_id="invalid",
            trace_id="invalid",
            selected_rail="INVALID_RAIL",  # Invalid rail
            selected_processor="invalid",
            selected_instrument="invalid",
            amount=-100.0,  # Invalid amount
            currency="USD",
            effective_cost=0.0,
            settlement_time_hours=-1,  # Invalid time
            confidence=2.0,  # Invalid confidence
            explanation="",
            alternatives=[],
            constraints_applied=[],
            metadata={}
        )
        
        # Should handle gracefully
        result = learning_loop.process_payment_with_learning(
            invalid_instruction,
            [],
            shadow_mode=True
        )
        
        # Should return error information
        assert "error" in result or "trace_id" in result
        
        # Test with empty alternatives
        valid_instruction = PaymentInstruction(
            instruction_id="valid",
            trace_id="valid",
            selected_rail="ACH",
            selected_processor="carat",
            selected_instrument="bank_transfer",
            amount=100.0,
            currency="USD",
            effective_cost=15.0,
            settlement_time_hours=24,
            confidence=0.9,
            explanation="Valid instruction",
            alternatives=[],
            constraints_applied=[],
            metadata={}
        )
        
        result = learning_loop.process_payment_with_learning(
            valid_instruction,
            [],  # Empty alternatives
            shadow_mode=True
        )
        
        assert "trace_id" in result
        assert result["counterfactuals"]["alternatives"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








