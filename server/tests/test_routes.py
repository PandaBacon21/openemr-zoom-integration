import pytest


def test_health_route(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_jwks_route(client):
    response = client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    body = response.get_json()
    assert "keys" in body
    assert len(body["keys"]) == 1
    assert body["keys"][0]["kid"] == "test-key-id"


def test_openemr_token_test_route_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.jwt_assertion.get_openemr_token",
        lambda force_refresh=False: "abcdefghijklmnopqrstuvwxyz123456",
    )

    response = client.get("/test/openemr-token")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["token_preview"] == "abcdefghijklmnopqrst..."


def test_openemr_token_test_route_failure(client, monkeypatch):
    def _raise(force_refresh=False):
        raise RuntimeError("token exchange failed")

    monkeypatch.setattr("app.auth.jwt_assertion.get_openemr_token", _raise)

    response = client.get("/test/openemr-token")

    assert response.status_code == 500
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "token exchange failed"


@pytest.mark.parametrize(
    ("path", "blueprint_name"),
    [
        ("/auth/", "auth"),
        ("/openemr/", "openemr"),
        ("/webhooks/", "webhooks"),
        ("/zoom/", "zoom"),
        ("/config/", "config"),
    ],
)
def test_blueprint_index_routes(client, path, blueprint_name):
    response = client.get(path)

    assert response.status_code == 200
    body = response.get_json()
    assert body["blueprint"] == blueprint_name
