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


def test_jwks_route_writes_fetched_audit(client, monkeypatch):
    import app as app_module

    calls = []
    monkeypatch.setattr(app_module, "write_audit_log", lambda **kwargs: calls.append(kwargs))

    response = client.get(
        "/.well-known/jwks.json",
        headers={"X-Forwarded-For": "203.0.113.5"},
    )

    assert response.status_code == 200
    audit = next(c for c in calls if c["event_type"] == "jwks.fetched")
    assert audit["success"] is True
    assert audit["detail"]["client_ip"] == "203.0.113.5"
    assert audit["detail"]["active_accounts"] == 0
    assert audit["detail"]["keys_served"] == 0


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
