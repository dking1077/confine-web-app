def test_search_input_schema_validation(client):
    response = client.post("/search/", json={})
    data = response.get_json()

    assert response.status_code == 400
    assert data["ok"] is False
    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data
    assert "details" in data