"""
MCP (Model Context Protocol) server implementation for Orca.
"""

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

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
        else:
            return MCPResponse(ok=False, error=f"Unsupported verb: {request.verb}")
    except Exception as e:
        return MCPResponse(ok=False, error=str(e))
