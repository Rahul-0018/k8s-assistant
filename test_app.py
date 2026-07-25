import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "model" in data


def test_readiness_without_api_key():
    response = client.get("/ready")
    # Should fail if GROQ_API_KEY not set
    assert response.status_code in [200, 503]


def test_list_models():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) > 0
    assert "llama-3.1-8b-instant" in [m["id"] for m in data["models"]]


def test_chat_without_api_key():
    response = client.post("/api/chat", json={"message": "Hello"})
    # Should fail if GROQ_API_KEY not configured
    assert response.status_code in [200, 503, 502]


def test_clear_conversation():
    response = client.delete("/api/conversations/test-123")
    assert response.status_code == 200
    assert response.json()["status"] == "cleared"


def test_root_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
