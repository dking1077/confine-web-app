import sys
from unittest.mock import MagicMock
import pytest
from app import create_app

# Mock app.prompts in-memory so test collection and imports never fail
mock_prompts = MagicMock()
mock_prompts.classify_search_messages = MagicMock(return_value=[])
mock_prompts.classify_concepts_message = MagicMock(return_value=[])
mock_prompts.create_tabs = MagicMock(return_value=[])
sys.modules["app.prompts"] = mock_prompts


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