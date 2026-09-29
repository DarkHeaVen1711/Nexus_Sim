"""Tests for NexusSim Unified Backend Gateway (Port 8000)."""

import pytest
from fastapi.testclient import TestClient
from gateway.server import app

client = TestClient(app)


def test_gateway_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["port"] == 8000
    assert "services" in data
    assert "gateway" in data


def test_gateway_chat_offline_graceful():
    # When upstream chat service is offline, return 503 rather than crash
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code in [200, 502, 503]


def test_gateway_incident_offline_graceful():
    response = client.post("/api/incident", json={"text": "crash on loop"})
    assert response.status_code in [200, 502, 503]


def test_gateway_algo_offline_graceful():
    response = client.get("/api/algo/matrix")
    assert response.status_code in [200, 502, 503]
