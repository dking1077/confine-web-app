def test_index_route_loads(client):
    response = client.get("/")
    assert response.status_code == 200


def test_session_route_loads(client):
    response = client.get("/session")
    assert response.status_code == 200


def test_sentry_test_route_exists(client):
    response = client.get("/sentry-test")
    assert response.status_code == 500