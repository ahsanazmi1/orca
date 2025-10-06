#!/usr/bin/env python3
"""
Demo script for Orca Phase 4 Payment Instruction functionality.

This script demonstrates how to use the PaymentInstructionFinalizer to generate
final payment instructions from negotiation results and constraints.
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orca_core.models import (
    NegotiationRequest,
    NegotiationResponse,
    RailEvaluation,
    PolicyConstraint,
    TrustSignal,
    TreasuryConstraint
)
from orca_core.payment_instruction import PaymentInstructionFinalizer


def create_sample_data():
    """Create sample data for demonstration."""
    
    # Create rail evaluations
    rail_evaluations = [
        RailEvaluation(
            rail_type="Card",
            score=0.85,
            cost=2.50,
            settlement_time_hours=24,
            confidence=0.9,
            risk_adjusted_cost=2.75,
            factors={"cost": 0.3, "speed": 0.4, "risk": 0.3},
            explanation="Card rail offers excellent speed with moderate cost"
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
    
    # Create negotiation response
    negotiation_response = NegotiationResponse(
        optimal_rail="Card",
        rail_evaluations=rail_evaluations,
        explanation="Card rail selected for optimal balance of speed and cost",
        confidence=0.85,
        trace_id="demo_trace_123",
        negotiation_metadata={
            "negotiation_round": 1,
            "bidding_enabled": True,
            "participating_processors": ["stripe", "square", "paypal"]
        }
    )
    
    # Create policy constraints
    policy_constraints = [
        PolicyConstraint(
            policy_type="max_transaction_cost",
            constraint_value=5.00,
            weight=0.8,
            description="Maximum cost per transaction cannot exceed $5.00"
        ),
        PolicyConstraint(
            policy_type="min_trust_score",
            constraint_value=0.7,
            weight=0.6,
            description="Minimum trust score requirement of 0.7"
        )
    ]
    
    # Create trust signal
    trust_signal = TrustSignal(
        trust_score=0.85,
        risk_level="low",
        signals=[
            {
                "type": "device_fingerprint",
                "score": 0.9,
                "description": "Device fingerprint matches known customer devices"
            },
            {
                "type": "payment_history",
                "score": 0.8,
                "description": "Strong payment history with low chargeback rate"
            }
        ],
        confidence=0.88
    )
    
    # Create treasury constraints
    treasury_constraints = [
        TreasuryConstraint(
            constraint_type="available_balance",
            status="passed",
            available_balance=25000.00,
            constraint_value=150.00
        ),
        TreasuryConstraint(
            constraint_type="daily_limit",
            status="passed",
            available_balance=100000.00,
            constraint_value=50000.00
        )
    ]
    
    return (
        negotiation_response,
        policy_constraints,
        trust_signal,
        treasury_constraints
    )


def main():
    """Main demo function."""
    print("🚀 Orca Phase 4 Payment Instruction Demo")
    print("=" * 50)
    
    # Create sample data
    (
        negotiation_response,
        policy_constraints,
        trust_signal,
        treasury_constraints
    ) = create_sample_data()
    
    print(f"📊 Negotiation Response:")
    print(f"   Optimal Rail: {negotiation_response.optimal_rail}")
    print(f"   Confidence: {negotiation_response.confidence}")
    print(f"   Available Rails: {[eval.rail_type for eval in negotiation_response.rail_evaluations]}")
    
    print(f"\n🛡️ Trust Signal:")
    print(f"   Trust Score: {trust_signal.trust_score}")
    print(f"   Risk Level: {trust_signal.risk_level}")
    print(f"   Confidence: {trust_signal.confidence}")
    
    print(f"\n📋 Policy Constraints: {len(policy_constraints)}")
    for constraint in policy_constraints:
        print(f"   - {constraint.policy_type}: {constraint.constraint_value} (weight: {constraint.weight})")
    
    print(f"\n💰 Treasury Constraints: {len(treasury_constraints)}")
    for constraint in treasury_constraints:
        print(f"   - {constraint.constraint_type}: {constraint.status}")
    
    # Initialize payment instruction finalizer
    finalizer = PaymentInstructionFinalizer()
    
    print(f"\n🔄 Finalizing Payment Instruction...")
    
    # Generate payment instruction
    instruction = finalizer.finalize_payment_instruction(
        negotiation_response=negotiation_response,
        policy_constraints=policy_constraints,
        trust_signal=trust_signal,
        treasury_constraints=treasury_constraints,
        trace_id="demo_trace_123"
    )
    
    print(f"\n✅ Payment Instruction Generated!")
    print("=" * 50)
    
    # Display results
    print(f"🎯 Selected Rail: {instruction.selected_rail}")
    print(f"🏦 Selected Processor: {instruction.selected_processor}")
    print(f"💳 Selected Instrument: {instruction.selected_instrument}")
    print(f"💵 Amount: ${instruction.amount:.2f}")
    print(f"💰 Effective Cost: ${instruction.effective_cost:.2f}")
    print(f"⏰ Settlement Time: {instruction.settlement_time_hours} hours")
    print(f"🎯 Confidence: {instruction.confidence:.3f}")
    
    print(f"\n📝 Explanation:")
    print(f"   {instruction.explanation}")
    
    print(f"\n🔄 Alternatives ({len(instruction.alternatives)}):")
    for i, alt in enumerate(instruction.alternatives, 1):
        print(f"   {i}. {alt['rail_type']}: ${alt['cost']:.2f}, {alt['settlement_time_hours']}h, score {alt['score']:.3f}")
        print(f"      Why not selected: {alt['why_not_selected']}")
    
    print(f"\n🛡️ Constraints Applied ({len(instruction.constraints_applied)}):")
    for constraint in instruction.constraints_applied:
        print(f"   - [{constraint['type']}] {constraint['name']}: {constraint['description']}")
    
    print(f"\n📊 Metadata:")
    for key, value in instruction.metadata.items():
        if key == "finalization_timestamp":
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: {value}")
    
    # Save to JSON file
    output_file = Path(__file__).parent / "payment_instruction_demo_output.json"
    with open(output_file, "w") as f:
        json.dump(instruction.dict(), f, indent=2, default=str)
    
    print(f"\n💾 Payment instruction saved to: {output_file}")
    print("\n🎉 Demo completed successfully!")


if __name__ == "__main__":
    main()








