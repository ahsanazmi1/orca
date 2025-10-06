"""
Explainability Diffs for Orca Phase 9.

Implements explainability difference analysis to understand why
different payment paths were selected and how decisions changed
over time for learning loop optimization.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.orca_core.models import (
    PaymentInstruction, CounterfactualAnalysis, RailType, InstrumentType
)
from src.orca_core.events import emit_payment_explanation_event

logger = logging.getLogger(__name__)


class ExplainabilityDiffAnalyzer:
    """
    Analyzes differences in payment decision explanations.
    
    Compares explanations between different payment paths, time periods,
    and configurations to understand decision-making patterns and changes.
    """
    
    def __init__(self):
        """Initialize the explainability diff analyzer."""
        self.explanation_history = {}  # Store explanation history
        logger.info("Explainability diff analyzer initialized")
    
    def analyze_explanation_diff(
        self,
        current_instruction: PaymentInstruction,
        previous_instruction: Optional[PaymentInstruction] = None,
        counterfactual_analysis: Optional[CounterfactualAnalysis] = None,
        baseline_explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze differences in payment explanations.
        
        Args:
            current_instruction: Current payment instruction
            previous_instruction: Previous instruction for comparison (optional)
            counterfactual_analysis: Counterfactual analysis (optional)
            baseline_explanation: Baseline explanation for comparison (optional)
            
        Returns:
            Dictionary containing explanation diff analysis
        """
        try:
            current_explanation = current_instruction.explanation
            
            # Analyze different types of diffs
            diff_analysis = {
                "trace_id": current_instruction.trace_id,
                "instruction_id": current_instruction.instruction_id,
                "current_explanation": current_explanation,
                "diff_timestamp": datetime.now().isoformat()
            }
            
            # Compare with previous instruction
            if previous_instruction:
                previous_diff = self._compare_with_previous(
                    current_instruction, previous_instruction
                )
                diff_analysis["previous_comparison"] = previous_diff
            
            # Compare with counterfactuals
            if counterfactual_analysis:
                counterfactual_diff = self._compare_with_counterfactuals(
                    current_instruction, counterfactual_analysis
                )
                diff_analysis["counterfactual_comparison"] = counterfactual_diff
            
            # Compare with baseline
            if baseline_explanation:
                baseline_diff = self._compare_with_baseline(
                    current_explanation, baseline_explanation
                )
                diff_analysis["baseline_comparison"] = baseline_diff
            
            # Analyze decision factors
            decision_factors = self._extract_decision_factors(current_instruction)
            diff_analysis["decision_factors"] = decision_factors
            
            # Calculate explanation confidence
            explanation_confidence = self._calculate_explanation_confidence(
                current_instruction, diff_analysis
            )
            diff_analysis["explanation_confidence"] = explanation_confidence
            
            # Store explanation for future comparison
            self._store_explanation(current_instruction)
            
            logger.info(f"Analyzed explanation diff for trace {current_instruction.trace_id}")
            return diff_analysis
            
        except Exception as e:
            logger.error(f"Explanation diff analysis failed: {str(e)}")
            return {
                "trace_id": current_instruction.trace_id,
                "error": str(e),
                "diff_timestamp": datetime.now().isoformat()
            }
    
    def _compare_with_previous(
        self,
        current: PaymentInstruction,
        previous: PaymentInstruction
    ) -> Dict[str, Any]:
        """Compare current explanation with previous instruction."""
        return {
            "comparison_type": "previous_instruction",
            "previous_trace_id": previous.trace_id,
            "rail_changed": current.selected_rail != previous.selected_rail,
            "instrument_changed": current.selected_instrument != previous.selected_instrument,
            "processor_changed": current.selected_processor != previous.selected_processor,
            "cost_change": current.effective_cost - previous.effective_cost,
            "settlement_time_change": current.settlement_time_hours - previous.settlement_time_hours,
            "confidence_change": current.confidence - previous.confidence,
            "explanation_similarity": self._calculate_explanation_similarity(
                current.explanation, previous.explanation
            ),
            "decision_consistency": self._assess_decision_consistency(current, previous)
        }
    
    def _compare_with_counterfactuals(
        self,
        current: PaymentInstruction,
        counterfactual_analysis: CounterfactualAnalysis
    ) -> Dict[str, Any]:
        """Compare current explanation with counterfactual alternatives."""
        alternatives = counterfactual_analysis.alternatives
        scenario_differences = counterfactual_analysis.scenario_differences
        
        if not alternatives:
            return {
                "comparison_type": "counterfactuals",
                "alternatives_count": 0,
                "message": "No alternatives available for comparison"
            }
        
        # Find best alternative
        best_alternative = None
        best_score = -1
        
        for alt in alternatives:
            score = alt.get("score", 0.0)
            if score > best_score:
                best_score = score
                best_alternative = alt
        
        # Compare with best alternative
        comparison = {
            "comparison_type": "counterfactuals",
            "alternatives_count": len(alternatives),
            "best_alternative": best_alternative,
            "best_alternative_score": best_score,
            "current_vs_best": self._compare_with_alternative(current, best_alternative) if best_alternative else None
        }
        
        # Analyze scenario differences
        if scenario_differences:
            comparison["scenario_analysis"] = {
                "total_scenarios": len(scenario_differences),
                "significant_differences": [
                    diff for diff in scenario_differences
                    if abs(diff.get("cost_difference", 0)) > 10 or
                       abs(diff.get("settlement_time_difference", 0)) > 24
                ]
            }
        
        return comparison
    
    def _compare_with_baseline(
        self,
        current_explanation: str,
        baseline_explanation: str
    ) -> Dict[str, Any]:
        """Compare current explanation with baseline explanation."""
        return {
            "comparison_type": "baseline",
            "explanation_similarity": self._calculate_explanation_similarity(
                current_explanation, baseline_explanation
            ),
            "explanation_length_diff": len(current_explanation) - len(baseline_explanation),
            "key_terms_diff": self._extract_key_terms_diff(current_explanation, baseline_explanation),
            "tone_analysis": self._analyze_explanation_tone_diff(current_explanation, baseline_explanation)
        }
    
    def _compare_with_alternative(
        self,
        current: PaymentInstruction,
        alternative: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare current instruction with an alternative."""
        return {
            "rail_comparison": {
                "current": current.selected_rail,
                "alternative": alternative.get("rail_type"),
                "different": current.selected_rail != alternative.get("rail_type")
            },
            "cost_comparison": {
                "current_cost": current.effective_cost,
                "alternative_cost": alternative.get("cost_bps", 0) * current.amount / 10000,
                "cost_difference": current.effective_cost - (alternative.get("cost_bps", 0) * current.amount / 10000)
            },
            "settlement_comparison": {
                "current_time": current.settlement_time_hours,
                "alternative_time": alternative.get("settlement_days", 1) * 24,
                "time_difference": current.settlement_time_hours - (alternative.get("settlement_days", 1) * 24)
            },
            "risk_comparison": {
                "current_risk": current.metadata.get("risk_score", 0.5),
                "alternative_risk": alternative.get("risk_score", 0.5),
                "risk_difference": current.metadata.get("risk_score", 0.5) - alternative.get("risk_score", 0.5)
            }
        }
    
    def _extract_decision_factors(self, instruction: PaymentInstruction) -> Dict[str, Any]:
        """Extract key decision factors from payment instruction."""
        return {
            "primary_factors": self._identify_primary_factors(instruction),
            "constraint_impacts": self._analyze_constraint_impacts(instruction),
            "risk_assessment": self._extract_risk_assessment(instruction),
            "cost_optimization": self._analyze_cost_optimization(instruction),
            "speed_considerations": self._analyze_speed_considerations(instruction)
        }
    
    def _identify_primary_factors(self, instruction: PaymentInstruction) -> List[str]:
        """Identify primary decision factors from explanation."""
        explanation = instruction.explanation.lower()
        factors = []
        
        if "cost" in explanation or "fee" in explanation:
            factors.append("cost_optimization")
        if "speed" in explanation or "settlement" in explanation:
            factors.append("settlement_speed")
        if "risk" in explanation or "security" in explanation:
            factors.append("risk_management")
        if "approval" in explanation or "success" in explanation:
            factors.append("approval_rate")
        if "policy" in explanation or "constraint" in explanation:
            factors.append("policy_compliance")
        
        return factors if factors else ["general_optimization"]
    
    def _analyze_constraint_impacts(self, instruction: PaymentInstruction) -> Dict[str, Any]:
        """Analyze how constraints influenced the decision."""
        constraints_applied = instruction.constraints_applied
        
        return {
            "total_constraints": len(constraints_applied),
            "constraint_types": list(set(constraint.get("type", "unknown") for constraint in constraints_applied)),
            "constraint_impact_score": self._calculate_constraint_impact_score(constraints_applied),
            "primary_constraint": self._identify_primary_constraint(constraints_applied)
        }
    
    def _extract_risk_assessment(self, instruction: PaymentInstruction) -> Dict[str, Any]:
        """Extract risk assessment information."""
        metadata = instruction.metadata
        
        return {
            "risk_score": metadata.get("risk_score", 0.5),
            "risk_level": metadata.get("risk_level", "medium"),
            "risk_factors": metadata.get("risk_factors", []),
            "risk_mitigation": metadata.get("risk_mitigation", []),
            "confidence_in_risk_assessment": metadata.get("risk_confidence", 0.5)
        }
    
    def _analyze_cost_optimization(self, instruction: PaymentInstruction) -> Dict[str, Any]:
        """Analyze cost optimization aspects."""
        return {
            "effective_cost": instruction.effective_cost,
            "cost_breakdown": instruction.metadata.get("cost_breakdown", {}),
            "cost_optimization_score": self._calculate_cost_optimization_score(instruction),
            "alternative_costs": instruction.metadata.get("alternative_costs", [])
        }
    
    def _analyze_speed_considerations(self, instruction: PaymentInstruction) -> Dict[str, Any]:
        """Analyze speed and settlement considerations."""
        return {
            "settlement_time_hours": instruction.settlement_time_hours,
            "speed_priority": instruction.metadata.get("speed_priority", "medium"),
            "real_time_requirement": instruction.metadata.get("real_time_required", False),
            "speed_vs_cost_tradeoff": instruction.metadata.get("speed_cost_tradeoff", "balanced")
        }
    
    def _calculate_explanation_similarity(self, explanation1: str, explanation2: str) -> float:
        """Calculate similarity between two explanations."""
        # Simple word-based similarity (in production, use more sophisticated NLP)
        words1 = set(explanation1.lower().split())
        words2 = set(explanation2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _assess_decision_consistency(self, current: PaymentInstruction, previous: PaymentInstruction) -> Dict[str, Any]:
        """Assess consistency between current and previous decisions."""
        return {
            "consistent_rail_selection": current.selected_rail == previous.selected_rail,
            "consistent_cost_range": abs(current.effective_cost - previous.effective_cost) / previous.effective_cost < 0.2,
            "consistent_settlement_time": abs(current.settlement_time_hours - previous.settlement_time_hours) < 24,
            "consistent_confidence": abs(current.confidence - previous.confidence) < 0.1,
            "overall_consistency_score": self._calculate_overall_consistency_score(current, previous)
        }
    
    def _calculate_overall_consistency_score(self, current: PaymentInstruction, previous: PaymentInstruction) -> float:
        """Calculate overall consistency score between instructions."""
        consistency_factors = [
            current.selected_rail == previous.selected_rail,
            abs(current.effective_cost - previous.effective_cost) / previous.effective_cost < 0.2,
            abs(current.settlement_time_hours - previous.settlement_time_hours) < 24,
            abs(current.confidence - previous.confidence) < 0.1
        ]
        
        return sum(consistency_factors) / len(consistency_factors)
    
    def _extract_key_terms_diff(self, explanation1: str, explanation2: str) -> Dict[str, Any]:
        """Extract differences in key terms between explanations."""
        # Simple key term extraction
        key_terms = ["cost", "speed", "risk", "approval", "policy", "constraint", "optimization"]
        
        terms1 = [term for term in key_terms if term in explanation1.lower()]
        terms2 = [term for term in key_terms if term in explanation2.lower()]
        
        return {
            "terms_in_current": terms1,
            "terms_in_baseline": terms2,
            "new_terms": list(set(terms1) - set(terms2)),
            "removed_terms": list(set(terms2) - set(terms1)),
            "common_terms": list(set(terms1).intersection(set(terms2)))
        }
    
    def _analyze_explanation_tone_diff(self, explanation1: str, explanation2: str) -> Dict[str, Any]:
        """Analyze tone differences between explanations."""
        # Simple tone analysis (in production, use sentiment analysis)
        positive_words = ["optimal", "best", "efficient", "secure", "fast", "reliable"]
        negative_words = ["risk", "constraint", "limitation", "delay", "cost"]
        
        def count_words(text, word_list):
            return sum(1 for word in word_list if word in text.lower())
        
        return {
            "current_tone": {
                "positive_words": count_words(explanation1, positive_words),
                "negative_words": count_words(explanation1, negative_words)
            },
            "baseline_tone": {
                "positive_words": count_words(explanation2, positive_words),
                "negative_words": count_words(explanation2, negative_words)
            },
            "tone_change": {
                "positive_change": count_words(explanation1, positive_words) - count_words(explanation2, positive_words),
                "negative_change": count_words(explanation1, negative_words) - count_words(explanation2, negative_words)
            }
        }
    
    def _calculate_constraint_impact_score(self, constraints: List[Dict[str, Any]]) -> float:
        """Calculate impact score of constraints on decision."""
        if not constraints:
            return 0.0
        
        # Simple scoring based on constraint types and severity
        impact_scores = []
        for constraint in constraints:
            constraint_type = constraint.get("type", "unknown")
            severity = constraint.get("severity", "medium")
            
            type_score = {
                "policy": 0.8,
                "risk": 0.7,
                "cost": 0.6,
                "speed": 0.5,
                "unknown": 0.3
            }.get(constraint_type, 0.3)
            
            severity_multiplier = {
                "high": 1.0,
                "medium": 0.7,
                "low": 0.4
            }.get(severity, 0.7)
            
            impact_scores.append(type_score * severity_multiplier)
        
        return sum(impact_scores) / len(impact_scores)
    
    def _identify_primary_constraint(self, constraints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Identify the primary constraint that influenced the decision."""
        if not constraints:
            return None
        
        # Find constraint with highest impact
        primary_constraint = max(
            constraints,
            key=lambda c: self._calculate_constraint_impact_score([c])
        )
        
        return primary_constraint
    
    def _calculate_cost_optimization_score(self, instruction: PaymentInstruction) -> float:
        """Calculate cost optimization score."""
        # Simple scoring based on cost and alternatives
        base_score = 0.5
        
        # Adjust based on effective cost (lower is better)
        if instruction.effective_cost < 10:
            base_score += 0.3
        elif instruction.effective_cost < 50:
            base_score += 0.2
        elif instruction.effective_cost > 100:
            base_score -= 0.2
        
        # Adjust based on alternatives
        alternatives = instruction.alternatives
        if alternatives:
            alternative_costs = [alt.get("cost", instruction.effective_cost) for alt in alternatives]
            if alternative_costs:
                min_alternative_cost = min(alternative_costs)
                if instruction.effective_cost <= min_alternative_cost:
                    base_score += 0.2
        
        return max(0.0, min(1.0, base_score))
    
    def _calculate_explanation_confidence(self, instruction: PaymentInstruction, diff_analysis: Dict[str, Any]) -> float:
        """Calculate confidence in the explanation."""
        base_confidence = instruction.confidence
        
        # Adjust based on explanation consistency
        if "previous_comparison" in diff_analysis:
            consistency_score = diff_analysis["previous_comparison"].get("decision_consistency", {}).get("overall_consistency_score", 0.5)
            base_confidence = (base_confidence + consistency_score) / 2
        
        # Adjust based on decision factors clarity
        decision_factors = diff_analysis.get("decision_factors", {})
        primary_factors = decision_factors.get("primary_factors", [])
        if len(primary_factors) > 0:
            base_confidence += 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _store_explanation(self, instruction: PaymentInstruction) -> None:
        """Store explanation for future comparison."""
        explanation_record = {
            "trace_id": instruction.trace_id,
            "instruction_id": instruction.instruction_id,
            "explanation": instruction.explanation,
            "decision_factors": self._extract_decision_factors(instruction),
            "timestamp": datetime.now().isoformat()
        }
        
        self.explanation_history[instruction.trace_id] = explanation_record
        
        # Keep only recent explanations (last 1000)
        if len(self.explanation_history) > 1000:
            oldest_key = min(self.explanation_history.keys())
            del self.explanation_history[oldest_key]
    
    def get_explanation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent explanation history."""
        history_items = list(self.explanation_history.values())
        return sorted(history_items, key=lambda x: x["timestamp"], reverse=True)[:limit]


# Global instance
_explainability_diff_analyzer = None


def get_explainability_diff_analyzer() -> ExplainabilityDiffAnalyzer:
    """Get global explainability diff analyzer instance."""
    global _explainability_diff_analyzer
    if _explainability_diff_analyzer is None:
        _explainability_diff_analyzer = ExplainabilityDiffAnalyzer()
    return _explainability_diff_analyzer








