import pytest
from unittest.mock import patch, MagicMock
from app.errors import ApiError


@pytest.fixture(autouse=True)
def mock_deps(monkeypatch):
    """Disable rate limiter and audit logging across all auth tests."""
    monkeypatch.setattr("app.extensions.limiter.limit", lambda *a, **kw: lambda f: f)
    monkeypatch.setattr("app.auth.routes.audit_log", MagicMock())


# --- REGISTER TESTS ---

def test_register_success(client, monkeypatch):
    monkeypatch.setattr("app.auth.routes.add_user", lambda db, email, pwd: {"ok": True, "user_id": 1})

    res = client.post("/auth/register", json={"email": "test@example.com", "password": "password123"})
    assert res.status_code == 201
    assert res.get_json()["data"] == {"user_id": 1, "email": "test@example.com"}


def test_register_failure(client, monkeypatch):
    monkeypatch.setattr("app.auth.routes.add_user", lambda db, email, pwd: {"ok": False, "error": "Email taken"})

    res = client.post("/auth/register", json={"email": "taken@example.com", "password": "password123"})
    assert res.status_code == 400
    assert res.get_json()["code"] == "REGISTER_FAILED"


# --- LOGIN TESTS ---

def test_login_success(client, monkeypatch):
    monkeypatch.setattr("app.auth.routes.login_user", lambda db, email, pwd: {"ok": True, "user_id": 1})

    res = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_invalid_credentials(client, monkeypatch):
    monkeypatch.setattr("app.auth.routes.login_user", lambda db, email, pwd: {"ok": False, "error": "Invalid"})

    res = client.post("/auth/login", json={"email": "test@example.com", "password": "wrong"})
    assert res.status_code == 401
    assert res.get_json()["code"] == "LOGIN_FAILED"


# --- PROTECTED ROUTE / LOGOUT / REFRESH TESTS ---

def test_protected_routes_without_token(client):
    assert client.get("/auth/session-status").status_code == 401
    assert client.post("/auth/logout").status_code == 401
    assert client.post("/auth/refresh").status_code == 401


def test_session_status_and_logout_success(client, monkeypatch):
    # 1. Login to get tokens
    monkeypatch.setattr("app.auth.routes.login_user", lambda db, email, pwd: {"ok": True, "user_id": 1})
    login_res = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    access_token = login_res.get_json()["data"]["access_token"]
    refresh_token = login_res.get_json()["data"]["refresh_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Check Session Status
    mock_user = MagicMock(email="test@example.com")
    monkeypatch.setattr("app.extensions.db_session.query", lambda *a: MagicMock(filter_by=lambda **kw: MagicMock(first=lambda: mock_user)))

    session_res = client.get("/auth/session-status", headers=headers)
    assert session_res.status_code == 200
    assert session_res.get_json()["data"]["logged_in"] is True

    # 3. Test Refresh Token
    refresh_headers = {"Authorization": f"Bearer {refresh_token}"}
    refresh_res = client.post("/auth/refresh", headers=refresh_headers)
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.get_json()["data"]

    # 4. Logout
    logout_res = client.post("/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # 5. Verify Token Revocation (using revoked token should fail)
    post_logout_res = client.get("/auth/session-status", headers=headers)
    assert post_logout_res.status_code == 401