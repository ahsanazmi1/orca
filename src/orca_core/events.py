"""
CloudEvent emission for Orca Core Phase 3 - Negotiation & Live Fee Bidding

This module handles the emission of CloudEvents for rail negotiation explanations
and decision reasoning as part of the OCN Phase 3 negotiation system.
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
