"""
Smoke tests for MCP (Model Context Protocol) endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from mcp.server import router


@pytest.fixture
def client():
    """Create test client for the MCP router only."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_mcp_get_status(client):
    """Test MCP getStatus verb returns expected response."""
    response = client.post("/mcp/invoke", json={"verb": "getStatus", "args": {}})

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert "data" in data
    assert data["data"]["agent"] == "orca"
    assert data["data"]["status"] == "active"


def test_mcp_get_decision_schema(client):
    """Test MCP getDecisionSchema verb returns expected response."""
    response = client.post("/mcp/invoke", json={"verb": "getDecisionSchema", "args": {}})

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert "data" in data
    assert data["data"]["agent"] == "orca"
    assert "schema_url" in data["data"]
    assert "schema_version" in data["data"]
    assert data["data"]["schema_version"] == "ap2.v1"
    assert "description" in data["data"]


def test_mcp_unsupported_verb(client):
    """Test MCP with unsupported verb returns error."""
    response = client.post("/mcp/invoke", json={"verb": "unsupportedVerb", "args": {}})

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is False
    assert "Unsupported verb" in data["error"]


def test_mcp_missing_verb(client):
    """Test MCP with missing verb returns validation error."""
    response = client.post("/mcp/invoke", json={"args": {}})

    assert response.status_code == 422


def test_mcp_invalid_json(client):
    """Test MCP with invalid JSON returns error."""
    response = client.post("/mcp/invoke", data="invalid json")

    assert response.status_code == 422
