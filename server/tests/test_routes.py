from auth_utils import AUTH_HEADERS


def test_health_route(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_jwks_route(client):
    response = client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"keys": []}


def test_openemr_root_route_requires_jwt(client):
    response = client.get("/openemr/")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Missing or invalid Authorization header"}


def test_zoom_root_route_requires_jwt(client):
    response = client.get("/zoom/")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Missing or invalid Authorization header"}


def test_config_root_requires_jwt(client):
    response = client.get("/config/")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Missing or invalid Authorization header"}


def test_protected_blueprint_roots_accept_jwt(client):
    openemr_response = client.get("/openemr/", headers=AUTH_HEADERS)
    zoom_response = client.get("/zoom/", headers=AUTH_HEADERS)
    config_response = client.get("/config/", headers=AUTH_HEADERS)

    assert openemr_response.status_code == 200
    assert openemr_response.get_json() == {
        "blueprint": "openemr_routes",
        "status": "ok",
    }
    assert zoom_response.status_code == 200
    assert zoom_response.get_json() == {
        "blueprint": "zoom_routes",
        "status": "ok",
    }
    assert config_response.status_code == 200
    assert config_response.get_json() == {
        "blueprint": "config_routes",
        "status": "active",
    }
