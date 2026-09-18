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


def test_index_route_loads(client):
    response = client.get("/")
    assert response.status_code == 200


def test_session_route_loads(client):
    response = client.get("/session")
    assert response.status_code == 200


def test_sentry_test_route_exists(client):
    response = client.get("/sentry-test")
    assert response.status_code == 500