"""Tests for the Orca API FastAPI service."""

from fastapi.testclient import TestClient
from orca_api.main import app

# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Test cases for the /healthz endpoint."""

    def test_health_check_success(self):
        """Test that health check returns ok=True."""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_health_check_response_format(self):
        """Test that health check response has correct format."""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "ok" in data
        assert isinstance(data["ok"], bool)


class TestDecisionEndpoint:
    """Test cases for the /decision endpoint."""

    def test_decision_approve_small_amount(self):
        """Test decision for small amount that should be approved."""
        request_data = {"cart_total": 50.0, "currency": "USD", "rail": "Card", "channel": "online"}

        response = client.post("/decision", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "decision" in data
        assert "reasons" in data
        assert "actions" in data
        assert "meta" in data

        # Should be approved for small amount
        assert data["decision"] in ["APPROVE", "REVIEW", "DECLINE"]
        assert isinstance(data["reasons"], list)
        assert isinstance(data["actions"], list)

    def test_decision_high_ticket(self):
        """Test decision for high ticket amount."""
        request_data = {
            "cart_total": 10000.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
        }

        response = client.post("/decision", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # High ticket should likely trigger review or decline
        assert data["decision"] in ["APPROVE", "REVIEW", "DECLINE"]
        assert len(data["reasons"]) > 0

    def test_decision_ach_rail(self):
        """Test decision for ACH rail."""
        request_data = {"cart_total": 1500.0, "currency": "USD", "rail": "ACH", "channel": "online"}

        response = client.post("/decision", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["decision"] in ["APPROVE", "REVIEW", "DECLINE"]
        assert "meta" in data

    def test_decision_with_features(self):
        """Test decision with additional features."""
        request_data = {
            "cart_total": 500.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
            "features": {"velocity_24h": 3, "risk_score": 0.2},
            "context": {"user_id": "test_user_123", "payment_method": "visa"},
        }

        response = client.post("/decision", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["decision"] in ["APPROVE", "REVIEW", "DECLINE"]
        assert "meta" in data

    def test_decision_invalid_cart_total(self):
        """Test decision with invalid cart total."""
        request_data = {
            "cart_total": -100.0,  # Invalid negative amount
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
        }

        response = client.post("/decision", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_decision_missing_required_fields(self):
        """Test decision with missing required fields."""
        request_data = {
            "currency": "USD"
            # Missing cart_total
        }

        response = client.post("/decision", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_decision_invalid_rail(self):
        """Test decision with invalid rail type."""
        request_data = {
            "cart_total": 100.0,
            "currency": "USD",
            "rail": "InvalidRail",  # Invalid rail
            "channel": "online",
        }

        response = client.post("/decision", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_decision_invalid_channel(self):
        """Test decision with invalid channel type."""
        request_data = {
            "cart_total": 100.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "invalid_channel",  # Invalid channel
        }

        response = client.post("/decision", json=request_data)

        assert response.status_code == 422  # Validation error


class TestExplainEndpoint:
    """Test cases for the /explain endpoint."""

    def test_explain_approve_decision(self):
        """Test explanation for approved decision."""
        decision_data = {
            "decision": "APPROVE",
            "reasons": ["Cart total $50.00 within approved threshold"],
            "actions": ["Process payment", "Send confirmation"],
            "meta": {"risk_score": 0.1, "cart_total": 50.0},
            "status": "APPROVE",
            "explanation": "Transaction approved for $50.00. Cart total within approved limits.",
        }

        request_data = {"decision": decision_data}

        response = client.post("/explain", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "explanation" in data
        assert isinstance(data["explanation"], str)
        assert len(data["explanation"]) > 0

    def test_explain_decline_decision(self):
        """Test explanation for declined decision."""
        decision_data = {
            "decision": "DECLINE",
            "reasons": ["HIGH_TICKET: Amount exceeds card threshold of $5000"],
            "actions": ["BLOCK"],
            "meta": {"risk_score": 0.9, "cart_total": 10000.0},
            "status": "DECLINE",
            "explanation": "Transaction declined due to high ML risk score of 0.900.",
        }

        request_data = {"decision": decision_data}

        response = client.post("/explain", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "explanation" in data
        assert isinstance(data["explanation"], str)
        assert len(data["explanation"]) > 0

    def test_explain_review_decision(self):
        """Test explanation for review decision."""
        decision_data = {
            "decision": "REVIEW",
            "reasons": ["VELOCITY_FLAG: Too many recent attempts"],
            "actions": ["manual_review"],
            "meta": {"risk_score": 0.5, "cart_total": 2000.0},
            "status": "ROUTE",
            "explanation": "Transaction flagged for manual review due to: VELOCITY_FLAG: Too many recent attempts.",
        }

        request_data = {"decision": decision_data}

        response = client.post("/explain", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "explanation" in data
        assert isinstance(data["explanation"], str)
        assert len(data["explanation"]) > 0

    def test_explain_with_human_explanation(self):
        """Test explanation when decision already has explanation_human."""
        decision_data = {
            "decision": "APPROVE",
            "reasons": ["Cart total $50.00 within approved threshold"],
            "actions": ["Process payment"],
            "meta": {"cart_total": 50.0},
            "status": "APPROVE",
            "explanation": "Transaction approved for $50.00. Cart total within approved limits.",
            "explanation_human": "Approved: Transaction amount within approved limits.",
        }

        request_data = {"decision": decision_data}

        response = client.post("/explain", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "explanation" in data
        assert data["explanation"] == "Approved: Transaction amount within approved limits."

    def test_explain_missing_decision(self):
        """Test explanation with missing decision field."""
        request_data = {}  # Missing decision field

        response = client.post("/explain", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_explain_invalid_decision_structure(self):
        """Test explanation with invalid decision structure."""
        request_data = {"decision": "invalid_decision"}  # Should be a DecisionResponse object

        response = client.post("/explain", json=request_data)

        assert response.status_code == 422  # Validation error


class TestAPIErrorHandling:
    """Test cases for API error handling."""

    def test_invalid_json_request(self):
        """Test handling of invalid JSON in request body."""
        response = client.post(
            "/decision", data="invalid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_unsupported_http_method(self):
        """Test handling of unsupported HTTP methods."""
        response = client.put("/healthz")
        assert response.status_code == 405  # Method not allowed

        response = client.delete("/decision")
        assert response.status_code == 405  # Method not allowed

    def test_nonexistent_endpoint(self):
        """Test handling of nonexistent endpoints."""
        response = client.get("/nonexistent")
        assert response.status_code == 404


class TestAPIResponseFormat:
    """Test cases for API response format consistency."""

    def test_decision_response_has_required_fields(self):
        """Test that decision response has all required fields."""
        request_data = {"cart_total": 100.0, "currency": "USD", "rail": "Card", "channel": "online"}

        response = client.post("/decision", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = ["decision", "reasons", "actions", "meta"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_explain_response_has_required_fields(self):
        """Test that explain response has all required fields."""
        decision_data = {
            "decision": "APPROVE",
            "reasons": ["Cart total $100.00 within approved threshold"],
            "actions": ["Process payment"],
            "meta": {"cart_total": 100.0},
            "status": "APPROVE",
        }

        request_data = {"decision": decision_data}

        response = client.post("/explain", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "explanation" in data
        assert isinstance(data["explanation"], str)

    def test_response_content_type(self):
        """Test that responses have correct content type."""
        # Test health endpoint
        response = client.get("/healthz")
        assert response.headers["content-type"] == "application/json"

        # Test decision endpoint
        request_data = {"cart_total": 100.0, "currency": "USD", "rail": "Card", "channel": "online"}
        response = client.post("/decision", json=request_data)
        assert response.headers["content-type"] == "application/json"

        # Test explain endpoint
        decision_data = {
            "decision": "APPROVE",
            "reasons": ["Cart total $100.00 within approved threshold"],
            "actions": ["Process payment"],
            "meta": {"cart_total": 100.0},
            "status": "APPROVE",
        }
        request_data = {"decision": decision_data}
        response = client.post("/explain", json=request_data)
        assert response.headers["content-type"] == "application/json"
