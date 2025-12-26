from fastapi.testclient import TestClient

from src.api.main import app


def test_voice_webhook_returns_twiml():
    client = TestClient(app)
    response = client.post("/voice")
    assert response.status_code == 200
    assert "<Stream" in response.text
