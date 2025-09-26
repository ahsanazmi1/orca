"""FastAPI service for Orca Core decision engine."""

import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse, HTMLResponse

try:
    from ocn_common.trace import trace_middleware
except ImportError:
    # Fallback when ocn-common is not available
    def trace_middleware(app):
        return app


from pydantic import BaseModel, Field, ValidationError

from src.orca.logging_setup import get_traced_logger, setup_logging
from src.orca_core.config import get_settings
from src.orca_core.engine import evaluate_rules
from src.orca_core.explanations import generate_human_explanation
from src.orca_core.llm.explain import get_llm_explainer, is_llm_configured
from src.orca_core.models import DecisionRequest, DecisionResponse
from mcp import router as mcp_router

# Set up structured logging with redaction
setup_logging(level="INFO", format_type="json")
logger = get_traced_logger(__name__)

# Create FastAPI app with orjson response class
app = FastAPI(
    title="Orca Core API",
    description="FastAPI service for the Orca Core decision engine",
    version="0.1.0",
    default_response_class=ORJSONResponse,
)

# Add trace middleware for automatic trace ID propagation
app = trace_middleware(app)

# Include MCP router
app.include_router(mcp_router)


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


@app.get("/demo", response_class=HTMLResponse)
async def web_demo():
    """Serve the web demo interface."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐋 Orca AI Decision Engine Demo</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        .card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e1e5e9;
            border-radius: 5px;
            font-size: 14px;
            box-sizing: border-box;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: background 0.3s;
        }
        button:hover {
            background: #5a67d8;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .status-card {
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            background: #f8f9fa;
        }
        .status-healthy {
            background: #d4edda;
            color: #155724;
        }
        .status-error {
            background: #f8d7da;
            color: #721c24;
        }
        .links {
            margin-top: 30px;
            text-align: center;
        }
        .links a {
            color: #667eea;
            text-decoration: none;
            margin: 0 15px;
            font-weight: 600;
        }
        .links a:hover {
            text-decoration: underline;
        }
        pre {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐋 Orca AI Decision Engine Demo</h1>
        <p style="text-align: center; color: #666; margin-bottom: 30px;">
            Open Checkout Network - AI Explainability Demo
        </p>

        <div class="grid">
            <div class="card">
                <h3>📊 Test Decision</h3>
                <form id="decisionForm">
                    <div class="form-group">
                        <label for="amount">Transaction Amount</label>
                        <input type="number" id="amount" value="125.50" step="0.01" min="0">
                    </div>
                    <div class="form-group">
                        <label for="traceId">Trace ID</label>
                        <input type="text" id="traceId" value="demo-trace-001">
                    </div>
                    <div class="form-group">
                        <label for="riskTier">Risk Tier</label>
                        <select id="riskTier">
                            <option value="low">Low</option>
                            <option value="medium" selected>Medium</option>
                            <option value="high">High</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="channel">Channel</label>
                        <select id="channel">
                            <option value="ecommerce" selected>E-commerce</option>
                            <option value="pos">POS</option>
                            <option value="mobile">Mobile</option>
                            <option value="atm">ATM</option>
                        </select>
                    </div>
                    <button type="submit">🚀 Make Decision</button>
                </form>

                <div id="result" class="result"></div>
            </div>

            <div class="card">
                <h3>🎯 System Status</h3>
                <div class="status-grid">
                    <div class="status-card" id="orcaStatus">
                        <h4>🐋 Orca</h4>
                        <p>Checking...</p>
                    </div>
                    <div class="status-card" id="orionStatus">
                        <h4>🚀 Orion</h4>
                        <p>Checking...</p>
                    </div>
                    <div class="status-card" id="weaveStatus">
                        <h4>🌊 Weave</h4>
                        <p>Checking...</p>
                    </div>
                </div>

                <h4 style="margin-top: 20px;">📈 Recent Demo Data</h4>
                <pre id="demoData">Loading demo data...</pre>
            </div>
        </div>

        <div class="links">
            <a href="http://localhost:8081/docs" target="_blank">🚀 Orion API Docs</a>
            <a href="http://localhost:8082/docs" target="_blank">🌊 Weave API Docs</a>
            <a href="http://localhost:8080/health" target="_blank">🐋 Orca Health</a>
        </div>
    </div>

    <script>
        // Check system status
        async function checkStatus() {
            const services = [
                { name: 'orca', url: 'http://localhost:8080/health', element: 'orcaStatus' },
                { name: 'orion', url: 'http://localhost:8081/health', element: 'orionStatus' },
                { name: 'weave', url: 'http://localhost:8082/health', element: 'weaveStatus' }
            ];

            for (const service of services) {
                try {
                    const response = await fetch(service.url);
                    const element = document.getElementById(service.element);
                    if (response.ok) {
                        element.className = 'status-card status-healthy';
                        element.querySelector('p').textContent = '✅ Healthy';
                    } else {
                        element.className = 'status-card status-error';
                        element.querySelector('p').textContent = '❌ Error';
                    }
                } catch (error) {
                    const element = document.getElementById(service.element);
                    element.className = 'status-card status-error';
                    element.querySelector('p').textContent = '❌ Offline';
                }
            }
        }

        // Load demo data
        async function loadDemoData() {
            try {
                const response = await fetch('http://localhost:8081/optimize?emit_ce=true', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        amount: 2500.00,
                        vendor_id: "demo_vendor",
                        urgency: "standard",
                        metadata: { demo: true, trace_id: "web-demo-001" }
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    document.getElementById('demoData').textContent = JSON.stringify(data, null, 2);
                } else {
                    document.getElementById('demoData').textContent = 'Demo data unavailable - services starting up';
                }
            } catch (error) {
                document.getElementById('demoData').textContent = 'Demo data unavailable - services starting up';
            }
        }

        // Handle decision form submission
        document.getElementById('decisionForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.className = 'result';
            resultDiv.innerHTML = '⏳ Processing decision...';

            const formData = {
                cart_total: parseFloat(document.getElementById('amount').value),
                currency: "USD",
                rail: "Card",
                channel: document.getElementById('channel').value === "ecommerce" ? "online" : "pos",
                features: {
                    amount: parseFloat(document.getElementById('amount').value),
                    risk_score: document.getElementById('riskTier').value === 'low' ? 0.2 :
                               document.getElementById('riskTier').value === 'medium' ? 0.5 : 0.8
                },
                context: {
                    trace_id: document.getElementById('traceId').value,
                    demo: true
                }
            };

            try {
                const response = await fetch('http://localhost:8080/decision', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });

                if (response.ok) {
                    const result = await response.json();
                    const outcome = result.decision || result.status || 'unknown';
                    const traceId = result.meta?.transaction_id || result.meta_structured?.transaction_id || 'N/A';
                    const explanation = result.explanation || result.explanation_human || '';
                    const railSelection = result.meta_structured?.rail_selection || result.meta?.rail_selection;

                    // Build rail selection info
                    let railInfo = '';
                    if (railSelection) {
                        const selectedRail = railSelection.selected_rail;
                        const originalRail = railSelection.original_rail;
                        const wasOptimized = railSelection.was_optimized;
                        const reason = railSelection.reason;
                        const cost = railSelection.cost;
                        const speedHours = railSelection.speed_hours;

                        if (wasOptimized) {
                            railInfo = `<br>🚀 <strong>Rail Optimized:</strong> ${originalRail} → ${selectedRail}<br>💰 Cost: $${cost} | ⏱️ Speed: ${speedHours}h | 📋 Reason: ${reason}`;
                        } else {
                            railInfo = `<br>🚀 <strong>Rail Selected:</strong> ${selectedRail}<br>💰 Cost: $${cost} | ⏱️ Speed: ${speedHours}h | 📋 Reason: ${reason}`;
                        }
                    }

                    if (outcome === 'APPROVE' || outcome === 'approve') {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `🎉 <strong>OUTCOME: APPROVE</strong><br>Transaction ID: ${traceId}${railInfo}${explanation ? '<br><br>📝 <strong>Explanation:</strong> ' + explanation : ''}`;
                    } else if (outcome === 'DECLINE' || outcome === 'decline') {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `❌ <strong>OUTCOME: DECLINE</strong><br>Transaction ID: ${traceId}${explanation ? '<br><br>📝 <strong>Explanation:</strong> ' + explanation : ''}`;
                    } else {
                        resultDiv.className = 'result warning';
                        resultDiv.innerHTML = `⚠️ <strong>OUTCOME: ${outcome.toUpperCase()}</strong><br>Transaction ID: ${traceId}${explanation ? '<br><br>📝 <strong>Explanation:</strong> ' + explanation : ''}`;
                    }
                } else {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `❌ API Error: ${response.status}<br>Make sure Orca is running on port 8080`;
                }
            } catch (error) {
                resultDiv.className = 'result error';
                resultDiv.innerHTML = `❌ Connection Error<br>Make sure 'make up' is running`;
            }
        });

        // Initialize page
        checkStatus();
        loadDemoData();

        // Refresh status every 30 seconds
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.exception_handler(Exception)
async def general_exception_handler(request: Any, exc: Exception) -> ORJSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return ORJSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)  # nosec B104
