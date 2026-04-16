def test_health_route(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_jwks_route(client):
    response = client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"keys": []}


def test_openemr_root_route_not_defined(client):
    response = client.get("/openemr/")
    assert response.status_code == 404


def test_zoom_root_route_not_defined(client):
    response = client.get("/zoom/")
    assert response.status_code == 404


def test_config_root_requires_api_key(client):
    response = client.get("/config/")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid or missing API key"}
