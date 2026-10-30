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
    """Test search is queued by mocking the Celery chain execution."""
    headers = get_auth_headers(app, user_id=1)

    mock_async_result = MagicMock()
    mock_async_result.id = "test-job-id-123"

    def mock_chain(*args, **kwargs):
        mock_chain_obj = MagicMock()
        mock_chain_obj.apply_async.return_value = mock_async_result
        return mock_chain_obj

    # Patch chain where it's used in the search route module
    monkeypatch.setattr("app.search.routes.chain", mock_chain)

    res = client.post(
        "/search/",
        json={"search_input": "Radiohead - Creep"},
        headers=headers,
    )

    assert res.status_code == 202
    data = res.get_json()
    assert data["code"] == "search_queued"
    assert data["data"]["job_id"] == "test-job-id-123"


# --- JOB STATUS ---

def queue_job(client, app, monkeypatch, user_id, job_id="job-1"):
    mock_async_result = MagicMock()
    mock_async_result.id = job_id

    def mock_chain(*args, **kwargs):
        mock_chain_obj = MagicMock()
        mock_chain_obj.apply_async.return_value = mock_async_result
        return mock_chain_obj

    monkeypatch.setattr("app.search.routes.chain", mock_chain)
    client.post(
        "/search/",
        json={"search_input": "Radiohead - Creep"},
        headers=get_auth_headers(app, user_id=user_id),
    )


def test_search_status_owner_can_read(client, app, monkeypatch):
    queue_job(client, app, monkeypatch, user_id=1)

    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.result = {"search_results": [{"track_name": "Creep"}]}
    monkeypatch.setattr("app.search.routes.AsyncResult", lambda job_id: mock_result)

    res = client.get("/search/status/job-1", headers=get_auth_headers(app, user_id=1))
    assert res.status_code == 200
    assert res.get_json()["data"]["result"][0]["track_name"] == "Creep"


def test_search_status_other_user_gets_404(client, app, monkeypatch):
    queue_job(client, app, monkeypatch, user_id=1)

    res = client.get("/search/status/job-1", headers=get_auth_headers(app, user_id=2))
    assert res.status_code == 404
    assert res.get_json()["code"] == "job_not_found"


def test_search_status_failure_hides_internal_errors(client, app, monkeypatch):
    queue_job(client, app, monkeypatch, user_id=1)

    mock_result = MagicMock()
    mock_result.state = "FAILURE"
    mock_result.result = Exception("secret internal detail")
    mock_result.traceback = "Traceback (most recent call last): secret"
    monkeypatch.setattr("app.search.routes.AsyncResult", lambda job_id: mock_result)

    res = client.get("/search/status/job-1", headers=get_auth_headers(app, user_id=1))
    assert res.status_code == 500
    body = res.get_data(as_text=True)
    assert "secret" not in body
    assert "traceback" not in body


# --- VALIDATION ERROR ---

def test_search_invalid_payload(client, app):
    """Test payload failing Marshmallow schema validation."""
    headers = get_auth_headers(app)

    # Missing required 'search_input' field
    res = client.post("/search/", json={}, headers=headers)
    assert res.status_code in (400, 422)