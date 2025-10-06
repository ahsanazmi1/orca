"""
Payment Instruction Finalization for Orca Phase 4

This module handles the finalization of optimal path selection by consuming
negotiation results, policies, trust signals, and treasury constraints to
generate final payment instructions.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .events import emit_payment_explanation_event, emit_counterfactual_event
from .ml.xgb_infer import XGBoostInference
from .models import (
    PaymentInstruction,
    NegotiationResponse,
    PolicyConstraint,
    TrustSignal,
    TreasuryConstraint,
    CounterfactualAnalysis,
    RailType,
)

# Set up logging
logger = logging.getLogger(__name__)


class PaymentInstructionFinalizer:
    """Finalizes optimal payment instruction from negotiation results and constraints."""

    def __init__(self, model_dir: str = "models"):
        """Initialize the payment instruction finalizer."""
        self.ml_inference = XGBoostInference(model_dir)
        self.weights = {
            "cost": 0.4,
            "speed": 0.3,
            "risk": 0.3
        }

    def finalize_payment_instruction(
        self,
        negotiation_response: NegotiationResponse,
        policy_constraints: List[PolicyConstraint],
        trust_signal: TrustSignal,
        treasury_constraints: List[TreasuryConstraint],
        processor_auction_results: Optional[Dict[str, Any]] = None,
        trace_id: str = None
    ) -> PaymentInstruction:
        """
        Finalize optimal payment instruction from negotiation results and constraints.
        
        Args:
            negotiation_response: Results from Phase 3 rail negotiation
            policy_constraints: Policy constraints from Olive agent
            trust_signal: Trust signal from Onyx agent
            treasury_constraints: Treasury constraints from Oasis agent
            processor_auction_results: Results from processor auction (optional)
            trace_id: Transaction trace ID
            
        Returns:
            PaymentInstruction: Final payment instruction
        """
        if trace_id is None:
            trace_id = f"instruction_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
        logger.info(f"Finalizing payment instruction for trace_id: {trace_id}")
        
        # Get the optimal rail from negotiation
        optimal_rail = negotiation_response.optimal_rail
        rail_evaluations = negotiation_response.rail_evaluations
        
        # Find the evaluation for the optimal rail
        optimal_evaluation = next(
            (eval for eval in rail_evaluations if eval.rail_type == optimal_rail),
            None
        )
        
        if not optimal_evaluation:
            raise ValueError(f"No evaluation found for optimal rail: {optimal_rail}")
        
        # Apply ML risk scoring to effective cost calculation
        risk_adjusted_cost = self._calculate_risk_adjusted_cost(
            optimal_evaluation,
            trust_signal,
            policy_constraints
        )
        
        # Select optimal processor and instrument
        processor_info = self._select_optimal_processor(
            processor_auction_results,
            optimal_rail,
            risk_adjusted_cost
        )
        
        # Generate explanation
        explanation = self._generate_payment_explanation(
            optimal_rail,
            optimal_evaluation,
            processor_info,
            policy_constraints,
            trust_signal,
            treasury_constraints
        )
        
        # Generate top-k alternatives
        alternatives = self._generate_alternatives(
            rail_evaluations,
            processor_auction_results,
            trust_signal
        )
        
        # Create payment instruction
        instruction = PaymentInstruction(
            instruction_id=str(uuid.uuid4()),
            trace_id=trace_id,
            selected_rail=optimal_rail,
            selected_processor=processor_info.get("processor_id", "default"),
            selected_instrument=processor_info.get("instrument", "default"),
            amount=negotiation_response.rail_evaluations[0].cost,  # Assuming first evaluation has the amount
            currency="USD",  # Default currency
            effective_cost=risk_adjusted_cost,
            settlement_time_hours=optimal_evaluation.settlement_time_hours,
            confidence=negotiation_response.confidence * trust_signal.confidence,
            explanation=explanation,
            alternatives=alternatives,
            constraints_applied=self._format_constraints(
                policy_constraints,
                trust_signal,
                treasury_constraints
            ),
            metadata={
                "negotiation_metadata": negotiation_response.negotiation_metadata,
                "trust_score": trust_signal.trust_score,
                "risk_level": trust_signal.risk_level,
                "ml_risk_score": self._get_ml_risk_score(trust_signal),
                "finalization_timestamp": datetime.now().isoformat()
            }
        )
        
        # Emit explanation event
        emit_payment_explanation_event(instruction, trace_id)
        
        # Generate and emit counterfactual analysis
        counterfactual = self._generate_counterfactual_analysis(
            instruction,
            rail_evaluations,
            alternatives,
            trace_id
        )
        emit_counterfactual_event(counterfactual, trace_id)
        
        logger.info(f"Payment instruction finalized: {instruction.instruction_id}")
        return instruction

    def _calculate_risk_adjusted_cost(
        self,
        evaluation,
        trust_signal: TrustSignal,
        policy_constraints: List[PolicyConstraint]
    ) -> float:
        """Calculate risk-adjusted effective cost using ML risk scoring."""
        base_cost = evaluation.cost
        
        # Get ML risk score
        ml_risk_score = self._get_ml_risk_score(trust_signal)
        
        # Apply risk adjustment
        risk_multiplier = 1.0 + (ml_risk_score * 0.5)  # Up to 50% cost increase for high risk
        
        # Apply policy constraints
        policy_adjustment = self._calculate_policy_adjustment(policy_constraints)
        
        risk_adjusted_cost = base_cost * risk_multiplier * policy_adjustment
        
        logger.debug(f"Risk adjustment: base_cost={base_cost}, ml_risk={ml_risk_score}, "
                    f"risk_multiplier={risk_multiplier}, policy_adjustment={policy_adjustment}, "
                    f"final_cost={risk_adjusted_cost}")
        
        return risk_adjusted_cost

    def _get_ml_risk_score(self, trust_signal: TrustSignal) -> float:
        """Get ML risk score from trust signal or XGBoost model."""
        try:
            # Try to get ML risk score from XGBoost model
            # This would use the actual ML model in a real implementation
            ml_score = self.ml_inference.predict_risk({
                "trust_score": trust_signal.trust_score,
                "risk_level": trust_signal.risk_level,
                "confidence": trust_signal.confidence
            })
            return ml_score
        except Exception as e:
            logger.warning(f"ML risk prediction failed, using trust score: {e}")
            # Fallback to trust signal
            return 1.0 - trust_signal.trust_score

    def _calculate_policy_adjustment(self, policy_constraints: List[PolicyConstraint]) -> float:
        """Calculate policy-based cost adjustment."""
        if not policy_constraints:
            return 1.0
        
        total_adjustment = 1.0
        for constraint in policy_constraints:
            # Apply policy weight to adjustment
            adjustment = constraint.constraint_value * constraint.weight
            total_adjustment += adjustment
        
        return max(0.1, min(2.0, total_adjustment))  # Clamp between 0.1 and 2.0

    def _select_optimal_processor(
        self,
        auction_results: Optional[Dict[str, Any]],
        rail_type: RailType,
        risk_adjusted_cost: float
    ) -> Dict[str, Any]:
        """Select optimal processor based on auction results or defaults."""
        if auction_results and "winning_processor" in auction_results:
            return auction_results["winning_processor"]
        
        # Default processor selection based on rail type
        default_processors = {
            "Card": {"processor_id": "stripe", "instrument": "visa_card", "cost": risk_adjusted_cost},
            "ACH": {"processor_id": "plaid", "instrument": "bank_account", "cost": risk_adjusted_cost * 0.3}
        }
        
        return default_processors.get(rail_type, {
            "processor_id": "default",
            "instrument": "default",
            "cost": risk_adjusted_cost
        })

    def _generate_payment_explanation(
        self,
        optimal_rail: RailType,
        evaluation,
        processor_info: Dict[str, Any],
        policy_constraints: List[PolicyConstraint],
        trust_signal: TrustSignal,
        treasury_constraints: List[TreasuryConstraint]
    ) -> str:
        """Generate human-readable explanation for payment instruction."""
        explanations = []
        
        # Base explanation
        explanations.append(f"Selected {optimal_rail} rail with {processor_info.get('processor_id', 'default')} processor")
        
        # Cost explanation
        explanations.append(f"Effective cost: ${evaluation.cost:.2f} (risk-adjusted from trust score: {trust_signal.trust_score:.2f})")
        
        # Speed explanation
        explanations.append(f"Settlement time: {evaluation.settlement_time_hours} hours")
        
        # Trust explanation
        explanations.append(f"Trust assessment: {trust_signal.risk_level} risk level with {trust_signal.confidence:.2f} confidence")
        
        # Policy constraints
        if policy_constraints:
            constraint_names = [c.policy_type for c in policy_constraints]
            explanations.append(f"Applied policy constraints: {', '.join(constraint_names)}")
        
        # Treasury constraints
        if treasury_constraints:
            treasury_status = [c.status for c in treasury_constraints]
            explanations.append(f"Treasury constraints: {', '.join(treasury_status)}")
        
        return ". ".join(explanations) + "."

    def _generate_alternatives(
        self,
        rail_evaluations: List,
        auction_results: Optional[Dict[str, Any]],
        trust_signal: TrustSignal
    ) -> List[Dict[str, Any]]:
        """Generate top-k alternative payment options."""
        alternatives = []
        
        # Sort evaluations by score (descending)
        sorted_evaluations = sorted(rail_evaluations, key=lambda x: x.score, reverse=True)
        
        # Take top 3 alternatives (excluding the optimal one)
        for i, evaluation in enumerate(sorted_evaluations[1:4], 1):
            alternative = {
                "rank": i,
                "rail_type": evaluation.rail_type,
                "score": evaluation.score,
                "cost": evaluation.cost,
                "settlement_time_hours": evaluation.settlement_time_hours,
                "confidence": evaluation.confidence,
                "explanation": evaluation.explanation,
                "why_not_selected": f"Lower overall score ({evaluation.score:.3f} vs {sorted_evaluations[0].score:.3f})"
            }
            alternatives.append(alternative)
        
        return alternatives

    def _format_constraints(
        self,
        policy_constraints: List[PolicyConstraint],
        trust_signal: TrustSignal,
        treasury_constraints: List[TreasuryConstraint]
    ) -> List[Dict[str, Any]]:
        """Format constraints for inclusion in payment instruction."""
        constraints = []
        
        # Policy constraints
        for constraint in policy_constraints:
            constraints.append({
                "type": "policy",
                "name": constraint.policy_type,
                "value": constraint.constraint_value,
                "weight": constraint.weight,
                "description": constraint.description
            })
        
        # Trust signal
        constraints.append({
            "type": "trust",
            "name": "trust_assessment",
            "value": trust_signal.trust_score,
            "weight": 1.0,
            "description": f"Trust score: {trust_signal.trust_score:.3f}, Risk level: {trust_signal.risk_level}"
        })
        
        # Treasury constraints
        for constraint in treasury_constraints:
            constraints.append({
                "type": "treasury",
                "name": constraint.constraint_type,
                "value": constraint.constraint_value,
                "status": constraint.status,
                "description": f"Available balance: ${constraint.available_balance:.2f}"
            })
        
        return constraints

    def _generate_counterfactual_analysis(
        self,
        instruction: PaymentInstruction,
        rail_evaluations: List,
        alternatives: List[Dict[str, Any]],
        trace_id: str
    ) -> CounterfactualAnalysis:
        """Generate counterfactual analysis for the payment instruction."""
        
        # Analyze scenario differences
        scenario_differences = []
        for alt in alternatives:
            difference = {
                "alternative_rank": alt["rank"],
                "rail_difference": alt["rail_type"] != instruction.selected_rail,
                "cost_difference": alt["cost"] - instruction.effective_cost,
                "time_difference": alt["settlement_time_hours"] - instruction.settlement_time_hours,
                "score_difference": alt["score"] - instruction.confidence
            }
            scenario_differences.append(difference)
        
        # Sensitivity analysis
        sensitivity_analysis = {
            "cost_sensitivity": self._analyze_cost_sensitivity(rail_evaluations),
            "trust_sensitivity": self._analyze_trust_sensitivity(instruction),
            "policy_sensitivity": self._analyze_policy_sensitivity(instruction)
        }
        
        return CounterfactualAnalysis(
            trace_id=trace_id,
            original_instruction=instruction,
            alternatives=alternatives,
            scenario_differences=scenario_differences,
            sensitivity_analysis=sensitivity_analysis
        )

    def _analyze_cost_sensitivity(self, rail_evaluations: List) -> Dict[str, Any]:
        """Analyze cost sensitivity across different rails."""
        costs = [eval.cost for eval in rail_evaluations]
        return {
            "min_cost": min(costs),
            "max_cost": max(costs),
            "cost_range": max(costs) - min(costs),
            "cost_std": sum(costs) / len(costs) if costs else 0
        }

    def _analyze_trust_sensitivity(self, instruction: PaymentInstruction) -> Dict[str, Any]:
        """Analyze trust sensitivity of the instruction."""
        trust_score = instruction.metadata.get("trust_score", 0.5)
        return {
            "trust_score": trust_score,
            "risk_level": instruction.metadata.get("risk_level", "medium"),
            "confidence_impact": instruction.confidence
        }

    def _analyze_policy_sensitivity(self, instruction: PaymentInstruction) -> Dict[str, Any]:
        """Analyze policy sensitivity of the instruction."""
        constraints = instruction.constraints_applied
        policy_constraints = [c for c in constraints if c.get("type") == "policy"]
        
        return {
            "policy_count": len(policy_constraints),
            "policy_types": [c.get("name") for c in policy_constraints],
            "total_weight": sum(c.get("weight", 0) for c in policy_constraints)
        }








