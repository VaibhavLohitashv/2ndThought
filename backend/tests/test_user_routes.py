import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_me_unauthorized():
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
