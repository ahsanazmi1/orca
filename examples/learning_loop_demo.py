#!/usr/bin/env python3
"""
Learning Loop Demo for Orca Phase 9

Demonstrates the complete learning loop functionality including:
- Counterfactuals and reward functions
- Shadow mode and epsilon-greedy bandit
- Explainability diffs
- Integration with Weave for outcomes tracking
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from orca_core.learning_loop import (
    get_learning_loop,
    RewardFunction,
    CounterfactualGenerator,
    EpsilonGreedyBandit
)
from orca_core.explainability_diffs import get_explainability_diff_analyzer
from orca_core.models import (
    PaymentInstruction, NegotiationResponse, PolicyConstraint,
    TrustSignal, TreasuryConstraint, RailEvaluation
)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


def demo_reward_function():
    """Demonstrate reward function calculation."""
    print_header("Reward Function Demo")
    
    reward_function = RewardFunction()
    
    # Create sample payment instruction
    payment_instruction = PaymentInstruction(
        instruction_id="demo_instruction_001",
        trace_id="demo_trace_001",
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
        metadata={"risk_score": 0.3}
    )
    
    # Create sample outcome data
    outcome_data = {
        "actual_cost": 14.5,
        "settlement_time_hours": 22,
        "approval_status": "approved",
        "customer_rating": 0.9,
        "risk_events": 0
    }
    
    baseline_performance = {
        "avg_cost": 25.0,
        "avg_settlement_time": 36.0,
        "avg_approval_rate": 0.95,
        "avg_customer_rating": 0.8,
        "avg_risk_events": 0.1
    }
    
    print_section("Calculating Reward for Good Outcome")
    reward_data = reward_function.calculate_reward(
        payment_instruction,
        outcome_data,
        baseline_performance
    )
    
    print(f"Total Reward: {reward_data['total_reward']:.3f}")
    print("\nComponent Breakdown:")
    for component, value in reward_data['components'].items():
        print(f"  {component}: {value:.3f}")
    
    # Demonstrate poor outcome
    print_section("Calculating Reward for Poor Outcome")
    poor_outcome = outcome_data.copy()
    poor_outcome.update({
        "actual_cost": 50.0,
        "approval_status": "declined",
        "customer_rating": 0.3,
        "risk_events": 2
    })
    
    poor_reward = reward_function.calculate_reward(
        payment_instruction,
        poor_outcome,
        baseline_performance
    )
    
    print(f"Total Reward: {poor_reward['total_reward']:.3f}")
    print(f"Reward Difference: {reward_data['total_reward'] - poor_reward['total_reward']:.3f}")


def demo_counterfactual_generation():
    """Demonstrate counterfactual analysis."""
    print_header("Counterfactual Generation Demo")
    
    counterfactual_generator = CounterfactualGenerator()
    
    # Create original payment instruction
    original_instruction = PaymentInstruction(
        instruction_id="demo_instruction_002",
        trace_id="demo_trace_002",
        selected_rail="Card",
        selected_processor="stripe",
        selected_instrument="credit_card",
        amount=500.0,
        currency="USD",
        effective_cost=20.0,
        settlement_time_hours=48,
        confidence=0.9,
        explanation="Selected Card rail for global reach and customer convenience",
        alternatives=[],
        constraints_applied=[],
        metadata={"risk_score": 0.4}
    )
    
    # Create available alternatives
    alternatives = [
        {
            "id": "alt_001",
            "rail_type": "ACH",
            "instrument_type": "bank_transfer",
            "processor_id": "carat",
            "cost_bps": 15.0,
            "settlement_days": 1,
            "risk_score": 0.2,
            "score": 0.85,
            "expected_reward": 0.8
        },
        {
            "id": "alt_002",
            "rail_type": "RTP",
            "instrument_type": "bank_transfer",
            "processor_id": "carat",
            "cost_bps": 18.0,
            "settlement_days": 0,
            "risk_score": 0.3,
            "score": 0.82,
            "expected_reward": 0.75
        },
        {
            "id": "alt_003",
            "rail_type": "Card",
            "instrument_type": "debit_card",
            "processor_id": "adyen",
            "cost_bps": 22.0,
            "settlement_days": 1,
            "risk_score": 0.35,
            "score": 0.78,
            "expected_reward": 0.7
        }
    ]
    
    print_section("Generating Counterfactuals")
    counterfactual = counterfactual_generator.generate_counterfactuals(
        original_instruction,
        alternatives,
        max_alternatives=3
    )
    
    print(f"Original Decision: {original_instruction.selected_rail} with {original_instruction.selected_instrument}")
    print(f"Cost: ${original_instruction.effective_cost:.2f}, Settlement: {original_instruction.settlement_time_hours}h")
    
    print(f"\nGenerated {len(counterfactual.alternatives)} alternatives:")
    for i, alt in enumerate(counterfactual.alternatives, 1):
        print(f"  {i}. {alt['rail_type']} with {alt['instrument_type']} (Score: {alt['score']:.2f})")
    
    print(f"\nScenario Differences:")
    for i, diff in enumerate(counterfactual.scenario_differences, 1):
        print(f"  Alternative {i}:")
        print(f"    Cost Difference: ${diff['cost_difference']:.2f}")
        print(f"    Settlement Time Difference: {diff['settlement_time_difference']:.1f}h")
        print(f"    Risk Difference: {diff['risk_difference']:.2f}")
    
    print(f"\nSensitivity Analysis:")
    for metric, analysis in counterfactual.sensitivity_analysis.items():
        if isinstance(analysis, dict) and 'variance' in analysis:
            print(f"  {metric}: Variance = {analysis['variance']:.4f}")


def demo_epsilon_greedy_bandit():
    """Demonstrate epsilon-greedy bandit selection."""
    print_header("Epsilon-Greedy Bandit Demo")
    
    bandit = EpsilonGreedyBandit(epsilon=0.2, min_samples=5)
    
    # Create available actions
    available_actions = [
        {
            "rail_type": "ACH",
            "instrument_type": "bank_transfer",
            "processor_id": "carat",
            "cost_bps": 15.0,
            "settlement_days": 1,
            "risk_score": 0.2,
            "approval_rate": 0.95,
            "baseline_cost_bps": 20.0
        },
        {
            "rail_type": "Card",
            "instrument_type": "credit_card",
            "processor_id": "stripe",
            "cost_bps": 200.0,
            "settlement_days": 2,
            "risk_score": 0.4,
            "approval_rate": 0.92,
            "baseline_cost_bps": 220.0
        },
        {
            "rail_type": "RTP",
            "instrument_type": "bank_transfer",
            "processor_id": "carat",
            "cost_bps": 18.0,
            "settlement_days": 0,
            "risk_score": 0.3,
            "approval_rate": 0.98,
            "baseline_cost_bps": 25.0
        }
    ]
    
    print_section("Action Selection (Shadow Mode)")
    print(f"Epsilon (exploration rate): {bandit.epsilon}")
    print(f"Available actions: {len(available_actions)}")
    
    # Demonstrate multiple selections
    selections = []
    for i in range(5):
        selected_action, metadata = bandit.select_action(available_actions, shadow_mode=True)
        selections.append((selected_action, metadata))
        
        print(f"\nSelection {i+1}:")
        print(f"  Strategy: {metadata['selection_strategy']}")
        print(f"  Selected: {selected_action['rail_type']} with {selected_action['instrument_type']}")
        print(f"  Cost: {selected_action['cost_bps']} bps")
        print(f"  Settlement: {selected_action['settlement_days']} days")
    
    print_section("Action Reward Updates")
    # Simulate reward updates
    for i, (action, metadata) in enumerate(selections):
        # Simulate rewards based on action quality
        if action['rail_type'] == 'ACH':
            reward = 0.9  # High reward for ACH
        elif action['rail_type'] == 'RTP':
            reward = 0.8  # Medium-high reward for RTP
        else:
            reward = 0.7  # Medium reward for Card
        
        bandit.update_action_reward(action, reward)
        print(f"Updated {action['rail_type']} reward: {reward:.2f}")
    
    print_section("Bandit Statistics")
    stats = bandit.get_statistics()
    print(f"Total actions tracked: {stats['total_actions']}")
    print("Action values:")
    for action_id, value in stats['action_values'].items():
        print(f"  {action_id}: {value:.3f}")


def demo_explainability_diffs():
    """Demonstrate explainability difference analysis."""
    print_header("Explainability Diffs Demo")
    
    analyzer = get_explainability_diff_analyzer()
    
    # Create current instruction
    current_instruction = PaymentInstruction(
        instruction_id="demo_instruction_003",
        trace_id="demo_trace_003",
        selected_rail="ACH",
        selected_processor="carat",
        selected_instrument="bank_transfer",
        amount=1000.0,
        currency="USD",
        effective_cost=15.0,
        settlement_time_hours=24,
        confidence=0.95,
        explanation="Selected ACH rail for optimal cost efficiency and reliable settlement. The decision prioritizes low processing costs while maintaining high approval rates for this merchant segment.",
        alternatives=[],
        constraints_applied=[
            {"type": "cost_constraint", "severity": "high", "description": "Cost must be under $20"},
            {"type": "settlement_constraint", "severity": "medium", "description": "Settlement within 48 hours"}
        ],
        metadata={"risk_score": 0.3, "merchant_id": "merchant_001"}
    )
    
    # Create previous instruction for comparison
    previous_instruction = PaymentInstruction(
        instruction_id="demo_instruction_002",
        trace_id="demo_trace_002",
        selected_rail="Card",
        selected_processor="stripe",
        selected_instrument="credit_card",
        amount=1000.0,
        currency="USD",
        effective_cost=25.0,
        settlement_time_hours=48,
        confidence=0.9,
        explanation="Selected Card rail for global reach and customer convenience. This choice ensures broad acceptance while providing fast settlement for international transactions.",
        alternatives=[],
        constraints_applied=[],
        metadata={"risk_score": 0.4}
    )
    
    print_section("Analyzing Explanation Differences")
    diff_analysis = analyzer.analyze_explanation_diff(
        current_instruction,
        previous_instruction=previous_instruction
    )
    
    print(f"Current Decision: {current_instruction.selected_rail} (${current_instruction.effective_cost:.2f})")
    print(f"Previous Decision: {previous_instruction.selected_rail} (${previous_instruction.effective_cost:.2f})")
    
    print(f"\nPrevious Comparison:")
    prev_comp = diff_analysis["previous_comparison"]
    print(f"  Rail Changed: {prev_comp['rail_changed']}")
    print(f"  Instrument Changed: {prev_comp['instrument_changed']}")
    print(f"  Cost Change: ${prev_comp['cost_change']:.2f}")
    print(f"  Settlement Time Change: {prev_comp['settlement_time_change']:.1f} hours")
    print(f"  Confidence Change: {prev_comp['confidence_change']:.2f}")
    print(f"  Explanation Similarity: {prev_comp['explanation_similarity']:.3f}")
    
    print(f"\nDecision Factors:")
    factors = diff_analysis["decision_factors"]
    print(f"  Primary Factors: {', '.join(factors['primary_factors'])}")
    print(f"  Total Constraints: {factors['constraint_impacts']['total_constraints']}")
    print(f"  Constraint Impact Score: {factors['constraint_impacts']['constraint_impact_score']:.3f}")
    print(f"  Risk Score: {factors['risk_assessment']['risk_score']:.2f}")
    print(f"  Cost Optimization Score: {factors['cost_optimization']['cost_optimization_score']:.3f}")
    
    print(f"\nExplanation Confidence: {diff_analysis['explanation_confidence']:.3f}")


def demo_complete_learning_loop():
    """Demonstrate the complete learning loop orchestration."""
    print_header("Complete Learning Loop Demo")
    
    learning_loop = get_learning_loop()
    
    # Create sample payment instruction
    payment_instruction = PaymentInstruction(
        instruction_id="demo_instruction_004",
        trace_id="demo_trace_004",
        selected_rail="ACH",
        selected_processor="carat",
        selected_instrument="bank_transfer",
        amount=1500.0,
        currency="USD",
        effective_cost=18.0,
        settlement_time_hours=24,
        confidence=0.93,
        explanation="Selected ACH rail for cost optimization while maintaining reliability",
        alternatives=[],
        constraints_applied=[],
        metadata={"risk_score": 0.25, "merchant_id": "merchant_002"}
    )
    
    # Create available alternatives
    alternatives = [
        {
            "rail_type": "Card",
            "instrument_type": "credit_card",
            "processor_id": "stripe",
            "cost_bps": 200.0,
            "settlement_days": 2,
            "risk_score": 0.4,
            "score": 0.75
        },
        {
            "rail_type": "RTP",
            "instrument_type": "bank_transfer",
            "processor_id": "carat",
            "cost_bps": 20.0,
            "settlement_days": 0,
            "risk_score": 0.3,
            "score": 0.82
        }
    ]
    
    print_section("Processing Payment with Learning")
    learning_result = learning_loop.process_payment_with_learning(
        payment_instruction,
        alternatives,
        shadow_mode=True
    )
    
    print(f"Trace ID: {learning_result['trace_id']}")
    print(f"Shadow Mode: {learning_result['shadow_mode']}")
    print(f"Counterfactuals Generated: {len(learning_result['counterfactuals']['alternatives'])}")
    
    if learning_result['selected_action']:
        selected = learning_result['selected_action']
        print(f"Selected Action: {selected['rail_type']} with {selected['instrument_type']}")
    
    print_section("Updating with Outcome")
    # Simulate outcome data
    outcome_data = {
        "actual_cost": 17.5,
        "settlement_time_hours": 22,
        "approval_status": "approved",
        "customer_rating": 0.92,
        "risk_events": 0,
        "rail_type": "ACH",
        "instrument_type": "bank_transfer",
        "processor_id": "carat"
    }
    
    update_result = learning_loop.update_with_outcome(
        payment_instruction.trace_id,
        outcome_data,
        payment_instruction
    )
    
    print(f"Reward Calculated: {update_result['reward_data']['total_reward']:.3f}")
    print("Reward Components:")
    for component, value in update_result['reward_data']['components'].items():
        print(f"  {component}: {value:.3f}")
    
    print_section("Learning Loop Statistics")
    stats = learning_result['bandit_statistics']
    print(f"Epsilon: {stats['epsilon']}")
    print(f"Total Actions Tracked: {stats['total_actions']}")
    print(f"Action Counts: {stats['action_counts']}")


def main():
    """Run the complete learning loop demo."""
    print("🚀 Orca Learning Loop Phase 9 Demo")
    print("=" * 60)
    
    try:
        # Run individual demos
        demo_reward_function()
        demo_counterfactual_generation()
        demo_epsilon_greedy_bandit()
        demo_explainability_diffs()
        demo_complete_learning_loop()
        
        print_header("Demo Complete! ✅")
        print("The learning loop is now operational with:")
        print("• Reward function optimization")
        print("• Counterfactual analysis")
        print("• Epsilon-greedy exploration/exploitation")
        print("• Explainability difference tracking")
        print("• Complete learning orchestration")
        print("\nNext steps:")
        print("• Integrate with Weave for outcomes tracking")
        print("• Set up nightly aggregation jobs")
        print("• Configure drift detection monitoring")
        print("• Implement auto-rollback procedures")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())








