from app.extensions import db
from app.models import ZoomAccount


def _create_account(account_id: str, *, is_active: bool = True) -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path="/tmp/private.pem",
        kid=f"zoomly-{account_id}",
        is_active=is_active,
    )
    db.session.add(account)
    db.session.commit()
    return account


def test_get_providers_returns_500_when_api_key_not_configured(client, app):
    app.config["API_KEY"] = None
    response = client.get("/openemr/providers")
    assert response.status_code == 500
    assert response.get_json() == {"error": "API_KEY not configured on server"}


def test_get_providers_returns_401_for_invalid_api_key(client, app):
    app.config["API_KEY"] = "expected-key"

    response = client.get("/openemr/providers", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid or missing API key"}


def test_get_providers_requires_zoom_account_id(client, app):
    app.config["API_KEY"] = "expected-key"

    response = client.get("/openemr/providers", headers={"X-API-Key": "expected-key"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_get_providers_returns_404_for_unknown_account(client, app):
    app.config["API_KEY"] = "expected-key"

    response = client.get(
        "/openemr/providers",
        headers={"X-API-Key": "expected-key"},
        query_string={"zoom_account_id": "missing-account"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "No active registration found for account missing-account"}


def test_get_providers_success_returns_provider_list(client, app, monkeypatch):
    app.config["API_KEY"] = "expected-key"

    with app.app_context():
        _create_account("acct-1", is_active=True)

    captured = {}

    def fake_get_practitioners(account, search=None, practitioner_id=None):
        captured["account_id"] = account.account_id
        captured["search"] = search
        captured["practitioner_id"] = practitioner_id
        return [
            {
                "fhir_id": "provider-1",
                "active": True,
                "first_name": "Jane",
                "last_name": "Doe",
                "full_name": "Dr Jane Doe",
                "npi": "1234567890",
                "email": "jane@example.com",
            }
        ]

    monkeypatch.setattr("app.blueprints.openemr.openemr_routes.get_practitioners", fake_get_practitioners)

    response = client.get(
        "/openemr/providers",
        headers={"X-API-Key": "expected-key"},
        query_string={
            "zoom_account_id": "acct-1",
            "search": "doe",
            "id": "provider-1",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "count": 1,
        "providers": [
            {
                "fhir_id": "provider-1",
                "active": True,
                "first_name": "Jane",
                "last_name": "Doe",
                "full_name": "Dr Jane Doe",
                "npi": "1234567890",
                "email": "jane@example.com",
            }
        ],
    }
    assert captured == {
        "account_id": "acct-1",
        "search": "doe",
        "practitioner_id": "provider-1",
    }


def test_get_providers_maps_service_error_to_500(client, app, monkeypatch):
    app.config["API_KEY"] = "expected-key"

    with app.app_context():
        _create_account("acct-1", is_active=True)

    def fake_get_practitioners(account, search=None, practitioner_id=None):
        raise RuntimeError("openemr timeout")

    monkeypatch.setattr("app.blueprints.openemr.openemr_routes.get_practitioners", fake_get_practitioners)

    response = client.get(
        "/openemr/providers",
        headers={"X-API-Key": "expected-key"},
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "openemr timeout"}


def test_get_appointment_types_returns_500_when_api_key_not_configured(client, app):
    app.config["API_KEY"] = None
    response = client.get("/openemr/appointment-types")
    assert response.status_code == 500
    assert response.get_json() == {"error": "API_KEY not configured on server"}


def test_get_appointment_types_returns_401_for_invalid_api_key(client, app):
    app.config["API_KEY"] = "expected-key"
    response = client.get("/openemr/appointment-types", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid or missing API key"}


def test_get_appointment_types_success(client, app, monkeypatch):
    app.config["API_KEY"] = "expected-key"
    monkeypatch.setattr(
        "app.blueprints.openemr.openemr_routes.get_appointment_types_list",
        lambda: [
            {
                "id": "1",
                "name": "New Patient",
                "description": "Initial consult",
                "duration_seconds": 1800,
                "color": "#33AA55",
            }
        ],
    )

    response = client.get("/openemr/appointment-types", headers={"X-API-Key": "expected-key"})

    assert response.status_code == 200
    assert response.get_json() == {
        "count": 1,
        "appointment_types": [
            {
                "id": "1",
                "name": "New Patient",
                "description": "Initial consult",
                "duration_seconds": 1800,
                "color": "#33AA55",
            }
        ],
    }


def test_get_appointment_types_maps_service_error_to_500(client, app, monkeypatch):
    app.config["API_KEY"] = "expected-key"
    monkeypatch.setattr(
        "app.blueprints.openemr.openemr_routes.get_appointment_types_list",
        lambda: (_ for _ in ()).throw(RuntimeError("db unavailable")),
    )

    response = client.get("/openemr/appointment-types", headers={"X-API-Key": "expected-key"})

    assert response.status_code == 500
    assert response.get_json() == {"error": "db unavailable"}
