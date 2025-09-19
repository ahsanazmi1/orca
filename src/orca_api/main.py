"""FastAPI service for Orca Core decision engine."""

import logging
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field, ValidationError

from src.orca_core.config import get_settings
from src.orca_core.engine import evaluate_rules
from src.orca_core.explanations import generate_human_explanation
from src.orca_core.llm.explain import get_llm_explainer, is_llm_configured
from src.orca_core.models import DecisionRequest, DecisionResponse

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
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field("0.1.0", description="Service version")
    environment: str = Field("production", description="Environment")


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    ready: bool = Field(True, description="Service readiness status")
    timestamp: str = Field(..., description="Current timestamp")
    checks: dict = Field(..., description="Individual component checks")
    overall_status: str = Field(..., description="Overall readiness status")


class ExplainRequest(BaseModel):
    """Request model for explanation endpoint."""

    decision: DecisionResponse = Field(..., description="Decision response to explain")


class ExplainResponse(BaseModel):
    """Response model for explanation endpoint."""

    explanation: str = Field(..., description="Plain-English explanation of the decision")


@app.get("/healthz", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for Kubernetes liveness probe.

    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(
        ok=True,
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "production"),
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint (alternative path).

    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(
        ok=True,
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "production"),
    )


@app.get("/readyz", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint for Kubernetes readiness probe.

    Returns:
        ReadinessResponse: Service readiness status with component checks
    """
    checks = {}
    overall_ready = True

    # Check configuration
    try:
        settings = get_settings()
        checks["configuration"] = {
            "status": "ok",
            "decision_mode": settings.decision_mode.value,
            "use_xgb": settings.use_xgb,
            "explain_enabled": settings.is_ai_enabled,
        }
    except Exception as e:
        checks["configuration"] = {"status": "error", "error": str(e)}
        overall_ready = False

    # Check ML model availability
    try:
        from orca_core.ml.model import predict_risk

        # Test with dummy data
        test_features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0}
        result = predict_risk(test_features)
        checks["ml_model"] = {
            "status": "ok",
            "model_type": result.get("model_type", "unknown"),
            "version": result.get("version", "unknown"),
        }
    except Exception as e:
        checks["ml_model"] = {"status": "error", "error": str(e)}
        overall_ready = False

    # Check LLM service
    try:
        llm_explainer = get_llm_explainer()
        if llm_explainer.is_configured():
            checks["llm_service"] = {"status": "ok", "configured": True}
        else:
            checks["llm_service"] = {
                "status": "warning",
                "configured": False,
                "message": "LLM service not configured, will use fallback explanations",
            }
    except Exception as e:
        checks["llm_service"] = {"status": "error", "error": str(e)}
        # LLM service failure shouldn't make the service unready
        overall_ready = True

    # Check model artifacts
    model_dir = os.getenv("ORCA_MODEL_DIR", "/app/models/xgb")
    if os.path.exists(model_dir):
        model_files = os.listdir(model_dir)
        checks["model_artifacts"] = {
            "status": "ok",
            "model_dir": model_dir,
            "files": str(model_files),
        }
    else:
        checks["model_artifacts"] = {
            "status": "warning",
            "model_dir": model_dir,
            "message": "Model directory not found, will use stub model",
        }
        # Missing model artifacts shouldn't make the service unready

    # Determine overall status
    if overall_ready:
        overall_status = "ready"
    else:
        overall_status = "not_ready"

    return ReadinessResponse(
        ready=overall_ready,
        timestamp=datetime.utcnow().isoformat(),
        checks=checks,
        overall_status=overall_status,
    )


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

        # Check if LLM explanation is available
        if is_llm_configured():
            # Try LLM explanation first
            llm_explainer = get_llm_explainer()
            llm_response = llm_explainer.explain_decision(
                decision=decision.decision,
                risk_score=decision.meta.get("ai", {}).get("risk_score", 0.0),
                reason_codes=decision.meta.get("ai", {}).get("reason_codes", []),
                transaction_data={
                    "amount": decision.meta.get("context", {}).get("cart_total", 0),
                    "currency": decision.meta.get("context", {}).get("currency", "USD"),
                    "rail": decision.meta.get("context", {}).get("rail", "Card"),
                    "channel": decision.meta.get("context", {}).get("channel", "online"),
                },
                model_type=decision.meta.get("ai", {}).get("model_type", "unknown"),
                model_version=decision.meta.get("ai", {}).get("version", "unknown"),
                rules_evaluated=decision.reasons,
                meta_data=decision.meta,
            )

            if (
                llm_response
                and llm_response.model_provenance.get("status") != "503_service_unavailable"
            ):
                logger.info(f"Generated LLM explanation for decision: {decision.decision}")
                return ExplainResponse(explanation=llm_response.explanation)
            else:
                # LLM returned 503, fall back to traditional explanation
                logger.warning(
                    "LLM explanation unavailable, falling back to traditional explanation"
                )
        else:
            logger.info("LLM not configured, using traditional explanation")

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
