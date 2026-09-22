import sys
from pathlib import Path
from unittest.mock import MagicMock
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