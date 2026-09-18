from app import create_app
import pytest


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    JWT_SECRET_KEY = "test"
    DB_USER = "postgres"
    DB_PASS = "postgres"
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_NAME = "postgres"
    POSTGRES_USER = "postgres"
    POSTGRES_PASS = "postgres"
    POSTGRES_HOST = "localhost"
    POSTGRES_PORT = "5432"
    OPENROUTER_APIKEY = "test"
    OPENROUTER_MODEL = "test"
    MUSIXMATCH_APIKEY = "test"
    RATELIMIT_ENABLED = False


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


def test_missing_auth_returns_contract(client):
    response = client.post("/search/", json={"search_input": "drake"})
    data = response.get_json()

    assert response.status_code == 401
    assert "ok" in data
    assert "code" in data
    assert "message" in data
    assert "details" in data


def test_validation_error_returns_contract(client):
    response = client.post("/auth/register", json={"email": "bad"})
    data = response.get_json()

    assert response.status_code == 400
    assert data["ok"] is False
    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    assert "details" in data


def test_not_found_api_returns_contract(client):
    response = client.get("/auth/not-a-route")
    data = response.get_json()

    assert response.status_code == 404
    assert data["ok"] is False
    assert data["code"] == "HTTP_404"
    assert "message" in data