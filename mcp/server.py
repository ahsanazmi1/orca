"""
MCP (Model Context Protocol) server implementation for Orca.
"""

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import sys
import os

# Add the src directory to the path to import Orca modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from orca_core.engine import determine_optimal_rail
    from orca_core.models import NegotiationRequest, NegotiationResponse
    ORCA_CORE_AVAILABLE = True
except ImportError:
    ORCA_CORE_AVAILABLE = False

router = APIRouter()


class MCPRequest(BaseModel):
    """MCP request model."""

    verb: str
    args: Dict[str, Any] = {}


class MCPResponse(BaseModel):
    """MCP response model."""

    ok: bool
    data: Any = None
    error: str = None


@router.post("/mcp/invoke")
async def invoke_mcp(request: MCPRequest) -> MCPResponse:
    """
    Handle MCP protocol requests.

    Supported verbs:
    - getStatus: Returns agent status
    - getDecisionSchema: Returns AP2 decision schema information
    - negotiateCheckout: Performs rail negotiation for checkout
    """
    try:
        if request.verb == "getStatus":
            return MCPResponse(ok=True, data={"agent": "orca", "status": "active"})
        elif request.verb == "getDecisionSchema":
            return MCPResponse(
                ok=True,
                data={
                    "agent": "orca",
                    "schema_url": "https://github.com/ocn-ai/orca/blob/main/docs/contract.md",
                    "schema_version": "ap2.v1",
                    "description": "AP2 decision schema for Orca checkout agent",
                },
            )
        elif request.verb == "negotiateCheckout":
            if not ORCA_CORE_AVAILABLE:
                return MCPResponse(ok=False, error="Orca core modules not available")
            
            # Extract negotiation parameters
            cart_total = request.args.get("cart_total", 100.0)
            currency = request.args.get("currency", "USD")
            channel = request.args.get("channel", "online")
            available_rails = request.args.get("available_rails", ["ACH", "Debit", "Credit"])
            features = request.args.get("features", {})
            context = request.args.get("context", {})
            deterministic_seed = request.args.get("deterministic_seed", 42)
            
            # Create negotiation request
            negotiation_request = NegotiationRequest(
                amount=cart_total,
                currency=currency,
                merchant_id=context.get("merchant_id", "demo_merchant_001"),
                channel=channel,
                available_rails=available_rails,
                customer_context={**context, "deterministic_seed": deterministic_seed},
                preferences=features,
                trace_id=f"mcp_trace_{deterministic_seed}"
            )
            
            # Perform negotiation
            negotiation_response = determine_optimal_rail(negotiation_request)
            
            # Format response for MCP
            mcp_data = {
                "chosen_rail": negotiation_response.optimal_rail,
                "candidate_scores": [
                    {
                        "rail_type": eval.rail_type,
                        "cost_score": eval.cost_score,
                        "speed_score": eval.speed_score,
                        "risk_score": eval.risk_score,
                        "composite_score": eval.composite_score,
                        "base_cost": eval.base_cost,
                        "settlement_days": eval.settlement_days,
                        "ml_risk_score": eval.ml_risk_score,
                    }
                    for eval in negotiation_response.rail_evaluations
                ],
                "rationale": negotiation_response.explanation,
                "trace_id": negotiation_response.trace_id,
                "timestamp": datetime.now().isoformat(),
                "ml_model_used": "orca_negotiation_v1",
                "negotiation_metadata": negotiation_response.negotiation_metadata,
            }
            
            return MCPResponse(ok=True, data=mcp_data)
        else:
            return MCPResponse(ok=False, error=f"Unsupported verb: {request.verb}")
    except Exception as e:
        return MCPResponse(ok=False, error=str(e))
