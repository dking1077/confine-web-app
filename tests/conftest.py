import sys
from pathlib import Path
from unittest.mock import MagicMock
import fakeredis
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestConfig:
    TESTING = True
    RATELIMIT_ENABLED = False  # <-- Add this line to prevent Redis connection attempts
    JWT_SECRET_KEY = "test-secret-key"
    POSTGRES_USER = "test"
    POSTGRES_PASS = "test"
    POSTGRES_HOST = "localhost"
    POSTGRES_PORT = "5432"
    POSTGRES_DB = "test_db"


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    # in-memory redis for the token blocklist and job ownership
    server = fakeredis.FakeServer()
    monkeypatch.setattr("app.extensions.redis_blocklist", fakeredis.FakeStrictRedis(server=server, decode_responses=True))
    monkeypatch.setattr("app.extensions.redis_jobs", fakeredis.FakeStrictRedis(server=server, decode_responses=True))
    monkeypatch.setattr("app.search.routes.redis_jobs", fakeredis.FakeStrictRedis(server=server, decode_responses=True))
    monkeypatch.setattr("app.tabs.routes.redis_jobs", fakeredis.FakeStrictRedis(server=server, decode_responses=True))


@pytest.fixture
def app(monkeypatch):
    # Mock out real database creation and table setup during tests
    monkeypatch.setattr("app.db_create", MagicMock())

    mock_db_session = MagicMock()
    monkeypatch.setattr("app.extensions.db_session", mock_db_session)
    monkeypatch.setattr("app.extensions.init_db", MagicMock())
    monkeypatch.setattr("app.extensions.create_tables", MagicMock())

    from app import create_app

    app_instance = create_app(TestConfig)
    yield app_instance


@pytest.fixture
def client(app):
    return app.test_client()