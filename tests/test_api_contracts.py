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