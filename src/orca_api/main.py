"""FastAPI service for Orca Core decision engine."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field, ValidationError

from orca_core.engine import evaluate_rules
from orca_core.explanations import generate_human_explanation
from orca_core.models import DecisionRequest, DecisionResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with orjson response class
app = FastAPI(
    title="Orca Core API",
    description="FastAPI service for the Orca Core decision engine",
    version="0.1.0",
    default_response_class=ORJSONResponse,
)


# Pydantic models for API requests/responses
class HealthResponse(BaseModel):
    """Health check response model."""

    ok: bool = Field(True, description="Service health status")


class ExplainRequest(BaseModel):
    """Request model for explanation endpoint."""

    decision: DecisionResponse = Field(..., description="Decision response to explain")


class ExplainResponse(BaseModel):
    """Response model for explanation endpoint."""

    explanation: str = Field(..., description="Plain-English explanation of the decision")


@app.get("/healthz", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(ok=True)


@app.post("/decision", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest) -> DecisionResponse:
    """
    Evaluate a decision request using the Orca Core engine.

    Args:
        request: Decision request with cart details and context

    Returns:
        DecisionResponse: Decision result with reasons and actions

    Raises:
        HTTPException: If request validation or processing fails
    """
    try:
        logger.info(f"Processing decision request for cart_total=${request.cart_total}")

        # Evaluate rules using the core engine
        response = evaluate_rules(request)

        logger.info(f"Decision made: {response.decision} (status: {response.status})")
        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=f"Validation error: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error processing decision: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


@app.post("/explain", response_model=ExplainResponse)
async def explain_decision(request: ExplainRequest) -> ExplainResponse:
    """
    Generate a plain-English explanation for a decision.

    Args:
        request: Decision response to explain

    Returns:
        ExplainResponse: Plain-English explanation

    Raises:
        HTTPException: If explanation generation fails
    """
    try:
        decision = request.decision

        # Use the existing explanation system
        if decision.explanation_human:
            explanation = decision.explanation_human
        elif decision.explanation:
            explanation = decision.explanation
        else:
            # Fallback to generating explanation from reasons
            explanation = generate_human_explanation(
                decision.reasons,
                decision.status or decision.decision,
                decision.meta.get("context", {}),
            )

        logger.info(f"Generated explanation for decision: {decision.decision}")
        return ExplainResponse(explanation=explanation)

    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate explanation: {str(e)}"
        ) from e


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Any, exc: ValidationError) -> ORJSONResponse:
    """Handle Pydantic validation errors."""
    return ORJSONResponse(status_code=422, content={"detail": f"Validation error: {exc}"})


@app.exception_handler(Exception)
async def general_exception_handler(request: Any, exc: Exception) -> ORJSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return ORJSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)  # nosec B104
