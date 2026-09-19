from unittest.mock import MagicMock
from app.errors import ApiError
from app.services import AIService
import pytest


@pytest.fixture
def ai_service():
    return AIService(api_key="test_key", model="test_model")


def make_mock_response(content: str):
    """Helper to build OpenAI completion response structure."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def test_parse_search_success(ai_service, monkeypatch):
    """Test parsing search prompt into artist and track."""
    mock_resp = make_mock_response('```json\n{"artist": "Radiohead", "track": "Karma Police"}\n```')
    monkeypatch.setattr(ai_service.client.chat.completions, "create", lambda **kw: mock_resp)

    artist, track = ai_service.parse_search("play karma police by radiohead")

    assert artist == "Radiohead"
    assert track == "Karma Police"


def test_parse_search_none_string_conversion(ai_service, monkeypatch):
    """Test string 'None' conversion to Python None."""
    mock_resp = make_mock_response('{"artist": "Radiohead", "track": "None"}')
    monkeypatch.setattr(ai_service.client.chat.completions, "create", lambda **kw: mock_resp)

    artist, track = ai_service.parse_search("play radiohead")

    assert artist == "Radiohead"
    assert track is None


def test_parse_json_response_invalid_json(ai_service):
    """Test invalid JSON response raises ApiError."""
    with pytest.raises(ApiError) as exc_info:
        ai_service.parse_json_response("invalid json response")

    assert exc_info.value.code == "AI_INVALID_RESPONSE"
    assert exc_info.value.status_code == 502


def test_transform_lyrics_markdown_cleanup(ai_service, monkeypatch):
    """Test markdown block removal from generated lyrics."""
    mock_resp = make_mock_response("```\nTransformed lyrics line 1\n```")
    monkeypatch.setattr(ai_service.client.chat.completions, "create", lambda **kw: mock_resp)

    res = ai_service.transform_lyrics("original lyrics", [], [])

    assert res == "Transformed lyrics line 1"


def test_retry_and_api_error(ai_service, monkeypatch):
    """Test retry behavior and eventual ApiError on failure."""
    ai_service.max_attempts = 2
    monkeypatch.setattr("time.sleep", lambda secs: None)

    def raise_error(**kw):
        raise Exception("API Error")

    monkeypatch.setattr(ai_service.client.chat.completions, "create", raise_error)

    with pytest.raises(ApiError) as exc_info:
        ai_service.parse_search("test")

    assert exc_info.value.code == "OPENROUTER_REQUEST_FAILED"
    assert exc_info.value.status_code == 502