"""
Multi-rail and multi-instrument evaluation engine for Orca Phase 7.

Provides comprehensive evaluation of payment rail and instrument combinations,
including ACH, RTP, FedNow, SEPA, and various payment instruments like
debit, prepaid, and stablecoin.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.orca_core.models import (
    RailType, InstrumentType, RailCapability, InstrumentCapability,
    MultiRailEvaluation, MultiRailNegotiationRequest, MultiRailNegotiationResponse
)

logger = logging.getLogger(__name__)


class MultiRailCapabilityRegistry:
    """
    Registry of payment rail and instrument capabilities.
    
    Provides comprehensive capability information for all supported
    payment rails and instruments, including cost, speed, and risk characteristics.
    """
    
    def __init__(self):
        """Initialize the capability registry with predefined rail and instrument capabilities."""
        self.rail_capabilities = self._initialize_rail_capabilities()
        self.instrument_capabilities = self._initialize_instrument_capabilities()
        logger.info("Multi-rail capability registry initialized")
    
    def _initialize_rail_capabilities(self) -> Dict[RailType, RailCapability]:
        """Initialize rail capabilities with comprehensive coverage."""
        return {
            "ACH": RailCapability(
                rail_type="ACH",
                supported_instruments=["debit_card", "bank_transfer"],
                max_amount=1000000.0,
                min_amount=1.0,
                settlement_time_hours=24,
                cost_basis_points=15.0,
                availability_24_7=False,
                cross_border=False,
                real_time=False,
                jurisdictions=["US"]
            ),
            "RTP": RailCapability(
                rail_type="RTP",
                supported_instruments=["debit_card", "bank_transfer"],
                max_amount=1000000.0,
                min_amount=1.0,
                settlement_time_hours=0,  # Real-time
                cost_basis_points=25.0,
                availability_24_7=True,
                cross_border=False,
                real_time=True,
                jurisdictions=["US"]
            ),
            "FedNow": RailCapability(
                rail_type="FedNow",
                supported_instruments=["debit_card", "bank_transfer"],
                max_amount=500000.0,
                min_amount=1.0,
                settlement_time_hours=0,  # Real-time
                cost_basis_points=20.0,
                availability_24_7=True,
                cross_border=False,
                real_time=True,
                jurisdictions=["US"]
            ),
            "SEPA": RailCapability(
                rail_type="SEPA",
                supported_instruments=["bank_transfer", "debit_card"],
                max_amount=50000.0,  # EUR
                min_amount=0.01,
                settlement_time_hours=24,
                cost_basis_points=10.0,
                availability_24_7=False,
                cross_border=True,
                real_time=False,
                jurisdictions=["EU", "EEA"]
            ),
            "Wire": RailCapability(
                rail_type="Wire",
                supported_instruments=["bank_transfer"],
                max_amount=10000000.0,
                min_amount=1000.0,
                settlement_time_hours=4,
                cost_basis_points=50.0,
                availability_24_7=False,
                cross_border=True,
                real_time=False,
                jurisdictions=["US", "EU", "Global"]
            ),
            "Crypto": RailCapability(
                rail_type="Crypto",
                supported_instruments=["stablecoin"],
                max_amount=1000000.0,
                min_amount=1.0,
                settlement_time_hours=1,
                cost_basis_points=5.0,
                availability_24_7=True,
                cross_border=True,
                real_time=True,
                jurisdictions=["Global"]
            ),
            "Card": RailCapability(
                rail_type="Card",
                supported_instruments=["credit_card", "debit_card", "prepaid_card"],
                max_amount=100000.0,
                min_amount=0.01,
                settlement_time_hours=48,
                cost_basis_points=200.0,
                availability_24_7=True,
                cross_border=True,
                real_time=True,
                jurisdictions=["Global"]
            )
        }
    
    def _initialize_instrument_capabilities(self) -> Dict[InstrumentType, InstrumentCapability]:
        """Initialize instrument capabilities with comprehensive coverage."""
        return {
            "credit_card": InstrumentCapability(
                instrument_type="credit_card",
                supported_rails=["Card"],
                max_amount=100000.0,
                min_amount=0.01,
                funding_time_hours=0,
                cost_basis_points=200.0,
                requires_verification=True,
                risk_level="medium",
                regulatory_requirements=["PCI_DSS", "EMV"]
            ),
            "debit_card": InstrumentCapability(
                instrument_type="debit_card",
                supported_rails=["Card", "ACH", "RTP", "FedNow", "SEPA"],
                max_amount=10000.0,
                min_amount=0.01,
                funding_time_hours=0,
                cost_basis_points=150.0,
                requires_verification=True,
                risk_level="low",
                regulatory_requirements=["PCI_DSS", "EMV"]
            ),
            "prepaid_card": InstrumentCapability(
                instrument_type="prepaid_card",
                supported_rails=["Card"],
                max_amount=5000.0,
                min_amount=1.0,
                funding_time_hours=0,
                cost_basis_points=180.0,
                requires_verification=False,
                risk_level="medium",
                regulatory_requirements=["PCI_DSS"]
            ),
            "bank_transfer": InstrumentCapability(
                instrument_type="bank_transfer",
                supported_rails=["ACH", "RTP", "FedNow", "SEPA", "Wire"],
                max_amount=1000000.0,
                min_amount=1.0,
                funding_time_hours=24,
                cost_basis_points=10.0,
                requires_verification=True,
                risk_level="low",
                regulatory_requirements=["KYC", "AML"]
            ),
            "stablecoin": InstrumentCapability(
                instrument_type="stablecoin",
                supported_rails=["Crypto"],
                max_amount=1000000.0,
                min_amount=1.0,
                funding_time_hours=1,
                cost_basis_points=5.0,
                requires_verification=True,
                risk_level="medium",
                regulatory_requirements=["KYC", "AML", "CFT"]
            ),
            "digital_wallet": InstrumentCapability(
                instrument_type="digital_wallet",
                supported_rails=["Card", "ACH"],
                max_amount=50000.0,
                min_amount=0.01,
                funding_time_hours=0,
                cost_basis_points=120.0,
                requires_verification=True,
                risk_level="medium",
                regulatory_requirements=["PCI_DSS"]
            ),
            "bnpl": InstrumentCapability(
                instrument_type="bnpl",
                supported_rails=["Card", "ACH"],
                max_amount=25000.0,
                min_amount=100.0,
                funding_time_hours=0,
                cost_basis_points=300.0,
                requires_verification=True,
                risk_level="high",
                regulatory_requirements=["KYC", "Credit_Check"]
            ),
            "cash": InstrumentCapability(
                instrument_type="cash",
                supported_rails=["Card"],  # Via cash advance
                max_amount=5000.0,
                min_amount=1.0,
                funding_time_hours=0,
                cost_basis_points=400.0,
                requires_verification=False,
                risk_level="high",
                regulatory_requirements=["AML"]
            )
        }
    
    def get_rail_capability(self, rail_type: RailType) -> Optional[RailCapability]:
        """Get capability information for a specific rail."""
        return self.rail_capabilities.get(rail_type)
    
    def get_instrument_capability(self, instrument_type: InstrumentType) -> Optional[InstrumentCapability]:
        """Get capability information for a specific instrument."""
        return self.instrument_capabilities.get(instrument_type)
    
    def get_valid_combinations(self) -> List[Tuple[RailType, InstrumentType]]:
        """Get all valid rail-instrument combinations."""
        combinations = []
        for rail_cap in self.rail_capabilities.values():
            for instrument in rail_cap.supported_instruments:
                if instrument in self.instrument_capabilities:
                    combinations.append((rail_cap.rail_type, instrument))
        return combinations


class MultiRailEvaluator:
    """
    Evaluator for multi-rail and multi-instrument combinations.
    
    Provides comprehensive scoring and evaluation of payment rail and
    instrument combinations based on cost, speed, risk, and availability.
    """
    
    def __init__(self):
        """Initialize the multi-rail evaluator."""
        self.capability_registry = MultiRailCapabilityRegistry()
        logger.info("Multi-rail evaluator initialized")
    
    def evaluate_combination(
        self,
        rail_type: RailType,
        instrument_type: InstrumentType,
        request: MultiRailNegotiationRequest
    ) -> Optional[MultiRailEvaluation]:
        """
        Evaluate a specific rail-instrument combination.
        
        Args:
            rail_type: Payment rail type
            instrument_type: Payment instrument type
            request: Negotiation request with constraints and preferences
            
        Returns:
            Evaluation result or None if combination is invalid
        """
        # Get capabilities
        rail_cap = self.capability_registry.get_rail_capability(rail_type)
        instrument_cap = self.capability_registry.get_instrument_capability(instrument_type)
        
        if not rail_cap or not instrument_cap:
            return None
        
        # Check if combination is valid
        if instrument_type not in rail_cap.supported_instruments:
            return None
        
        if rail_type not in instrument_cap.supported_rails:
            return None
        
        # Check constraints
        if not self._meets_constraints(rail_cap, instrument_cap, request):
            return None
        
        # Calculate scores
        cost_score = self._calculate_cost_score(rail_cap, instrument_cap, request)
        speed_score = self._calculate_speed_score(rail_cap, instrument_cap, request)
        risk_score = self._calculate_risk_score(rail_cap, instrument_cap, request)
        availability_score = self._calculate_availability_score(rail_cap, instrument_cap, request)
        
        # Calculate total score
        total_score = self._calculate_total_score(
            cost_score, speed_score, risk_score, availability_score, request
        )
        
        # Calculate financial metrics
        total_cost = self._calculate_total_cost(rail_cap, instrument_cap, request)
        effective_cost_bps = (total_cost / request.amount) * 10000 if request.amount > 0 else 0
        
        # Determine risk level and compliance
        risk_level = self._determine_risk_level(rail_cap, instrument_cap, request)
        compliance_status = self._determine_compliance_status(rail_cap, instrument_cap, request)
        
        # Generate explanation
        explanation = self._generate_explanation(
            rail_cap, instrument_cap, cost_score, speed_score, risk_score, availability_score
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(rail_cap, instrument_cap, request)
        
        return MultiRailEvaluation(
            rail_type=rail_type,
            instrument_type=instrument_type,
            combination_id=f"{rail_type}_{instrument_type}_{uuid.uuid4().hex[:8]}",
            total_score=total_score,
            cost_score=cost_score,
            speed_score=speed_score,
            risk_score=risk_score,
            availability_score=availability_score,
            total_cost=total_cost,
            effective_cost_bps=effective_cost_bps,
            settlement_time_hours=rail_cap.settlement_time_hours,
            is_available=True,
            is_real_time=rail_cap.real_time,
            is_cross_border=rail_cap.cross_border,
            risk_level=risk_level,
            compliance_status=compliance_status,
            requires_kyc=instrument_cap.requires_verification,
            explanation=explanation,
            confidence=confidence,
            metadata={
                "rail_capability": rail_cap.dict(),
                "instrument_capability": instrument_cap.dict(),
                "request_constraints": request.dict()
            }
        )
    
    def _meets_constraints(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> bool:
        """Check if combination meets request constraints."""
        # Check amount constraints
        if request.amount > rail_cap.max_amount or request.amount < rail_cap.min_amount:
            return False
        
        if request.amount > instrument_cap.max_amount or request.amount < instrument_cap.min_amount:
            return False
        
        # Check settlement time constraint
        if rail_cap.settlement_time_hours > request.max_settlement_hours:
            return False
        
        # Check cost constraint
        total_cost_bps = rail_cap.cost_basis_points + instrument_cap.cost_basis_points
        if total_cost_bps > request.max_cost_bps:
            return False
        
        # Check real-time requirement
        if request.require_real_time and not rail_cap.real_time:
            return False
        
        # Check cross-border requirement
        if request.cross_border and not rail_cap.cross_border:
            return False
        
        return True
    
    def _calculate_cost_score(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate cost efficiency score (higher is better)."""
        total_cost_bps = rail_cap.cost_basis_points + instrument_cap.cost_basis_points
        
        # Normalize to 0-1 scale (lower cost = higher score)
        max_expected_cost = 500.0  # 5% in basis points
        score = max(0.0, 1.0 - (total_cost_bps / max_expected_cost))
        
        return min(1.0, score)
    
    def _calculate_speed_score(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate speed/velocity score (higher is better)."""
        # Real-time rails get highest score
        if rail_cap.real_time:
            return 1.0
        
        # Score based on settlement time (lower time = higher score)
        max_settlement_time = 168  # 1 week in hours
        score = max(0.0, 1.0 - (rail_cap.settlement_time_hours / max_settlement_time))
        
        return min(1.0, score)
    
    def _calculate_risk_score(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate risk assessment score (higher is better)."""
        # Base risk from instrument
        risk_mapping = {"low": 1.0, "medium": 0.7, "high": 0.3}
        base_score = risk_mapping.get(instrument_cap.risk_level, 0.5)
        
        # Adjust for real-time capability (real-time = lower risk)
        if rail_cap.real_time:
            base_score *= 1.1
        
        # Adjust for cross-border (higher risk)
        if rail_cap.cross_border:
            base_score *= 0.9
        
        return min(1.0, base_score)
    
    def _calculate_availability_score(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate availability score (higher is better)."""
        score = 0.5  # Base availability
        
        # 24/7 availability bonus
        if rail_cap.availability_24_7:
            score += 0.3
        
        # Real-time capability bonus
        if rail_cap.real_time:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_total_score(
        self,
        cost_score: float,
        speed_score: float,
        risk_score: float,
        availability_score: float,
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate weighted total score."""
        # Weights based on risk tolerance
        weights = {
            "low": {"cost": 0.4, "speed": 0.3, "risk": 0.2, "availability": 0.1},
            "medium": {"cost": 0.3, "speed": 0.3, "risk": 0.3, "availability": 0.1},
            "high": {"cost": 0.2, "speed": 0.3, "risk": 0.4, "availability": 0.1}
        }
        
        weight_set = weights.get(request.risk_tolerance, weights["medium"])
        
        total_score = (
            cost_score * weight_set["cost"] +
            speed_score * weight_set["speed"] +
            risk_score * weight_set["risk"] +
            availability_score * weight_set["availability"]
        )
        
        return min(1.0, total_score)
    
    def _calculate_total_cost(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate total cost in USD."""
        total_cost_bps = rail_cap.cost_basis_points + instrument_cap.cost_basis_points
        return (request.amount * total_cost_bps) / 10000
    
    def _determine_risk_level(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> str:
        """Determine overall risk level for the combination."""
        instrument_risk = instrument_cap.risk_level
        
        # Adjust based on rail characteristics
        if rail_cap.real_time:
            if instrument_risk == "high":
                return "medium"
            elif instrument_risk == "medium":
                return "low"
        
        if rail_cap.cross_border and instrument_risk == "low":
            return "medium"
        
        return instrument_risk
    
    def _determine_compliance_status(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> str:
        """Determine compliance status for the combination."""
        if instrument_cap.requires_verification:
            return "requires_kyc"
        elif len(instrument_cap.regulatory_requirements) > 3:
            return "high_compliance"
        else:
            return "standard_compliance"
    
    def _generate_explanation(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        cost_score: float,
        speed_score: float,
        risk_score: float,
        availability_score: float
    ) -> str:
        """Generate human-readable explanation of the evaluation."""
        explanation_parts = []
        
        explanation_parts.append(f"{rail_cap.rail_type} rail with {instrument_cap.instrument_type}")
        
        # Cost explanation
        if cost_score > 0.8:
            explanation_parts.append("excellent cost efficiency")
        elif cost_score > 0.6:
            explanation_parts.append("good cost efficiency")
        else:
            explanation_parts.append("moderate cost efficiency")
        
        # Speed explanation
        if rail_cap.real_time:
            explanation_parts.append("real-time processing")
        elif speed_score > 0.7:
            explanation_parts.append("fast settlement")
        else:
            explanation_parts.append("standard settlement time")
        
        # Risk explanation
        explanation_parts.append(f"{instrument_cap.risk_level} risk level")
        
        # Availability explanation
        if rail_cap.availability_24_7:
            explanation_parts.append("24/7 availability")
        
        return ", ".join(explanation_parts) + "."
    
    def _calculate_confidence(
        self,
        rail_cap: RailCapability,
        instrument_cap: InstrumentCapability,
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate confidence in the evaluation."""
        confidence = 0.8  # Base confidence
        
        # Higher confidence for well-established rails
        established_rails = ["ACH", "Card", "Wire"]
        if rail_cap.rail_type in established_rails:
            confidence += 0.1
        
        # Higher confidence for established instruments
        established_instruments = ["credit_card", "debit_card", "bank_transfer"]
        if instrument_cap.instrument_type in established_instruments:
            confidence += 0.1
        
        return min(1.0, confidence)


class MultiRailNegotiationEngine:
    """
    Main negotiation engine for multi-rail and multi-instrument combinations.
    
    Orchestrates the evaluation of all valid combinations and selects
    the optimal rail-instrument combination based on comprehensive scoring.
    """
    
    def __init__(self):
        """Initialize the multi-rail negotiation engine."""
        self.evaluator = MultiRailEvaluator()
        logger.info("Multi-rail negotiation engine initialized")
    
    def negotiate(
        self,
        request: MultiRailNegotiationRequest
    ) -> MultiRailNegotiationResponse:
        """
        Perform multi-rail and multi-instrument negotiation.
        
        Args:
            request: Negotiation request with constraints and preferences
            
        Returns:
            Comprehensive negotiation response with optimal combination
        """
        # Get all valid combinations
        valid_combinations = self.evaluator.capability_registry.get_valid_combinations()
        
        # Filter based on preferences and exclusions
        candidate_combinations = self._filter_candidates(valid_combinations, request)
        
        # Evaluate all candidate combinations
        evaluations = []
        for rail_type, instrument_type in candidate_combinations:
            evaluation = self.evaluator.evaluate_combination(rail_type, instrument_type, request)
            if evaluation:
                evaluations.append(evaluation)
        
        if not evaluations:
            raise ValueError("No valid rail-instrument combinations found for the request")
        
        # Sort by total score (descending)
        evaluations.sort(key=lambda e: e.total_score, reverse=True)
        
        # Select optimal combination
        optimal_combination = evaluations[0]
        
        # Get top alternatives (top 3 excluding optimal)
        top_alternatives = evaluations[1:4]
        
        # Calculate summary metrics
        available_combinations = len([e for e in evaluations if e.is_available])
        real_time_combinations = len([e for e in evaluations if e.is_real_time])
        
        # Generate overall explanation
        explanation = self._generate_negotiation_explanation(
            optimal_combination, evaluations, request
        )
        
        # Calculate overall confidence
        confidence = self._calculate_negotiation_confidence(evaluations, request)
        
        return MultiRailNegotiationResponse(
            trace_id=request.trace_id,
            optimal_combination=optimal_combination,
            all_evaluations=evaluations,
            total_combinations_evaluated=len(evaluations),
            available_combinations=available_combinations,
            real_time_combinations=real_time_combinations,
            top_alternatives=top_alternatives,
            explanation=explanation,
            confidence=confidence,
            negotiation_metadata={
                "candidate_count": len(candidate_combinations),
                "valid_combinations": len(valid_combinations),
                "filtered_combinations": len(candidate_combinations),
                "evaluated_combinations": len(evaluations)
            }
        )
    
    def _filter_candidates(
        self,
        valid_combinations: List[Tuple[RailType, InstrumentType]],
        request: MultiRailNegotiationRequest
    ) -> List[Tuple[RailType, InstrumentType]]:
        """Filter candidate combinations based on preferences and exclusions."""
        candidates = valid_combinations.copy()
        
        # Apply exclusions
        if request.excluded_rails:
            candidates = [(r, i) for r, i in candidates if r not in request.excluded_rails]
        
        if request.excluded_instruments:
            candidates = [(r, i) for r, i in candidates if i not in request.excluded_instruments]
        
        # Apply preferences (if specified, only include preferred combinations)
        if request.preferred_rails or request.preferred_instruments:
            preferred_candidates = []
            
            if request.preferred_rails and request.preferred_instruments:
                # Both rails and instruments specified - intersection
                for rail in request.preferred_rails:
                    for instrument in request.preferred_instruments:
                        if (rail, instrument) in candidates:
                            preferred_candidates.append((rail, instrument))
            elif request.preferred_rails:
                # Only rails specified
                preferred_candidates = [(r, i) for r, i in candidates if r in request.preferred_rails]
            elif request.preferred_instruments:
                # Only instruments specified
                preferred_candidates = [(r, i) for r, i in candidates if i in request.preferred_instruments]
            
            candidates = preferred_candidates
        
        return candidates
    
    def _generate_negotiation_explanation(
        self,
        optimal: MultiRailEvaluation,
        all_evaluations: List[MultiRailEvaluation],
        request: MultiRailNegotiationRequest
    ) -> str:
        """Generate comprehensive explanation of the negotiation result."""
        explanation_parts = []
        
        # Optimal choice explanation
        explanation_parts.append(f"Selected {optimal.rail_type} rail with {optimal.instrument_type} instrument")
        explanation_parts.append(f"with total score {optimal.total_score:.3f}")
        
        # Score breakdown
        explanation_parts.append(f"(Cost: {optimal.cost_score:.3f}, Speed: {optimal.speed_score:.3f}, "
                               f"Risk: {optimal.risk_score:.3f}, Availability: {optimal.availability_score:.3f})")
        
        # Cost and speed details
        explanation_parts.append(f"Effective cost: {optimal.effective_cost_bps:.1f} bps, "
                               f"Settlement time: {optimal.settlement_time_hours}h")
        
        # Alternative mention
        if len(all_evaluations) > 1:
            second_best = all_evaluations[1]
            explanation_parts.append(f"Alternative: {second_best.rail_type}/{second_best.instrument_type} "
                                   f"(score: {second_best.total_score:.3f})")
        
        # Context mention
        if request.require_real_time and optimal.is_real_time:
            explanation_parts.append("Selected real-time option as required")
        
        if request.cross_border and optimal.is_cross_border:
            explanation_parts.append("Selected cross-border capable option")
        
        return " ".join(explanation_parts) + "."
    
    def _calculate_negotiation_confidence(
        self,
        evaluations: List[MultiRailEvaluation],
        request: MultiRailNegotiationRequest
    ) -> float:
        """Calculate overall confidence in the negotiation result."""
        if not evaluations:
            return 0.0
        
        # Base confidence from optimal combination
        base_confidence = evaluations[0].confidence
        
        # Bonus for clear winner (score gap)
        if len(evaluations) > 1:
            score_gap = evaluations[0].total_score - evaluations[1].total_score
            gap_bonus = min(0.2, score_gap * 2)  # Up to 0.2 bonus for clear winner
            base_confidence += gap_bonus
        
        # Bonus for multiple good options
        good_options = len([e for e in evaluations if e.total_score > 0.7])
        if good_options > 1:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)


# Global instances
_capability_registry = None
_evaluator = None
_negotiation_engine = None


def get_capability_registry() -> MultiRailCapabilityRegistry:
    """Get global capability registry instance."""
    global _capability_registry
    if _capability_registry is None:
        _capability_registry = MultiRailCapabilityRegistry()
    return _capability_registry


def get_multi_rail_evaluator() -> MultiRailEvaluator:
    """Get global multi-rail evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = MultiRailEvaluator()
    return _evaluator


def get_multi_rail_negotiation_engine() -> MultiRailNegotiationEngine:
    """Get global multi-rail negotiation engine instance."""
    global _negotiation_engine
    if _negotiation_engine is None:
        _negotiation_engine = MultiRailNegotiationEngine()
    return _negotiation_engine
