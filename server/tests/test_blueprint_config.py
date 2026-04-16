from datetime import datetime, timezone
from types import SimpleNamespace

from app.extensions import db
from app.models import ZoomAccount

API_HEADERS = {"X-API-Key": "test-api-key"}


def _create_account(app, account_id: str, *, is_active: bool = True) -> ZoomAccount:
    with app.app_context():
        account = ZoomAccount(
            account_id=account_id,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{account_id}/private.pem",
            kid=f"zoomly-{account_id}",
            is_active=is_active,
        )
        db.session.add(account)
        db.session.commit()
        return account


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


def test_verify_registration_returns_404_for_unknown_account(client):
    response = client.post("/config/register/missing/verify", headers=API_HEADERS)
    assert response.status_code == 404
    assert response.get_json() == {"error": "No active registration found for account missing"}


def test_verify_registration_returns_success_true(client, app, monkeypatch):
    _create_account(app, "acct-verify", is_active=True)
    monkeypatch.setattr(
        "app.services.reg_verification.verify_openemr_token_for_account",
        lambda account: True,
    )

    response = client.post("/config/register/acct-verify/verify", headers=API_HEADERS)

    assert response.status_code == 200
    assert response.get_json() == {
        "zoom_account_id": "acct-verify",
        "openemr_verified": True,
        "message": "OpenEMR token verified successfully",
    }


def test_verify_registration_returns_success_false(client, app, monkeypatch):
    _create_account(app, "acct-verify", is_active=True)
    monkeypatch.setattr(
        "app.services.reg_verification.verify_openemr_token_for_account",
        lambda account: False,
    )

    response = client.post("/config/register/acct-verify/verify", headers=API_HEADERS)

    assert response.status_code == 200
    assert response.get_json() == {
        "zoom_account_id": "acct-verify",
        "openemr_verified": False,
        "message": "OpenEMR client not yet enabled — enable it in OpenEMR admin and try again",
    }


def test_create_provider_mapping_requires_body(client):
    response = client.post("/config/providers", headers=API_HEADERS, json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body is required"}


def test_create_provider_mapping_requires_fields(client):
    response = client.post(
        "/config/providers",
        headers=API_HEADERS,
        json={"zoom_account_id": "acct-1", "openemr_fhir_id": "pract-1"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Missing required fields: openemr_provider_npi, zoom_user_id, zoom_user_email, zoom_user_type"
    }


def test_create_provider_mapping_success(client, monkeypatch):
    fake_mapping = SimpleNamespace(
        id=12,
        openemr_provider_npi="1234567890",
        openemr_provider_name="Dr Jane Doe",
        zoom_user_email="jane@example.com",
        zoom_user_name="Dr Jane Doe",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    monkeypatch.setattr("app.services.providers.create_provider_mapping", lambda **kwargs: fake_mapping)

    response = client.post(
        "/config/providers",
        headers=API_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "openemr_fhir_id": "pract-1",
            "openemr_provider_npi": "1234567890",
            "zoom_user_id": "u-1",
            "zoom_user_email": "jane@example.com",
            "zoom_user_type": 2,
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "id": 12,
        "openemr_provider_npi": "1234567890",
        "openemr_provider_name": "Dr Jane Doe",
        "zoom_user_email": "jane@example.com",
        "zoom_user_name": "Dr Jane Doe",
        "created_at": "2026-01-02T00:00:00+00:00",
    }


def test_create_provider_mapping_maps_value_error_to_400(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.providers.create_provider_mapping",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("duplicate mapping")),
    )

    response = client.post(
        "/config/providers",
        headers=API_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "openemr_fhir_id": "pract-1",
            "openemr_provider_npi": "1234567890",
            "zoom_user_id": "u-1",
            "zoom_user_email": "jane@example.com",
            "zoom_user_type": 2,
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "duplicate mapping"}


def test_create_provider_mapping_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.providers.create_provider_mapping",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.post(
        "/config/providers",
        headers=API_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "openemr_fhir_id": "pract-1",
            "openemr_provider_npi": "1234567890",
            "zoom_user_id": "u-1",
            "zoom_user_email": "jane@example.com",
            "zoom_user_type": 2,
        },
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}


def test_list_provider_mappings_requires_zoom_account_id(client):
    response = client.get("/config/providers", headers=API_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_list_provider_mappings_success(client, monkeypatch):
    fake_mappings = [
        SimpleNamespace(
            id=21,
            openemr_fhir_id="pract-1",
            openemr_provider_npi="1234567890",
            openemr_provider_name="Dr Jane Doe",
            zoom_user_id="u-1",
            zoom_user_email="jane@example.com",
            zoom_user_name="Dr Jane Doe",
            created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
    ]
    monkeypatch.setattr("app.services.providers.get_provider_mappings", lambda account_id: fake_mappings)

    response = client.get(
        "/config/providers",
        headers=API_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "count": 1,
        "providers": [
            {
                "id": 21,
                "openemr_fhir_id": "pract-1",
                "openemr_provider_npi": "1234567890",
                "openemr_provider_name": "Dr Jane Doe",
                "zoom_user_id": "u-1",
                "zoom_user_email": "jane@example.com",
                "zoom_user_name": "Dr Jane Doe",
                "created_at": "2026-01-03T00:00:00+00:00",
            }
        ],
    }


def test_list_provider_mappings_maps_value_error_to_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.providers.get_provider_mappings",
        lambda account_id: (_ for _ in ()).throw(ValueError("not found")),
    )

    response = client.get(
        "/config/providers",
        headers=API_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_list_provider_mappings_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.providers.get_provider_mappings",
        lambda account_id: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.get(
        "/config/providers",
        headers=API_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}


def test_delete_provider_mapping_requires_zoom_account_id(client):
    response = client.delete("/config/providers/10", headers=API_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_delete_provider_mapping_success(client, monkeypatch):
    monkeypatch.setattr("app.services.providers.delete_provider_mapping", lambda account_id, mapping_id: None)

    response = client.delete(
        "/config/providers/10",
        headers=API_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted", "id": 10}


def test_delete_provider_mapping_maps_value_error_to_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.providers.delete_provider_mapping",
        lambda account_id, mapping_id: (_ for _ in ()).throw(ValueError("not found")),
    )

    response = client.delete(
        "/config/providers/10",
        headers=API_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_delete_provider_mapping_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.providers.delete_provider_mapping",
        lambda account_id, mapping_id: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.delete(
        "/config/providers/10",
        headers=API_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}
