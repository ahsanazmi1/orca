"""
CloudEvent emission for Orca Core Phase 3 & 4 - Negotiation & Payment Instructions

This module handles the emission of CloudEvents for rail negotiation explanations,
decision reasoning, payment instruction explanations, and counterfactual analysis
as part of the OCN Phase 3 & 4 negotiation and payment instruction system.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

try:
    from cloudevents.http import CloudEvent
    from cloudevents.conversion import to_json
    CLOUDEVENTS_AVAILABLE = True
except ImportError:
    CLOUDEVENTS_AVAILABLE = False
    # Fallback CloudEvent implementation
    class CloudEvent:
        def __init__(self, **kwargs):
            self.data = kwargs.get('data', {})
            self.attributes = {k: v for k, v in kwargs.items() if k != 'data'}
        
        def to_dict(self):
            return {
                **self.attributes,
                'data': self.data
            }

# Set up logging
logger = logging.getLogger(__name__)


def emit_negotiation_explanation_event(
    negotiation_response,
    trace_id: str,
    source: str = "https://orca.ocn.ai/negotiation"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for rail negotiation explanation.
    
    Args:
        negotiation_response: NegotiationResponse object
        trace_id: Transaction trace ID
        source: Event source URI
        
    Returns:
        Dictionary representation of the CloudEvent
    """
    # Generate event ID
    event_id = str(uuid4())
    
    # Create CloudEvent data payload
    event_data = {
        "trace_id": trace_id,
        "optimal_rail": negotiation_response.optimal_rail,
        "explanation": negotiation_response.explanation,
        "rail_evaluations": [
            {
                "rail_type": eval.rail_type,
                "cost_score": eval.cost_score,
                "speed_score": eval.speed_score,
                "risk_score": eval.risk_score,
                "composite_score": eval.composite_score,
                "base_cost": eval.base_cost,
                "settlement_days": eval.settlement_days,
                "ml_risk_score": eval.ml_risk_score,
                "cost_factors": eval.cost_factors,
                "speed_factors": eval.speed_factors,
                "risk_factors": eval.risk_factors,
            }
            for eval in negotiation_response.rail_evaluations
        ],
        "ml_model_used": negotiation_response.ml_model_used,
        "negotiation_metadata": negotiation_response.negotiation_metadata,
        "timestamp": negotiation_response.timestamp.isoformat(),
    }
    
    # Create CloudEvent attributes
    event_attributes = {
        "specversion": "1.0",
        "id": event_id,
        "source": source,
        "type": "ocn.orca.explanation.v1",
        "subject": f"txn_{trace_id.replace('-', '')[:16]}",
        "time": datetime.now().isoformat() + "Z",
        "datacontenttype": "application/json",
        "dataschema": "https://schemas.ocn.ai/events/v1/orca.explanation.v1.schema.json",
    }
    
    # Create CloudEvent
    if CLOUDEVENTS_AVAILABLE:
        event = CloudEvent(
            data=event_data,
            **event_attributes
        )
        event_dict = event.to_dict()
    else:
        # Fallback implementation
        event_dict = {
            **event_attributes,
            "data": event_data
        }
    
    # Log the event
    logger.info(
        f"Emitted negotiation explanation CloudEvent",
        extra={
            "event_id": event_id,
            "trace_id": trace_id,
            "optimal_rail": negotiation_response.optimal_rail,
            "event_type": "ocn.orca.explanation.v1"
        }
    )
    
    # Emit to configured destination (if any)
    emit_destination = os.getenv("ORCA_CLOUDEVENT_DESTINATION")
    if emit_destination:
        try:
            # In a real implementation, this would send to a message queue or HTTP endpoint
            logger.info(f"Event would be sent to: {emit_destination}")
            # For now, we'll just log the destination
        except Exception as e:
            logger.error(f"Failed to emit event to destination: {e}")
    
    return event_dict


def emit_rail_selection_event(
    rail_type: str,
    explanation: str,
    trace_id: str,
    ml_risk_score: float,
    composite_score: float,
    source: str = "https://orca.ocn.ai/negotiation"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for rail selection decision.
    
    Args:
        rail_type: Selected payment rail
        explanation: Explanation of selection
        trace_id: Transaction trace ID
        ml_risk_score: ML risk score used
        composite_score: Composite scoring result
        source: Event source URI
        
    Returns:
        Dictionary representation of the CloudEvent
    """
    # Generate event ID
    event_id = str(uuid4())
    
    # Create CloudEvent data payload
    event_data = {
        "trace_id": trace_id,
        "selected_rail": rail_type,
        "explanation": explanation,
        "ml_risk_score": ml_risk_score,
        "composite_score": composite_score,
        "timestamp": datetime.now().isoformat(),
        "decision_factors": {
            "cost_weight": 0.4,
            "speed_weight": 0.3,
            "risk_weight": 0.3,
        }
    }
    
    # Create CloudEvent attributes
    event_attributes = {
        "specversion": "1.0",
        "id": event_id,
        "source": source,
        "type": "ocn.orca.rail_selection.v1",
        "subject": f"txn_{trace_id.replace('-', '')[:16]}",
        "time": datetime.now().isoformat() + "Z",
        "datacontenttype": "application/json",
        "dataschema": "https://schemas.ocn.ai/events/v1/orca.rail_selection.v1.schema.json",
    }
    
    # Create CloudEvent
    if CLOUDEVENTS_AVAILABLE:
        event = CloudEvent(
            data=event_data,
            **event_attributes
        )
        event_dict = event.to_dict()
    else:
        # Fallback implementation
        event_dict = {
            **event_attributes,
            "data": event_data
        }
    
    # Log the event
    logger.info(
        f"Emitted rail selection CloudEvent",
        extra={
            "event_id": event_id,
            "trace_id": trace_id,
            "selected_rail": rail_type,
            "event_type": "ocn.orca.rail_selection.v1"
        }
    )
    
    return event_dict


def get_event_schema_validation(event_dict: Dict[str, Any]) -> bool:
    """
    Validate CloudEvent structure against CloudEvents specification.
    
    Args:
        event_dict: CloudEvent dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_attributes = [
        "specversion", "id", "source", "type", "subject", "time", "data"
    ]
    
    for attr in required_attributes:
        if attr not in event_dict:
            logger.error(f"Missing required CloudEvent attribute: {attr}")
            return False
    
    # Validate specversion
    if event_dict["specversion"] != "1.0":
        logger.error(f"Invalid specversion: {event_dict['specversion']}")
        return False
    
    # Validate type format
    event_type = event_dict["type"]
    if not event_type.startswith("ocn.orca."):
        logger.error(f"Invalid event type format: {event_type}")
        return False
    
    # Validate subject format
    subject = event_dict["subject"]
    if not subject.startswith("txn_"):
        logger.error(f"Invalid subject format: {subject}")
        return False
    
    logger.info("CloudEvent validation passed")
    return True


def emit_payment_explanation_event(
    payment_instruction,
    trace_id: str,
    source: str = "https://orca.ocn.ai/payment-instruction"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for payment instruction explanation.
    
    Args:
        payment_instruction: PaymentInstruction object
        trace_id: Transaction trace ID
        source: Event source URI
        
    Returns:
        Dict containing the CloudEvent data
    """
    if not CLOUDEVENTS_AVAILABLE:
        logger.warning("CloudEvents library not available, skipping event emission")
        return {}
    
    try:
        event_data = {
            "specversion": "1.0",
            "id": f"evt_payment_explanation_{uuid4().hex[:8]}",
            "source": source,
            "type": "ocn.orca.explanation.v1",
            "subject": trace_id,
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/vnd.ocn.ap2+json; version=1",
            "dataschema": "https://schemas.ocn.ai/events/v1/orca.explanation.v1.schema.json",
            "data": {
                "explanation_version": "0.1.0",
                "trace_id": trace_id,
                "instruction_id": payment_instruction.instruction_id,
                "explanation_type": "payment_instruction",
                "explanation_result": {
                    "selected_rail": payment_instruction.selected_rail,
                    "selected_processor": payment_instruction.selected_processor,
                    "selected_instrument": payment_instruction.selected_instrument,
                    "effective_cost": payment_instruction.effective_cost,
                    "settlement_time_hours": payment_instruction.settlement_time_hours,
                    "confidence": payment_instruction.confidence,
                    "explanation": payment_instruction.explanation,
                    "decision_factors": {
                        "cost_weight": 0.4,
                        "speed_weight": 0.3,
                        "risk_weight": 0.3,
                        "trust_score": payment_instruction.metadata.get("trust_score", 0.5),
                        "risk_level": payment_instruction.metadata.get("risk_level", "medium")
                    },
                    "constraints_applied": payment_instruction.constraints_applied
                },
                "metadata": payment_instruction.metadata
            }
        }
        
        # Create CloudEvent
        event = CloudEvent(**event_data)
        
        # Log the event
        logger.info(f"Emitting payment explanation event: {event_data['id']} for trace_id: {trace_id}")
        
        # In a real implementation, you would emit this to an event bus
        # For now, we'll just log it
        if os.getenv("OCN_EMIT_EVENTS", "false").lower() == "true":
            logger.info(f"Payment explanation event data: {json.dumps(event.to_dict(), indent=2)}")
        
        return event.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to emit payment explanation event: {e}")
        return {}


def emit_counterfactual_event(
    counterfactual_analysis,
    trace_id: str,
    source: str = "https://orca.ocn.ai/counterfactual"
) -> Dict[str, Any]:
    """
    Emit a CloudEvent for counterfactual analysis.
    
    Args:
        counterfactual_analysis: CounterfactualAnalysis object
        trace_id: Transaction trace ID
        source: Event source URI
        
    Returns:
        Dict containing the CloudEvent data
    """
    if not CLOUDEVENTS_AVAILABLE:
        logger.warning("CloudEvents library not available, skipping event emission")
        return {}
    
    try:
        event_data = {
            "specversion": "1.0",
            "id": f"evt_counterfactual_{uuid4().hex[:8]}",
            "source": source,
            "type": "ocn.orca.counterfactual.v1",
            "subject": trace_id,
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/vnd.ocn.ap2+json; version=1",
            "dataschema": "https://schemas.ocn.ai/events/v1/orca.counterfactual.v1.schema.json",
            "data": {
                "counterfactual_version": "0.1.0",
                "trace_id": trace_id,
                "original_instruction": {
                    "instruction_id": counterfactual_analysis.original_instruction.instruction_id,
                    "selected_rail": counterfactual_analysis.original_instruction.selected_rail,
                    "selected_processor": counterfactual_analysis.original_instruction.selected_processor,
                    "effective_cost": counterfactual_analysis.original_instruction.effective_cost,
                    "confidence": counterfactual_analysis.original_instruction.confidence
                },
                "alternatives": counterfactual_analysis.alternatives,
                "scenario_differences": counterfactual_analysis.scenario_differences,
                "sensitivity_analysis": counterfactual_analysis.sensitivity_analysis,
                "metadata": {
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "total_alternatives": len(counterfactual_analysis.alternatives),
                    "analysis_type": "payment_instruction_counterfactual"
                }
            }
        }
        
        # Create CloudEvent
        event = CloudEvent(**event_data)
        
        # Log the event
        logger.info(f"Emitting counterfactual event: {event_data['id']} for trace_id: {trace_id}")
        
        # In a real implementation, you would emit this to an event bus
        # For now, we'll just log it
        if os.getenv("OCN_EMIT_EVENTS", "false").lower() == "true":
            logger.info(f"Counterfactual event data: {json.dumps(event.to_dict(), indent=2)}")
        
        return event.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to emit counterfactual event: {e}")
        return {}

