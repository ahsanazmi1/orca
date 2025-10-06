"""
Learning Loop Implementation for Orca Phase 9.

Implements counterfactuals, reward functions, shadow mode, and ε-greedy bandit
with guardrails for continuous learning and optimization.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.orca_core.models import (
    PaymentInstruction, CounterfactualAnalysis, RailType, InstrumentType
)
from src.orca_core.events import (
    emit_payment_explanation_event,
    emit_counterfactual_event
)

logger = logging.getLogger(__name__)


class RewardFunction:
    """
    Reward function for learning loop optimization.
    
    Calculates rewards based on payment outcomes, costs, and performance metrics
    to guide the learning algorithm toward optimal payment path selection.
    """
    
    def __init__(self):
        """Initialize the reward function."""
        self.reward_weights = {
            "cost_efficiency": 0.4,      # 40% weight on cost optimization
            "settlement_speed": 0.2,     # 20% weight on speed
            "approval_rate": 0.2,        # 20% weight on success rate
            "customer_satisfaction": 0.1, # 10% weight on user experience
            "risk_mitigation": 0.1       # 10% weight on risk management
        }
        logger.info("Reward function initialized")
    
    def calculate_reward(
        self,
        payment_instruction: PaymentInstruction,
        outcome_data: Dict[str, Any],
        baseline_performance: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate reward for a payment instruction based on outcomes.
        
        Args:
            payment_instruction: The payment instruction that was executed
            outcome_data: Outcome data including costs, timing, success status
            baseline_performance: Baseline performance metrics for comparison
            
        Returns:
            Dictionary containing reward components and total reward
        """
        try:
            # Extract outcome metrics
            actual_cost = outcome_data.get("actual_cost", payment_instruction.effective_cost)
            settlement_time = outcome_data.get("settlement_time_hours", payment_instruction.settlement_time_hours)
            approval_status = outcome_data.get("approval_status", "approved")
            customer_rating = outcome_data.get("customer_rating", 0.5)
            risk_events = outcome_data.get("risk_events", 0)
            
            # Calculate individual reward components
            cost_reward = self._calculate_cost_reward(actual_cost, baseline_performance)
            speed_reward = self._calculate_speed_reward(settlement_time, baseline_performance)
            approval_reward = self._calculate_approval_reward(approval_status)
            satisfaction_reward = self._calculate_satisfaction_reward(customer_rating)
            risk_reward = self._calculate_risk_reward(risk_events, baseline_performance)
            
            # Calculate weighted total reward
            total_reward = (
                cost_reward * self.reward_weights["cost_efficiency"] +
                speed_reward * self.reward_weights["settlement_speed"] +
                approval_reward * self.reward_weights["approval_rate"] +
                satisfaction_reward * self.reward_weights["customer_satisfaction"] +
                risk_reward * self.reward_weights["risk_mitigation"]
            )
            
            reward_data = {
                "total_reward": total_reward,
                "components": {
                    "cost_efficiency": cost_reward,
                    "settlement_speed": speed_reward,
                    "approval_rate": approval_reward,
                    "customer_satisfaction": satisfaction_reward,
                    "risk_mitigation": risk_reward
                },
                "weights": self.reward_weights,
                "outcome_data": outcome_data,
                "payment_instruction": payment_instruction.dict(),
                "calculated_at": datetime.now().isoformat()
            }
            
            logger.debug(f"Calculated reward {total_reward:.3f} for instruction {payment_instruction.instruction_id}")
            return reward_data
            
        except Exception as e:
            logger.error(f"Failed to calculate reward: {str(e)}")
            return {
                "total_reward": 0.0,
                "error": str(e),
                "calculated_at": datetime.now().isoformat()
            }
    
    def _calculate_cost_reward(self, actual_cost: float, baseline: Optional[Dict[str, Any]]) -> float:
        """Calculate cost efficiency reward component."""
        if not baseline or "avg_cost" not in baseline:
            # Default reward based on absolute cost
            return max(0.0, 1.0 - (actual_cost / 1000.0))  # Normalize to $1000 max
        
        avg_cost = baseline["avg_cost"]
        if avg_cost <= 0:
            return 0.5
        
        # Reward for cost below baseline, penalize for above
        cost_ratio = actual_cost / avg_cost
        if cost_ratio <= 0.8:  # 20% better than baseline
            return 1.0
        elif cost_ratio <= 1.0:  # At or better than baseline
            return 0.8
        elif cost_ratio <= 1.2:  # 20% worse than baseline
            return 0.4
        else:  # Much worse than baseline
            return 0.0
    
    def _calculate_speed_reward(self, settlement_time: float, baseline: Optional[Dict[str, Any]]) -> float:
        """Calculate settlement speed reward component."""
        if not baseline or "avg_settlement_time" not in baseline:
            # Default reward based on absolute time
            return max(0.0, 1.0 - (settlement_time / 168.0))  # Normalize to 1 week max
        
        avg_time = baseline["avg_settlement_time"]
        if avg_time <= 0:
            return 0.5
        
        # Reward for faster settlement than baseline
        time_ratio = settlement_time / avg_time
        if time_ratio <= 0.5:  # 50% faster than baseline
            return 1.0
        elif time_ratio <= 0.8:  # 20% faster than baseline
            return 0.8
        elif time_ratio <= 1.0:  # At or faster than baseline
            return 0.6
        elif time_ratio <= 1.5:  # 50% slower than baseline
            return 0.3
        else:  # Much slower than baseline
            return 0.0
    
    def _calculate_approval_reward(self, approval_status: str) -> float:
        """Calculate approval rate reward component."""
        if approval_status == "approved":
            return 1.0
        elif approval_status == "declined":
            return 0.0
        elif approval_status == "pending":
            return 0.5
        else:
            return 0.0
    
    def _calculate_satisfaction_reward(self, customer_rating: float) -> float:
        """Calculate customer satisfaction reward component."""
        # Normalize rating to 0-1 scale
        normalized_rating = max(0.0, min(1.0, customer_rating))
        return normalized_rating
    
    def _calculate_risk_reward(self, risk_events: int, baseline: Optional[Dict[str, Any]]) -> float:
        """Calculate risk mitigation reward component."""
        if risk_events == 0:
            return 1.0  # No risk events = perfect reward
        
        # Penalize based on number of risk events
        if risk_events == 1:
            return 0.7
        elif risk_events <= 3:
            return 0.4
        else:
            return 0.0


class CounterfactualGenerator:
    """
    Generates counterfactual analysis for learning loop.
    
    Creates alternative scenarios to understand what would have happened
    with different payment path selections, enabling learning from
    unexplored options.
    """
    
    def __init__(self):
        """Initialize the counterfactual generator."""
        self.alternative_rails = ["ACH", "Card", "RTP", "FedNow", "SEPA", "Crypto"]
        self.alternative_instruments = ["credit_card", "debit_card", "bank_transfer", "stablecoin"]
        logger.info("Counterfactual generator initialized")
    
    def generate_counterfactuals(
        self,
        original_instruction: PaymentInstruction,
        available_alternatives: List[Dict[str, Any]],
        max_alternatives: int = 5
    ) -> CounterfactualAnalysis:
        """
        Generate counterfactual analysis for a payment instruction.
        
        Args:
            original_instruction: The original payment instruction
            available_alternatives: List of alternative payment options
            max_alternatives: Maximum number of alternatives to generate
            
        Returns:
            CounterfactualAnalysis with alternative scenarios
        """
        try:
            # Select top alternatives
            selected_alternatives = self._select_top_alternatives(
                available_alternatives, max_alternatives
            )
            
            # Generate scenario differences
            scenario_differences = self._calculate_scenario_differences(
                original_instruction, selected_alternatives
            )
            
            # Perform sensitivity analysis
            sensitivity_analysis = self._perform_sensitivity_analysis(
                original_instruction, selected_alternatives
            )
            
            counterfactual = CounterfactualAnalysis(
                trace_id=original_instruction.trace_id,
                original_instruction=original_instruction,
                alternatives=selected_alternatives,
                scenario_differences=scenario_differences,
                sensitivity_analysis=sensitivity_analysis
            )
            
            logger.info(f"Generated {len(selected_alternatives)} counterfactuals for trace {original_instruction.trace_id}")
            return counterfactual
            
        except Exception as e:
            logger.error(f"Failed to generate counterfactuals: {str(e)}")
            # Return minimal counterfactual on error
            return CounterfactualAnalysis(
                trace_id=original_instruction.trace_id,
                original_instruction=original_instruction,
                alternatives=[],
                scenario_differences=[],
                sensitivity_analysis={"error": str(e)}
            )
    
    def _select_top_alternatives(
        self,
        alternatives: List[Dict[str, Any]],
        max_count: int
    ) -> List[Dict[str, Any]]:
        """Select top alternatives based on scoring."""
        # Sort by score (if available) or cost
        sorted_alternatives = sorted(
            alternatives,
            key=lambda alt: alt.get("score", 1.0 - alt.get("cost_bps", 100) / 1000.0),
            reverse=True
        )
        
        return sorted_alternatives[:max_count]
    
    def _calculate_scenario_differences(
        self,
        original: PaymentInstruction,
        alternatives: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate differences between original and alternative scenarios."""
        differences = []
        
        for alt in alternatives:
            diff = {
                "alternative_id": alt.get("id", str(uuid.uuid4())),
                "rail_difference": alt.get("rail_type") != original.selected_rail,
                "instrument_difference": alt.get("instrument_type") != original.selected_instrument,
                "cost_difference": alt.get("cost_bps", 0) - (original.effective_cost * 10000 / original.amount if original.amount > 0 else 0),
                "settlement_time_difference": alt.get("settlement_days", 1) - (original.settlement_time_hours / 24),
                "risk_difference": alt.get("risk_score", 0.5) - 0.5,  # Assume original risk is 0.5
                "expected_reward_difference": alt.get("expected_reward", 0.5) - 0.5
            }
            differences.append(diff)
        
        return differences
    
    def _perform_sensitivity_analysis(
        self,
        original: PaymentInstruction,
        alternatives: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis on key parameters."""
        return {
            "cost_sensitivity": {
                "original_cost": original.effective_cost,
                "cost_range": [
                    min(alt.get("cost_bps", 0) * original.amount / 10000 for alt in alternatives),
                    max(alt.get("cost_bps", 0) * original.amount / 10000 for alt in alternatives)
                ],
                "cost_variance": np.var([alt.get("cost_bps", 0) for alt in alternatives]) if alternatives else 0
            },
            "speed_sensitivity": {
                "original_time": original.settlement_time_hours,
                "time_range": [
                    min(alt.get("settlement_days", 1) * 24 for alt in alternatives),
                    max(alt.get("settlement_days", 1) * 24 for alt in alternatives)
                ],
                "time_variance": np.var([alt.get("settlement_days", 1) * 24 for alt in alternatives]) if alternatives else 0
            },
            "risk_sensitivity": {
                "original_risk": 0.5,  # Assume original risk
                "risk_range": [
                    min(alt.get("risk_score", 0.5) for alt in alternatives),
                    max(alt.get("risk_score", 0.5) for alt in alternatives)
                ],
                "risk_variance": np.var([alt.get("risk_score", 0.5) for alt in alternatives]) if alternatives else 0
            }
        }


class EpsilonGreedyBandit:
    """
    ε-greedy bandit algorithm for exploration vs exploitation.
    
    Balances exploration of new payment paths with exploitation of
    known good paths, with guardrails to prevent risky decisions.
    """
    
    def __init__(self, epsilon: float = 0.1, min_samples: int = 10):
        """
        Initialize ε-greedy bandit.
        
        Args:
            epsilon: Exploration rate (0.0 = pure exploitation, 1.0 = pure exploration)
            min_samples: Minimum samples before considering a path "known"
        """
        self.epsilon = epsilon
        self.min_samples = min_samples
        self.action_values = {}  # Track average rewards for each action
        self.action_counts = {}  # Track number of times each action was taken
        self.guardrails = {
            "max_risk_threshold": 0.8,
            "min_approval_rate": 0.85,
            "max_cost_increase": 0.5  # 50% cost increase threshold
        }
        logger.info(f"ε-greedy bandit initialized with epsilon={epsilon}")
    
    def select_action(
        self,
        available_actions: List[Dict[str, Any]],
        shadow_mode: bool = True
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Select action using ε-greedy strategy with guardrails.
        
        Args:
            available_actions: List of available payment actions/paths
            shadow_mode: Whether to run in shadow mode (no real impact)
            
        Returns:
            Tuple of (selected_action, selection_metadata)
        """
        try:
            if not available_actions:
                raise ValueError("No available actions provided")
            
            # Apply guardrails to filter safe actions
            safe_actions = self._apply_guardrails(available_actions)
            
            if not safe_actions:
                logger.warning("No safe actions after applying guardrails, falling back to original actions")
                safe_actions = available_actions
            
            # Select action based on ε-greedy strategy
            if shadow_mode or random.random() < self.epsilon:
                # Exploration: select random action
                selected_action = random.choice(safe_actions)
                selection_strategy = "exploration"
            else:
                # Exploitation: select best known action
                selected_action = self._select_best_known_action(safe_actions)
                selection_strategy = "exploitation"
            
            # Update action statistics
            action_id = self._get_action_id(selected_action)
            self.action_counts[action_id] = self.action_counts.get(action_id, 0) + 1
            
            selection_metadata = {
                "selection_strategy": selection_strategy,
                "epsilon": self.epsilon,
                "action_id": action_id,
                "action_count": self.action_counts[action_id],
                "shadow_mode": shadow_mode,
                "guardrails_applied": len(safe_actions) < len(available_actions),
                "safe_actions_count": len(safe_actions),
                "total_actions_count": len(available_actions)
            }
            
            logger.debug(f"Selected action using {selection_strategy} strategy")
            return selected_action, selection_metadata
            
        except Exception as e:
            logger.error(f"Failed to select action: {str(e)}")
            # Fallback to first available action
            return available_actions[0], {"error": str(e), "fallback": True}
    
    def update_action_reward(self, action: Dict[str, Any], reward: float) -> None:
        """
        Update the estimated value of an action based on observed reward.
        
        Args:
            action: The action that was taken
            reward: The observed reward for this action
        """
        try:
            action_id = self._get_action_id(action)
            
            # Update action value using incremental average
            if action_id in self.action_values:
                current_count = self.action_counts[action_id]
                current_value = self.action_values[action_id]
                new_value = (current_value * current_count + reward) / (current_count + 1)
                self.action_values[action_id] = new_value
            else:
                self.action_values[action_id] = reward
            
            logger.debug(f"Updated action {action_id} reward to {self.action_values[action_id]:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to update action reward: {str(e)}")
    
    def _apply_guardrails(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply guardrails to filter out risky actions."""
        safe_actions = []
        
        for action in actions:
            is_safe = True
            
            # Check risk threshold
            risk_score = action.get("risk_score", 0.5)
            if risk_score > self.guardrails["max_risk_threshold"]:
                is_safe = False
                logger.debug(f"Action filtered out due to high risk: {risk_score}")
            
            # Check approval rate (if available)
            approval_rate = action.get("approval_rate", 1.0)
            if approval_rate < self.guardrails["min_approval_rate"]:
                is_safe = False
                logger.debug(f"Action filtered out due to low approval rate: {approval_rate}")
            
            # Check cost increase (if baseline available)
            cost_bps = action.get("cost_bps", 100)
            baseline_cost = action.get("baseline_cost_bps", 100)
            if cost_bps > baseline_cost * (1 + self.guardrails["max_cost_increase"]):
                is_safe = False
                logger.debug(f"Action filtered out due to high cost: {cost_bps} vs {baseline_cost}")
            
            if is_safe:
                safe_actions.append(action)
        
        return safe_actions
    
    def _select_best_known_action(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the action with the highest estimated value."""
        best_action = None
        best_value = float('-inf')
        
        for action in actions:
            action_id = self._get_action_id(action)
            action_value = self.action_values.get(action_id, 0.0)
            
            # Add small random tie-breaker
            action_value += random.random() * 0.001
            
            if action_value > best_value:
                best_value = action_value
                best_action = action
        
        return best_action or actions[0]  # Fallback to first action
    
    def _get_action_id(self, action: Dict[str, Any]) -> str:
        """Generate unique ID for an action."""
        rail_type = action.get("rail_type", "unknown")
        instrument_type = action.get("instrument_type", "unknown")
        processor_id = action.get("processor_id", "unknown")
        return f"{rail_type}_{instrument_type}_{processor_id}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current bandit statistics."""
        return {
            "epsilon": self.epsilon,
            "min_samples": self.min_samples,
            "total_actions": len(self.action_values),
            "action_values": self.action_values.copy(),
            "action_counts": self.action_counts.copy(),
            "guardrails": self.guardrails.copy()
        }


class LearningLoopOrchestrator:
    """
    Orchestrates the complete learning loop for Orca.
    
    Coordinates counterfactuals, rewards, bandit selection, and learning
    to continuously optimize payment path selection.
    """
    
    def __init__(self):
        """Initialize the learning loop orchestrator."""
        self.reward_function = RewardFunction()
        self.counterfactual_generator = CounterfactualGenerator()
        self.bandit = EpsilonGreedyBandit()
        self.baseline_performance = self._initialize_baseline()
        logger.info("Learning loop orchestrator initialized")
    
    def process_payment_with_learning(
        self,
        payment_instruction: PaymentInstruction,
        available_alternatives: List[Dict[str, Any]],
        shadow_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Process payment with learning loop integration.
        
        Args:
            payment_instruction: The payment instruction to process
            available_alternatives: Available alternative payment paths
            shadow_mode: Whether to run in shadow mode
            
        Returns:
            Dictionary containing learning results and metadata
        """
        try:
            # Generate counterfactuals
            counterfactuals = self.counterfactual_generator.generate_counterfactuals(
                payment_instruction, available_alternatives
            )
            
            # Emit counterfactual event
            emit_counterfactual_event(counterfactuals, payment_instruction.trace_id)
            
            # Select action using bandit (if not shadow mode)
            if not shadow_mode:
                selected_action, selection_metadata = self.bandit.select_action(
                    available_alternatives, shadow_mode=False
                )
            else:
                selected_action = None
                selection_metadata = {"shadow_mode": True}
            
            # Prepare learning result
            learning_result = {
                "trace_id": payment_instruction.trace_id,
                "instruction_id": payment_instruction.instruction_id,
                "counterfactuals": counterfactuals.dict(),
                "selected_action": selected_action,
                "selection_metadata": selection_metadata,
                "shadow_mode": shadow_mode,
                "baseline_performance": self.baseline_performance,
                "bandit_statistics": self.bandit.get_statistics(),
                "processed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Processed payment with learning for trace {payment_instruction.trace_id}")
            return learning_result
            
        except Exception as e:
            logger.error(f"Failed to process payment with learning: {str(e)}")
            return {
                "trace_id": payment_instruction.trace_id,
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    def update_with_outcome(
        self,
        trace_id: str,
        outcome_data: Dict[str, Any],
        payment_instruction: Optional[PaymentInstruction] = None
    ) -> Dict[str, Any]:
        """
        Update learning with payment outcome data.
        
        Args:
            trace_id: Transaction trace ID
            outcome_data: Outcome data from payment processing
            payment_instruction: Original payment instruction (if available)
            
        Returns:
            Dictionary containing update results
        """
        try:
            # Calculate reward if payment instruction is available
            reward_data = None
            if payment_instruction:
                reward_data = self.reward_function.calculate_reward(
                    payment_instruction, outcome_data, self.baseline_performance
                )
                
                # Update bandit with reward
                # Extract action information from outcome
                action_info = {
                    "rail_type": outcome_data.get("rail_type", payment_instruction.selected_rail),
                    "instrument_type": outcome_data.get("instrument_type", payment_instruction.selected_instrument),
                    "processor_id": outcome_data.get("processor_id", payment_instruction.selected_processor)
                }
                self.bandit.update_action_reward(action_info, reward_data["total_reward"])
            
            update_result = {
                "trace_id": trace_id,
                "reward_data": reward_data,
                "outcome_data": outcome_data,
                "updated_at": datetime.now().isoformat(),
                "bandit_statistics": self.bandit.get_statistics()
            }
            
            logger.info(f"Updated learning with outcome for trace {trace_id}")
            return update_result
            
        except Exception as e:
            logger.error(f"Failed to update with outcome: {str(e)}")
            return {
                "trace_id": trace_id,
                "error": str(e),
                "updated_at": datetime.now().isoformat()
            }
    
    def _initialize_baseline(self) -> Dict[str, Any]:
        """Initialize baseline performance metrics."""
        return {
            "avg_cost": 25.0,  # $25 average cost
            "avg_settlement_time": 24.0,  # 24 hours average
            "avg_approval_rate": 0.95,  # 95% approval rate
            "avg_customer_rating": 0.8,  # 4/5 customer rating
            "avg_risk_events": 0.1  # 0.1 risk events per transaction
        }


# Global instance
_learning_loop = None


def get_learning_loop() -> LearningLoopOrchestrator:
    """Get global learning loop orchestrator instance."""
    global _learning_loop
    if _learning_loop is None:
        _learning_loop = LearningLoopOrchestrator()
    return _learning_loop








