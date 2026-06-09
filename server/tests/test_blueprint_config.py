from datetime import datetime, timezone
from types import SimpleNamespace

from auth_utils import AUTH_HEADERS
from app.extensions import db
from app.models import AccountConfig, ZoomAccount


def _create_account(app, account_id: str, *, is_active: bool = True) -> ZoomAccount:
    with app.app_context():
        account = ZoomAccount(
            nickname=None,
            account_id=account_id,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{account_id}/private.pem",
            kid=f"zoomly-{account_id}",
            tenant_id=f"t{account_id[-9:]}",
            is_active=is_active,
        )
        db.session.add(account)
        db.session.add(
            AccountConfig(
                account_id=account_id,
                timezone="America/New_York",
            )
        )
        db.session.commit()
        return account


def _fake_registration_result(
    *,
    nickname=None,
    account_id="acct-1",
    client_id="client-id",
    openemr_client_id="openemr-client-id",
    tenant_id="tenant-123",
    ehr_context_username=None,
    kid="zoomly-acct-1",
    timezone_name="America/New_York",
    note_writeback_mode="both",
):
    return (
        SimpleNamespace(
            nickname=nickname,
            account_id=account_id,
            client_id=client_id,
            openemr_client_id=openemr_client_id,
            tenant_id=tenant_id,
            ehr_context_username=ehr_context_username,
            kid=kid,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        SimpleNamespace(timezone=timezone_name, note_writeback_mode=note_writeback_mode),
    )


def test_register_endpoint_requires_json_body(client):
    response = client.post("/config/register", headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be JSON"}


def test_register_endpoint_requires_all_fields(client):
    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
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
    fake_result = _fake_registration_result(
        nickname="Demo Account",
        tenant_id="tenant-abc",
        ehr_context_username="ehr-user",
    )
    monkeypatch.setattr("app.blueprints.config.config_routes.register_zoom_account", lambda **kwargs: fake_result)

    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret",
            "zoom_webhook_secret": "webhook-secret",
            "contact_email": "admin@example.com",
            "nickname": "Demo Account",
            "ehr_context_username": "ehr-user",
            "ehr_context_password": "ehr-pass",
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "status": "registered",
        "nickname": "Demo Account",
        "zoom_account_id": "acct-1",
        "zoom_client_id": "client-id",
        "openemr_client_id": "openemr-client-id",
        "tenant_id": "tenant-abc",
        "ehr_context_username": "ehr-user",
        "note_writeback_mode": "both",
        "kid": "zoomly-acct-1",
        "timezone": "America/New_York",
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def test_register_endpoint_audits_without_secret_values(client, monkeypatch):
    fake_result = _fake_registration_result(
        account_id="acct-1",
        client_id="client-id",
        ehr_context_username="ehr-user",
    )
    calls = []
    monkeypatch.setattr("app.blueprints.config.config_routes.register_zoom_account", lambda **kwargs: fake_result)
    monkeypatch.setattr("app.blueprints.config.config_routes.write_audit_log", lambda **kwargs: calls.append(kwargs))

    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret-value",
            "zoom_webhook_secret": "webhook-secret-value",
            "contact_email": "admin@example.com",
            "ehr_context_username": "ehr-user",
            "ehr_context_password": "ehr-password-value",
            "timezone": "America/Denver",
        },
    )

    assert response.status_code == 201
    audit_call = calls[0]
    assert audit_call["event_type"] == "config.registration_created"
    assert audit_call["success"] is True
    assert audit_call["zoom_account_id"] == "acct-1"
    assert audit_call["detail"] == {
        "credential_fields": [
            "contact_email",
            "ehr_context_password",
            "ehr_context_username",
            "zoom_client_id",
            "zoom_client_secret",
            "zoom_webhook_secret",
        ],
        "config_fields": ["timezone"],
    }
    detail_text = str(audit_call["detail"])
    assert "client-secret-value" not in detail_text
    assert "webhook-secret-value" not in detail_text
    assert "ehr-password-value" not in detail_text


def test_register_endpoint_maps_value_error_to_400(client, monkeypatch):
    def _raise(**kwargs):
        raise ValueError("duplicate account")

    monkeypatch.setattr("app.blueprints.config.config_routes.register_zoom_account", _raise)
    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
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

    monkeypatch.setattr("app.blueprints.config.config_routes.register_zoom_account", _raise)
    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
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


def test_register_endpoint_passes_timezone_to_service(client, monkeypatch):
    captured = {}

    def fake_register(**kwargs):
        captured.update(kwargs)
        return _fake_registration_result(timezone_name=kwargs["timezone"])

    monkeypatch.setattr("app.blueprints.config.config_routes.register_zoom_account", fake_register)

    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret",
            "zoom_webhook_secret": "webhook-secret",
            "contact_email": "admin@example.com",
            "timezone": "America/Chicago",
        },
    )

    assert response.status_code == 201
    assert captured["timezone"] == "America/Chicago"
    assert response.get_json()["timezone"] == "America/Chicago"


def test_register_endpoint_defaults_timezone_when_missing(client, monkeypatch):
    captured = {}

    def fake_register(**kwargs):
        captured.update(kwargs)
        return _fake_registration_result(timezone_name=kwargs["timezone"])

    monkeypatch.setattr("app.blueprints.config.config_routes.register_zoom_account", fake_register)

    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret",
            "zoom_webhook_secret": "webhook-secret",
            "contact_email": "admin@example.com",
        },
    )

    assert response.status_code == 201
    assert captured["timezone"] == "America/New_York"
    assert response.get_json()["timezone"] == "America/New_York"


def test_register_endpoint_passes_nickname_to_service(client, monkeypatch):
    captured = {}

    def fake_register(**kwargs):
        captured.update(kwargs)
        return _fake_registration_result(
            nickname=kwargs["nickname"],
            timezone_name=kwargs["timezone"],
        )

    monkeypatch.setattr("app.blueprints.config.config_routes.register_zoom_account", fake_register)

    response = client.post(
        "/config/register",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "zoom_client_id": "client-id",
            "zoom_client_secret": "client-secret",
            "zoom_webhook_secret": "webhook-secret",
            "contact_email": "admin@example.com",
            "nickname": "North Clinic",
        },
    )

    assert response.status_code == 201
    assert captured["nickname"] == "North Clinic"
    assert response.get_json()["nickname"] == "North Clinic"


def test_update_registration_requires_json_body(client):
    response = client.patch("/config/register/acct-1", headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be JSON"}


def test_update_registration_success(client, app):
    _create_account(app, "acct-1", is_active=True)

    response = client.patch(
        "/config/register/acct-1",
        headers=AUTH_HEADERS,
        json={
            "nickname": "South Clinic",
            "zoom_client_secret": "new-client-secret",
            "zoom_webhook_secret": "new-webhook-secret",
            "ehr_context_username": "ehr-user",
            "ehr_context_password": "ehr-pass",
            "timezone": "America/Denver",
            "demo_patient_email_override_enabled": True,
            "demo_patient_email_override": "demo-patient@example.com",
            "demo_patient_phone_override_enabled": True,
            "demo_patient_phone_override": "+13035550199",
            "note_writeback_mode": "soap_only",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "updated"
    assert body["zoom_account_id"] == "acct-1"
    assert body["nickname"] == "South Clinic"
    assert body["timezone"] == "America/Denver"
    assert body["ehr_context_username"] == "ehr-user"
    assert body["demo_patient_email_override_enabled"] is True
    assert body["demo_patient_email_override"] == "demo-patient@example.com"
    assert body["demo_patient_phone_override_enabled"] is True
    assert body["demo_patient_phone_override"] == "+13035550199"
    assert body["note_writeback_mode"] == "soap_only"
    assert isinstance(body["updated_at"], str)


def test_update_registration_audits_changed_fields_without_secret_values(client, app, monkeypatch):
    _create_account(app, "acct-1", is_active=True)
    calls = []
    monkeypatch.setattr("app.blueprints.config.config_routes.write_audit_log", lambda **kwargs: calls.append(kwargs))

    response = client.patch(
        "/config/register/acct-1",
        headers=AUTH_HEADERS,
        json={
            "nickname": "South Clinic",
            "zoom_client_secret": "new-client-secret-value",
            "zoom_webhook_secret": "new-webhook-secret-value",
            "ehr_context_username": "ehr-user",
            "ehr_context_password": "new-ehr-password-value",
            "timezone": "America/Denver",
            "note_writeback_mode": "clinical_note_only",
        },
    )

    assert response.status_code == 200
    audit_call = calls[0]
    assert audit_call["event_type"] == "config.registration_updated"
    assert audit_call["success"] is True
    assert audit_call["zoom_account_id"] == "acct-1"
    assert audit_call["detail"] == {
        "credential_fields": [
            "ehr_context_password",
            "ehr_context_username",
            "nickname",
            "zoom_client_secret",
            "zoom_webhook_secret",
        ],
        "config_fields": ["note_writeback_mode", "timezone"],
    }
    detail_text = str(audit_call["detail"])
    assert "new-client-secret-value" not in detail_text
    assert "new-webhook-secret-value" not in detail_text
    assert "new-ehr-password-value" not in detail_text


def test_update_registration_passes_false_override_flag(client, app):
    _create_account(app, "acct-1", is_active=True)

    response = client.patch(
        "/config/register/acct-1",
        headers=AUTH_HEADERS,
        json={"demo_patient_email_override_enabled": False},
    )

    assert response.status_code == 200
    assert response.get_json()["demo_patient_email_override_enabled"] is False


def test_update_registration_maps_value_error_to_400(client, monkeypatch):
    response = client.patch(
        "/config/register/acct-1",
        headers=AUTH_HEADERS,
        json={"unknown": "value"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "No valid fields provided"}


def test_update_registration_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes.update_zoom_account_credentials",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.patch(
        "/config/register/acct-1",
        headers=AUTH_HEADERS,
        json={"nickname": "South Clinic"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Update failed", "detail": "db down"}


def test_deregister_endpoint_success(client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.blueprints.config.config_routes.deregister_zoom_account", lambda account_id: None)
    monkeypatch.setattr("app.blueprints.config.config_routes.write_audit_log", lambda **kwargs: calls.append(kwargs))
    response = client.delete("/config/register/acct-1", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.get_json() == {"status": "deregistered", "zoom_account_id": "acct-1"}
    assert calls == [
        {
            "event_type": "config.registration_deleted",
            "success": True,
            "zoom_account_id": "acct-1",
        }
    ]


def test_deregister_endpoint_maps_not_found_to_404(client, monkeypatch):
    def _raise(account_id):
        raise ValueError("not found")

    monkeypatch.setattr("app.blueprints.config.config_routes.deregister_zoom_account", _raise)
    response = client.delete("/config/register/acct-1", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_deregister_endpoint_maps_unexpected_error_to_500(client, monkeypatch):
    def _raise(account_id):
        raise RuntimeError("db down")

    monkeypatch.setattr("app.blueprints.config.config_routes.deregister_zoom_account", _raise)
    response = client.delete("/config/register/acct-1", headers=AUTH_HEADERS)
    assert response.status_code == 500
    assert response.get_json() == {"error": "Deregistration failed", "detail": "db down"}


def test_list_registrations_returns_summary(client, app):
    with app.app_context():
        db.session.add(
            ZoomAccount(
                nickname="Primary Clinic",
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
            AccountConfig(
                account_id="acct-1",
                timezone="America/Denver",
                demo_patient_email_override_enabled=True,
                demo_patient_email_override="demo-patient+acct1@example.com",
                demo_patient_phone_override_enabled=True,
                demo_patient_phone_override="+13035550111",
                note_writeback_mode="soap_only",
            )
        )
        db.session.add(
            ZoomAccount(
                nickname=None,
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
        db.session.add(AccountConfig(account_id="acct-2", timezone="America/New_York"))
        db.session.commit()

    response = client.get("/config/registrations", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 2
    assert len(body["registrations"]) == 2

    acct1 = next(item for item in body["registrations"] if item["zoom_account_id"] == "acct-1")
    acct2 = next(item for item in body["registrations"] if item["zoom_account_id"] == "acct-2")

    assert acct1["nickname"] == "Primary Clinic"
    assert acct1["openemr_client_id"] == "openemr-client-id"
    assert acct1["kid"] == "zoomly-acct-1"
    assert acct1["is_active"] is True
    assert acct1["has_zoom_token"] is True
    assert acct1["has_openemr_token"] is True
    assert acct1["timezone"] == "America/Denver"
    assert acct1["demo_patient_email_override_enabled"] is True
    assert acct1["demo_patient_email_override"] == "demo-patient+acct1@example.com"
    assert acct1["demo_patient_phone_override_enabled"] is True
    assert acct1["demo_patient_phone_override"] == "+13035550111"
    assert acct1["note_writeback_mode"] == "soap_only"
    assert isinstance(acct1["created_at"], str)
    assert isinstance(acct1["updated_at"], str)

    assert acct2["nickname"] is None
    assert acct2["is_active"] is False
    assert acct2["has_zoom_token"] is False
    assert acct2["has_openemr_token"] is False
    assert acct2["timezone"] == "America/New_York"
    assert acct2["demo_patient_email_override_enabled"] is False
    assert acct2["demo_patient_email_override"] is None
    assert acct2["demo_patient_phone_override_enabled"] is False
    assert acct2["demo_patient_phone_override"] is None
    assert acct2["note_writeback_mode"] == "both"  # fallback when no AccountConfig


def test_verify_registration_returns_404_for_unknown_account(client):
    response = client.post("/config/register/missing/verify", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.get_json() == {"error": "No active registration found for account missing"}


def test_verify_registration_returns_success_true(client, app, monkeypatch):
    _create_account(app, "acct-verify", is_active=True)
    with app.app_context():
        account = ZoomAccount.query.filter_by(account_id="acct-verify").first()
        account.zoom_access_token = "zoom-token"
        db.session.commit()
    monkeypatch.setattr(
        "app.blueprints.config.config_routes.verify_openemr_token_for_account",
        lambda account: True,
    )

    response = client.post("/config/register/acct-verify/verify", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.get_json()
    assert body["nickname"] is None
    assert body["zoom_account_id"] == "acct-verify"
    assert body["openemr_verified"] is True
    # zoom_verified is a bool — never leak the access token to the browser
    assert body["zoom_verified"] is True
    assert body["message"] == "OpenEMR and Zoom token verified successfully"


def test_verify_registration_returns_success_false(client, app, monkeypatch):
    _create_account(app, "acct-verify", is_active=True)
    monkeypatch.setattr(
        "app.blueprints.config.config_routes.verify_openemr_token_for_account",
        lambda account: False,
    )

    response = client.post("/config/register/acct-verify/verify", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.get_json()
    assert body["nickname"] is None
    assert body["zoom_account_id"] == "acct-verify"
    assert body["openemr_verified"] is False
    assert body["zoom_verified"] is False
    assert "OpenEMR token verification failed" in body["message"]


def test_create_user_mapping_requires_body(client):
    response = client.post("/config/providers", headers=AUTH_HEADERS, json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body is required"}


def test_create_user_mapping_requires_envelope_fields(client):
    """The route validates only the always-required envelope; per-role field
    requirements are enforced in the service layer (raised as ValueError → 400).
    """
    response = client.post(
        "/config/providers",
        headers=AUTH_HEADERS,
        json={"openemr_fhir_id": "pract-1"},  # missing zoom_account_id + zoom_user_email
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Missing required fields: zoom_account_id, zoom_user_email"
    }


def test_create_user_mapping_success(client, monkeypatch):
    fake_mapping = SimpleNamespace(
        id=12,
        is_provider=True,
        is_zcc_agent=False,
        openemr_user_id="10",
        openemr_provider_npi="1234567890",
        openemr_provider_name="Dr Jane Doe",
        openemr_facility_id=1,
        openemr_facility_name="Zoomly Medical Center",
        zoom_user_id="u-1",
        zoom_user_email="jane@example.com",
        zoom_user_name="Dr Jane Doe",
        zoom_user_timezone="America/Los_Angeles",
        zcc_user_id=None,
        agent_role=None,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    captured = {}
    def _capture_create(**kwargs):
        captured.update(kwargs)
        return fake_mapping
    monkeypatch.setattr("app.blueprints.config.config_routes._create_user_mapping", _capture_create)

    response = client.post(
        "/config/providers",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "is_provider": True,
            "is_zcc_agent": False,
            "openemr_fhir_id": "pract-1",
            "openemr_provider_npi": "1234567890",
            "openemr_user_id": "10",
            "openemr_facility_id": 1,
            "openemr_facility_name": "Zoomly Medical Center",
            "zoom_user_id": "u-1",
            "zoom_user_email": "jane@example.com",
            "zoom_user_type": 2,
            "zoom_user_timezone": "America/Los_Angeles",
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "id": 12,
        "is_provider": True,
        "is_zcc_agent": False,
        "openemr_user_id": "10",
        "openemr_provider_npi": "1234567890",
        "openemr_provider_name": "Dr Jane Doe",
        "openemr_facility_id": 1,
        "openemr_facility_name": "Zoomly Medical Center",
        "zoom_user_id": "u-1",
        "zoom_user_email": "jane@example.com",
        "zoom_user_name": "Dr Jane Doe",
        "zoom_user_timezone": "America/Los_Angeles",
        "zcc_user_id": None,
        "agent_role": None,
        "created_at": "2026-01-02T00:00:00+00:00",
    }
    # Facility + provider TZ + role flags are threaded through to the service-layer
    # call so they actually land on the new UserMapping row.
    assert captured["is_provider"] is True
    assert captured["is_zcc_agent"] is False
    assert captured["openemr_facility_id"] == 1
    assert captured["openemr_facility_name"] == "Zoomly Medical Center"
    assert captured["zoom_user_timezone"] == "America/Los_Angeles"


def test_create_user_mapping_maps_value_error_to_400(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._create_user_mapping",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("duplicate mapping")),
    )

    response = client.post(
        "/config/providers",
        headers=AUTH_HEADERS,
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


def test_create_user_mapping_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._create_user_mapping",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.post(
        "/config/providers",
        headers=AUTH_HEADERS,
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


def test_list_user_mappings_requires_zoom_account_id(client):
    response = client.get("/config/providers", headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_list_user_mappings_success(client, monkeypatch):
    fake_mappings = [
        SimpleNamespace(
            id=21,
            openemr_fhir_id="pract-1",
            openemr_provider_npi="1234567890",
            openemr_user_id="10",
            openemr_provider_name="Dr Jane Doe",
            openemr_facility_id=1,
            openemr_facility_name="Zoomly Medical Center",
            zoom_user_id="u-1",
            zoom_user_email="jane@example.com",
            zoom_user_name="Dr Jane Doe",
            zoom_user_timezone="America/Denver",
            is_provider=True,
            is_zcc_agent=False,
            zcc_user_id=None,
            agent_role=None,
            created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
    ]
    monkeypatch.setattr("app.blueprints.config.config_routes._get_user_mappings", lambda account_id: fake_mappings)

    response = client.get(
        "/config/providers",
        headers=AUTH_HEADERS,
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
                "openemr_user_id": "10",
                "openemr_provider_name": "Dr Jane Doe",
                "openemr_facility_id": 1,
                "openemr_facility_name": "Zoomly Medical Center",
                "zoom_user_id": "u-1",
                "zoom_user_email": "jane@example.com",
                "zoom_user_name": "Dr Jane Doe",
                "zoom_user_timezone": "America/Denver",
                "is_provider": True,
                "is_zcc_agent": False,
                "zcc_user_id": None,
                "agent_role": None,
                "created_at": "2026-01-03T00:00:00+00:00",
            }
        ],
    }


def test_list_user_mappings_maps_value_error_to_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._get_user_mappings",
        lambda account_id: (_ for _ in ()).throw(ValueError("not found")),
    )

    response = client.get(
        "/config/providers",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_list_user_mappings_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._get_user_mappings",
        lambda account_id: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.get(
        "/config/providers",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}


def test_delete_user_mapping_requires_zoom_account_id(client):
    response = client.delete("/config/providers/10", headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_delete_user_mapping_success(client, monkeypatch):
    monkeypatch.setattr("app.blueprints.config.config_routes._delete_user_mapping", lambda account_id, npi: None)

    response = client.delete(
        "/config/providers/10",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted", "openemr_user_id": "10"}


def test_delete_user_mapping_maps_value_error_to_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._delete_user_mapping",
        lambda account_id, npi: (_ for _ in ()).throw(ValueError("not found")),
    )

    response = client.delete(
        "/config/providers/10",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_delete_user_mapping_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._delete_user_mapping",
        lambda account_id, npi: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.delete(
        "/config/providers/10",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}


def test_create_appointment_filter_requires_body(client):
    response = client.post("/config/appointment-types", headers=AUTH_HEADERS, json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body is required"}


def test_create_appointment_filter_requires_fields(client):
    response = client.post(
        "/config/appointment-types",
        headers=AUTH_HEADERS,
        json={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing required fields: openemr_type_id, openemr_type_name"}


def test_create_appointment_filter_success(client, monkeypatch):
    fake_filter = SimpleNamespace(
        id=33,
        openemr_type_id="5",
        openemr_type_name="Telehealth Follow-up",
        created_at=datetime(2026, 1, 4, tzinfo=timezone.utc),
    )
    monkeypatch.setattr("app.blueprints.config.config_routes._create_appointment_filter", lambda **kwargs: fake_filter)

    response = client.post(
        "/config/appointment-types",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "openemr_type_id": "5",
            "openemr_type_name": "Telehealth Follow-up",
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "id": 33,
        "openemr_type_id": "5",
        "openemr_type_name": "Telehealth Follow-up",
        "created_at": "2026-01-04T00:00:00+00:00",
    }


def test_create_appointment_filter_maps_value_error_to_400(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._create_appointment_filter",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("duplicate appointment type")),
    )

    response = client.post(
        "/config/appointment-types",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "openemr_type_id": "5",
            "openemr_type_name": "Telehealth Follow-up",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "duplicate appointment type"}


def test_create_appointment_filter_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._create_appointment_filter",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.post(
        "/config/appointment-types",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-1",
            "openemr_type_id": "5",
            "openemr_type_name": "Telehealth Follow-up",
        },
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}


def test_list_appointment_filters_requires_zoom_account_id(client):
    response = client.get("/config/appointment-types", headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_list_appointment_filters_success(client, monkeypatch):
    fake_filters = [
        SimpleNamespace(
            id=44,
            openemr_type_id="7",
            openemr_type_name="New Patient Consult",
            created_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
    ]
    monkeypatch.setattr("app.blueprints.config.config_routes._get_appointment_filters", lambda account_id: fake_filters)

    response = client.get(
        "/config/appointment-types",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "count": 1,
        "appointment_types": [
            {
                "id": 44,
                "openemr_type_id": "7",
                "openemr_type_name": "New Patient Consult",
                "created_at": "2026-01-05T00:00:00+00:00",
            }
        ],
    }


def test_list_appointment_filters_maps_value_error_to_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._get_appointment_filters",
        lambda account_id: (_ for _ in ()).throw(ValueError("not found")),
    )

    response = client.get(
        "/config/appointment-types",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_list_appointment_filters_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._get_appointment_filters",
        lambda account_id: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.get(
        "/config/appointment-types",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}


def test_delete_appointment_filter_requires_zoom_account_id(client):
    response = client.delete("/config/appointment-types/7", headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_delete_appointment_filter_success(client, monkeypatch):
    monkeypatch.setattr("app.blueprints.config.config_routes._delete_appointment_filter", lambda **kwargs: None)

    response = client.delete(
        "/config/appointment-types/7",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted", "appointment_type_id": "7"}


def test_delete_appointment_filter_maps_value_error_to_404(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._delete_appointment_filter",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("not found")),
    )

    response = client.delete(
        "/config/appointment-types/7",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_delete_appointment_filter_maps_unexpected_error_to_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.config.config_routes._delete_appointment_filter",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    response = client.delete(
        "/config/appointment-types/7",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "db down"}


def test_set_ehr_context_credentials_audits_without_password_value(client, app, monkeypatch):
    _create_account(app, "acct-ehr", is_active=True)
    calls = []
    monkeypatch.setattr("app.blueprints.config.config_routes.write_audit_log", lambda **kwargs: calls.append(kwargs))

    response = client.post(
        "/config/ehr-credentials",
        headers=AUTH_HEADERS,
        json={
            "zoom_account_id": "acct-ehr",
            "ehr_context_username": "ehr-user",
            "ehr_context_password": "ehr-password-value",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "updated",
        "zoom_account_id": "acct-ehr",
        "ehr_context_username": "ehr-user",
        "tenant_id": "tacct-ehr",
    }
    audit_call = calls[0]
    assert audit_call["event_type"] == "config.ehr_credentials_updated"
    assert audit_call["success"] is True
    assert audit_call["zoom_account_id"] == "acct-ehr"
    assert audit_call["detail"] == {
        "credential_fields": ["ehr_context_password", "ehr_context_username"],
    }
    assert "ehr-password-value" not in str(audit_call["detail"])

    with app.app_context():
        account = ZoomAccount.query.filter_by(account_id="acct-ehr").first()
        assert account.ehr_context_username == "ehr-user"
        assert account.ehr_context_password_hash


def test_features_returns_db_browser_true_when_enabled(app, client):
    app.config["ENABLE_DBGATE"] = True
    response = client.get("/config/features", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.get_json() == {"db_browser": True}


def test_features_returns_db_browser_false_when_disabled(app, client):
    app.config["ENABLE_DBGATE"] = False
    response = client.get("/config/features", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.get_json() == {"db_browser": False}


def test_features_returns_db_browser_false_when_unset(app, client):
    app.config.pop("ENABLE_DBGATE", None)
    response = client.get("/config/features", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.get_json() == {"db_browser": False}


def test_features_requires_auth(client):
    response = client.get("/config/features")
    assert response.status_code == 401
