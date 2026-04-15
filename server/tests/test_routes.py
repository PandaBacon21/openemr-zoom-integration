import pytest


def test_health_route(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_jwks_route(client):
    response = client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"keys": []}


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
