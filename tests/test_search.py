from unittest.mock import MagicMock
import pytest
from flask_jwt_extended import create_access_token


@pytest.fixture(autouse=True)
def mock_search_deps(monkeypatch):
    """Bypass rate limiter and audit logging for all search tests."""
    monkeypatch.setattr("app.extensions.limiter.limit", lambda *a, **kw: lambda f: f)
    monkeypatch.setattr("app.audit.audit_log", MagicMock())


def get_auth_headers(app, user_id=1):
    """Generate JWT headers directly using Flask-JWT-Extended without route calls."""
    with app.app_context():
        token = create_access_token(identity=str(user_id))
        return {"Authorization": f"Bearer {token}"}


# --- UNAUTHORIZED ACCESS ---

def test_search_unauthorized(client):
    """Verify request fails with 401 if JWT token is missing."""
    res = client.post("/search/", json={"search_input": "Radiohead - Creep"})
    assert res.status_code == 401


# --- SUCCESSFUL SEARCH ---

def test_search_success(client, app, monkeypatch):
    """Test successful search execution by mocking the Celery chain execution."""
    headers = get_auth_headers(app, user_id=1)

    # 1. Mock Celery AsyncResult / Task chain
    mock_async_result = MagicMock()
    mock_async_result.id = "test-job-id-123"
    mock_async_result.get.return_value = {
        "search_results": [
            {"track_name": "Creep", "artist_name": "Radiohead"}
        ]
    }

    # 2. Safely mock chain(...).apply_async(...) without IDE warnings
    def mock_chain(*args, **kwargs):
        mock_chain_obj = MagicMock()
        mock_chain_obj.apply_async.return_value = mock_async_result
        return mock_chain_obj

    # Patch chain where it's used in the search route module
    monkeypatch.setattr("app.search.routes.chain", mock_chain)

    # 3. Make POST request
    res = client.post(
        "/search/",
        json={"search_input": "Radiohead - Creep"},
        headers=headers,
    )

    # 4. Assertions
    assert res.status_code == 200
    data = res.get_json()
    assert data["code"] == "SEARCH_SUCCESS"
    assert data["data"]["job_id"] == "test-job-id-123"
    assert len(data["data"]["result"]) == 1
    assert data["data"]["result"][0]["track_name"] == "Creep"


# --- VALIDATION ERROR ---

def test_search_invalid_payload(client, app):
    """Test payload failing Marshmallow schema validation."""
    headers = get_auth_headers(app)

    # Missing required 'search_input' field
    res = client.post("/search/", json={}, headers=headers)
    assert res.status_code in (400, 422)