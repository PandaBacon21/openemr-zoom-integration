from datetime import datetime, timezone
from types import SimpleNamespace

from app.extensions import db
from app.models import ZoomAccount

API_HEADERS = {"X-API-Key": "test-api-key"}


def test_register_endpoint_requires_json_body(client):
    response = client.post("/config/register", headers=API_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be JSON"}


def test_register_endpoint_requires_all_fields(client):
    response = client.post(
        "/config/register",
        headers=API_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Missing required fields"
    assert set(body["missing"]) == {"zoom_client_secret", "zoom_webhook_secret", "contact_email"}


def test_register_endpoint_success(client, monkeypatch):
    fake_account = SimpleNamespace(
        account_id="acct-1",
        openemr_client_id="openemr-client-id",
        kid="zoomly-acct-1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    monkeypatch.setattr("app.blueprints.config.register_zoom_account", lambda **kwargs: fake_account)

    response = client.post(
        "/config/register",
        headers=API_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret",
            "zoom_webhook_secret": "webhook-secret",
            "contact_email": "admin@example.com",
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "status": "registered",
        "zoom_account_id": "acct-1",
        "openemr_client_id": "openemr-client-id",
        "kid": "zoomly-acct-1",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def test_register_endpoint_maps_value_error_to_400(client, monkeypatch):
    def _raise(**kwargs):
        raise ValueError("duplicate account")

    monkeypatch.setattr("app.blueprints.config.register_zoom_account", _raise)
    response = client.post(
        "/config/register",
        headers=API_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret",
            "zoom_webhook_secret": "webhook-secret",
            "contact_email": "admin@example.com",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "duplicate account"}


def test_register_endpoint_maps_unexpected_error_to_500(client, monkeypatch):
    def _raise(**kwargs):
        raise RuntimeError("openemr timeout")

    monkeypatch.setattr("app.blueprints.config.register_zoom_account", _raise)
    response = client.post(
        "/config/register",
        headers=API_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret",
            "zoom_webhook_secret": "webhook-secret",
            "contact_email": "admin@example.com",
        },
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Registration failed", "detail": "openemr timeout"}


def test_deregister_endpoint_success(client, monkeypatch):
    monkeypatch.setattr("app.blueprints.config.deregister_zoom_account", lambda account_id: None)
    response = client.delete("/config/register/acct-1", headers=API_HEADERS)
    assert response.status_code == 200
    assert response.get_json() == {"status": "deregistered", "zoom_account_id": "acct-1"}


def test_deregister_endpoint_maps_not_found_to_404(client, monkeypatch):
    def _raise(account_id):
        raise ValueError("not found")

    monkeypatch.setattr("app.blueprints.config.deregister_zoom_account", _raise)
    response = client.delete("/config/register/acct-1", headers=API_HEADERS)
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_deregister_endpoint_maps_unexpected_error_to_500(client, monkeypatch):
    def _raise(account_id):
        raise RuntimeError("db down")

    monkeypatch.setattr("app.blueprints.config.deregister_zoom_account", _raise)
    response = client.delete("/config/register/acct-1", headers=API_HEADERS)
    assert response.status_code == 500
    assert response.get_json() == {"error": "Deregistration failed", "detail": "db down"}


def test_list_registrations_returns_summary(client, app):
    with app.app_context():
        db.session.add(
            ZoomAccount(
                account_id="acct-1",
                client_id="zoom-client-id",
                client_secret="zoom-client-secret",
                webhook_secret="webhook-secret",
                openemr_client_id="openemr-client-id",
                private_key_path="/tmp/keys/acct-1/private.pem",
                kid="zoomly-acct-1",
                zoom_access_token="zoom-token",
                openemr_access_token="openemr-token",
                is_active=True,
            )
        )
        db.session.add(
            ZoomAccount(
                account_id="acct-2",
                client_id="zoom-client-id-2",
                client_secret="zoom-client-secret-2",
                webhook_secret="webhook-secret-2",
                openemr_client_id="openemr-client-id-2",
                private_key_path="/tmp/keys/acct-2/private.pem",
                kid="zoomly-acct-2",
                is_active=False,
            )
        )
        db.session.commit()

    response = client.get("/config/registrations", headers=API_HEADERS)

    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 2
    assert len(body["registrations"]) == 2

    acct1 = next(item for item in body["registrations"] if item["zoom_account_id"] == "acct-1")
    acct2 = next(item for item in body["registrations"] if item["zoom_account_id"] == "acct-2")

    assert acct1["openemr_client_id"] == "openemr-client-id"
    assert acct1["kid"] == "zoomly-acct-1"
    assert acct1["is_active"] is True
    assert acct1["has_zoom_token"] is True
    assert acct1["has_openemr_token"] is True
    assert isinstance(acct1["created_at"], str)
    assert isinstance(acct1["updated_at"], str)

    assert acct2["is_active"] is False
    assert acct2["has_zoom_token"] is False
    assert acct2["has_openemr_token"] is False
