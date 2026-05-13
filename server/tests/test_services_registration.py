import requests
import pytest

from app.extensions import db
from app.models import AccountConfig, ZoomAccount
from app.services.registration import registration


def _create_account(account_id: str, *, is_active: bool = True, **overrides) -> ZoomAccount:
    account = ZoomAccount(
        nickname=overrides.get("nickname"),
        account_id=account_id,
        client_id=overrides.get("client_id", "zoom-client-id"),
        client_secret=overrides.get("client_secret", "zoom-client-secret"),
        webhook_secret=overrides.get("webhook_secret", "zoom-webhook-secret"),
        openemr_client_id=overrides.get("openemr_client_id", "openemr-client-id"),
        openemr_client_secret=overrides.get("openemr_client_secret", "openemr-client-secret"),
        openemr_registration_access_token=overrides.get("openemr_registration_access_token", "registration-token"),
        openemr_registration_client_uri=overrides.get("openemr_registration_client_uri", "http://openemr.internal/client/1"),
        private_key_path=overrides.get("private_key_path", "/tmp/private.pem"),
        kid=overrides.get("kid", f"zoomly-{account_id}"),
        is_active=is_active,
    )
    db.session.add(account)
    db.session.add(
        AccountConfig(
            account_id=account_id,
            timezone=overrides.get("timezone", "America/New_York"),
            demo_patient_email_override_enabled=overrides.get(
                "demo_patient_email_override_enabled", False
            ),
            demo_patient_email_override=overrides.get("demo_patient_email_override"),
            demo_patient_phone_override_enabled=overrides.get(
                "demo_patient_phone_override_enabled", False
            ),
            demo_patient_phone_override=overrides.get("demo_patient_phone_override"),
            allow_shared_zoom_user=overrides.get("allow_shared_zoom_user", False),
            note_writeback_mode=overrides.get("note_writeback_mode", "both"),
        )
    )
    db.session.commit()
    return account


def test_register_with_openemr_posts_expected_payload(app, monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"client_id": "openemr-client-id"}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr(registration.requests, "post", fake_post)

    with app.app_context():
        response = registration._register_with_openemr("acct-1", "admin@example.com")

    assert response == {"client_id": "openemr-client-id"}
    assert captured["url"] == "http://openemr.internal/oauth2/default/registration"
    assert captured["json"]["client_name"] == "Zoomly Bridge - acct-1"
    assert captured["json"]["contacts"] == ["admin@example.com"]
    assert captured["json"]["scope"] == "system/Patient.read system/Appointment.read system/Encounter.read"
    assert captured["json"]["jwks_uri"] == "http://zoom-bridge:5000/.well-known/jwks.json"
    assert captured["json"]["redirect_uris"] == ["http://zoom-bridge:5000/callback"]
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["timeout"] == 15


def test_deregister_from_openemr_swallows_errors(monkeypatch):
    def fake_delete(*args, **kwargs):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(registration.requests, "delete", fake_delete)

    registration._deregister_from_openemr("http://openemr.internal/client/1", "token")


def test_register_zoom_account_rejects_invalid_zoom_credentials(app, monkeypatch):
    cleanup_called = {}
    deregister_called = {}

    monkeypatch.setattr(registration, "validate_zoom_credentials", lambda account: False)
    monkeypatch.setattr(registration, "_enable_openemr_client", lambda zoom_account_id, openemr_client_id: None)
    monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
    monkeypatch.setattr(
        registration,
        "_register_with_openemr",
        lambda account_id, contact_email: {
            "client_id": "openemr-client-id",
            "registration_access_token": "registration-token",
            "registration_client_uri": "https://openemr.public/oauth2/default/client/abc",
        },
    )
    monkeypatch.setattr(
        registration,
        "_deregister_from_openemr",
        lambda uri, token: deregister_called.__setitem__("call", (uri, token)),
    )
    monkeypatch.setattr(
        registration,
        "delete_keypair",
        lambda account_id: cleanup_called.__setitem__("account_id", account_id),
    )

    with app.app_context():
        with pytest.raises(ValueError, match="Zoom credential validation failed"):
            registration.register_zoom_account(
                None,
                "acct-invalid",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                None,
                None,
                "admin@example.com",
            )
        record = ZoomAccount.query.filter_by(account_id="acct-invalid").first()

    assert cleanup_called["account_id"] == "acct-invalid"
    assert deregister_called["call"] == (
        "http://openemr.internal/oauth2/default/client/abc",
        "registration-token",
    )
    assert record is None


def test_register_zoom_account_rejects_duplicate_active(app, monkeypatch):
    with app.app_context():
        _create_account("acct-dup", is_active=True)
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda *args: True)

        with pytest.raises(ValueError, match="already registered and active"):
            registration.register_zoom_account(
                None,
                "acct-dup",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                None,
                None,
                "admin@example.com",
            )


def test_register_zoom_account_replaces_inactive_record(app, monkeypatch):
    with app.app_context():
        _create_account("acct-inactive", is_active=False)
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda account: True)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
        monkeypatch.setattr(registration, "_enable_openemr_client", lambda zoom_account_id, openemr_client_id: None)
        monkeypatch.setattr(
            registration,
            "_register_with_openemr",
            lambda account_id, contact_email: {
                "client_id": "new-openemr-client-id",
                "client_secret": "new-openemr-client-secret",
                "registration_access_token": "registration-token",
                "registration_client_uri": "https://openemr.public/oauth2/default/client/abc",
            },
        )

        account, config = registration.register_zoom_account(
            None,
            "acct-inactive",
            "zoom-client-id",
            "zoom-client-secret",
            "webhook-secret",
            None,
            None,
            "admin@example.com",
        )
        records = ZoomAccount.query.filter_by(account_id="acct-inactive").all()
        config_account_id = config.account_id

    assert len(records) == 1
    assert records[0].account_id == account.account_id
    assert account.is_active is True
    assert config_account_id == "acct-inactive"


def test_register_zoom_account_cleans_up_keys_when_openemr_registration_fails(app, monkeypatch):
    cleanup_called = {}

    with app.app_context():
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda account: True)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
        monkeypatch.setattr(registration, "_register_with_openemr", lambda *args: (_ for _ in ()).throw(requests.HTTPError("bad request")))
        monkeypatch.setattr(registration, "delete_keypair", lambda account_id: cleanup_called.__setitem__("account_id", account_id))

        with pytest.raises(requests.HTTPError):
            registration.register_zoom_account(
                None,
                "acct-openemr-fail",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                None,
                None,
                "admin@example.com",
            )

        record = ZoomAccount.query.filter_by(account_id="acct-openemr-fail").first()

    assert cleanup_called["account_id"] == "acct-openemr-fail"
    assert record is None


def test_register_zoom_account_rolls_back_deregisters_and_cleans_keys_on_db_failure(app, monkeypatch):
    cleanup_called = {}
    rollback_called = {"called": False}
    deregister_calls = []

    with app.app_context():
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda account: True)
        monkeypatch.setattr(registration, "_enable_openemr_client", lambda zoom_account_id, openemr_client_id: None)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
        monkeypatch.setattr(
            registration,
            "_register_with_openemr",
            lambda account_id, contact_email: {
                "client_id": "openemr-client-id",
                "registration_access_token": "registration-token",
                "registration_client_uri": "https://openemr.public/oauth2/default/client/abc",
            },
        )
        monkeypatch.setattr(
            registration,
            "_deregister_from_openemr",
            lambda uri, token: deregister_calls.append((uri, token)),
        )
        monkeypatch.setattr(registration, "delete_keypair", lambda account_id: cleanup_called.__setitem__("account_id", account_id))
        monkeypatch.setattr(registration.db.session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("db write failed")))
        monkeypatch.setattr(registration.db.session, "rollback", lambda: rollback_called.__setitem__("called", True))

        with pytest.raises(RuntimeError, match="db write failed"):
            registration.register_zoom_account(
                None,
                "acct-db-fail",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                None,
                None,
                "admin@example.com",
            )

    assert cleanup_called["account_id"] == "acct-db-fail"
    assert rollback_called["called"] is True
    # The (already-enabled) OpenEMR client must be deregistered so we don't
    # leave an orphan in oauth_clients tied to a non-existent Flask account.
    assert deregister_calls == [("https://openemr.public/oauth2/default/client/abc", "registration-token")]


def test_register_zoom_account_success_persists_and_normalizes_client_uri(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda account: True)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
        monkeypatch.setattr(registration, "_enable_openemr_client", lambda zoom_account_id, openemr_client_id: None)
        monkeypatch.setattr(
            registration,
            "_register_with_openemr",
            lambda account_id, contact_email: {
                "client_id": "openemr-client-id",
                "client_secret": "openemr-client-secret",
                "registration_access_token": "registration-token",
                "registration_client_uri": "https://openemr.public/oauth2/default/client/abc",
            },
        )

        account, config = registration.register_zoom_account(
            "Main Clinic",
            "acct-success",
            "zoom-client-id",
            "zoom-client-secret",
            "webhook-secret",
            None,
            None,
            "admin@example.com",
        )

        stored = ZoomAccount.query.filter_by(account_id="acct-success").first()
        config_timezone = config.timezone
        stored_config_exists = stored.config is not None

    assert account.account_id == "acct-success"
    assert account.openemr_client_id == "openemr-client-id"
    assert account.nickname == "Main Clinic"
    assert account.kid == "zoomly-acct-success"
    assert config_timezone == "America/New_York"
    assert account.openemr_registration_client_uri == "http://openemr.internal/oauth2/default/client/abc"
    assert stored is not None
    assert stored_config_exists is True


def test_register_zoom_account_persists_custom_timezone(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda account: True)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
        monkeypatch.setattr(registration, "_enable_openemr_client", lambda zoom_account_id, openemr_client_id: None)
        monkeypatch.setattr(
            registration,
            "_register_with_openemr",
            lambda account_id, contact_email: {
                "client_id": "openemr-client-id",
                "client_secret": "openemr-client-secret",
                "registration_access_token": "registration-token",
                "registration_client_uri": "https://openemr.public/oauth2/default/client/abc",
            },
        )

        registration.register_zoom_account(
            None,
            "acct-custom-tz",
            "zoom-client-id",
            "zoom-client-secret",
            "webhook-secret",
            None,
            None,
            "admin@example.com",
            timezone="America/Los_Angeles",
        )
        stored = ZoomAccount.query.filter_by(account_id="acct-custom-tz").first()
        assert stored is not None
        assert stored.config.timezone == "America/Los_Angeles"


def test_update_zoom_account_updates_editable_fields(app):
    with app.app_context():
        _create_account(
            "acct-update",
            nickname="Old Clinic",
            timezone="America/New_York",
            demo_patient_email_override_enabled=False,
            demo_patient_phone_override_enabled=False,
            demo_patient_email_override=None,
            demo_patient_phone_override=None,
        )

        account = registration.update_zoom_account_credentials(
            zoom_account_id="acct-update",
            nickname="New Clinic",
            zoom_client_secret="new-client-secret",
            zoom_webhook_secret="new-webhook-secret",
        )
        config = registration.update_account_config(
            zoom_account_id="acct-update",
            timezone="America/Denver",
            demo_patient_email_override_enabled=True,
            demo_patient_email_override="demo-patient@example.com",
            demo_patient_phone_override_enabled=True,
            demo_patient_phone_override="+13035550199",
            allow_shared_zoom_user=True,
            note_writeback_mode="clinical_note_only",
        )

        stored = ZoomAccount.query.filter_by(account_id="acct-update").first()
        config_values = {
            "timezone": config.timezone,
            "demo_patient_email_override_enabled": config.demo_patient_email_override_enabled,
            "demo_patient_email_override": config.demo_patient_email_override,
            "demo_patient_phone_override_enabled": config.demo_patient_phone_override_enabled,
            "demo_patient_phone_override": config.demo_patient_phone_override,
            "allow_shared_zoom_user": config.allow_shared_zoom_user,
            "note_writeback_mode": config.note_writeback_mode,
        }

    assert stored is not None
    assert account.account_id == stored.account_id
    assert stored.nickname == "New Clinic"
    assert stored.client_secret == "new-client-secret"
    assert stored.webhook_secret == "new-webhook-secret"
    assert config_values["timezone"] == "America/Denver"
    assert config_values["demo_patient_email_override_enabled"] is True
    assert config_values["demo_patient_email_override"] == "demo-patient@example.com"
    assert config_values["demo_patient_phone_override_enabled"] is True
    assert config_values["demo_patient_phone_override"] == "+13035550199"
    assert config_values["allow_shared_zoom_user"] is True
    assert config_values["note_writeback_mode"] == "clinical_note_only"


def test_update_account_config_updates_false_boolean(app):
    with app.app_context():
        _create_account("acct-update-false", demo_patient_email_override_enabled=True)

        config = registration.update_account_config(
            zoom_account_id="acct-update-false",
            demo_patient_email_override_enabled=False,
        )
        assert config.demo_patient_email_override_enabled is False


def test_update_zoom_account_credentials_raises_when_missing(app):
    with app.app_context():
        with pytest.raises(ValueError, match="No active registration found"):
            registration.update_zoom_account_credentials("missing-account", nickname="New Clinic")


def test_update_zoom_account_credentials_raises_when_no_valid_fields(app):
    with app.app_context():
        _create_account("acct-update-empty")

        with pytest.raises(ValueError, match="No valid fields provided"):
            registration.update_zoom_account_credentials("acct-update-empty")


def test_update_account_config_raises_when_no_valid_fields(app):
    with app.app_context():
        _create_account("acct-config-empty")

        with pytest.raises(ValueError, match="No valid fields provided"):
            registration.update_account_config("acct-config-empty")


def test_deregister_zoom_account_raises_when_missing(app):
    with app.app_context():
        with pytest.raises(ValueError, match="No active registration found"):
            registration.deregister_zoom_account("missing-account")


def test_deregister_zoom_account_calls_openemr_and_deletes_record(app, monkeypatch):
    captured = {}

    with app.app_context():
        _create_account(
            "acct-delete",
            openemr_registration_client_uri="http://openemr.internal/oauth2/default/client/123",
            openemr_registration_access_token="registration-token",
        )
        monkeypatch.setattr(
            registration,
            "_deregister_from_openemr",
            lambda uri, token: captured.__setitem__("openemr", (uri, token)),
        )
        monkeypatch.setattr(registration, "delete_keypair", lambda account_id: captured.__setitem__("keypair", account_id))

        registration.deregister_zoom_account("acct-delete")
        record = ZoomAccount.query.filter_by(account_id="acct-delete").first()

    assert captured["openemr"] == ("http://openemr.internal/oauth2/default/client/123", "registration-token")
    assert captured["keypair"] == "acct-delete"
    assert record is None


def test_deregister_zoom_account_skips_openemr_when_registration_data_missing(app, monkeypatch):
    captured = {"openemr_called": False}

    with app.app_context():
        _create_account(
            "acct-delete-no-openemr",
            openemr_registration_client_uri=None,
            openemr_registration_access_token=None,
        )
        monkeypatch.setattr(
            registration,
            "_deregister_from_openemr",
            lambda *args: captured.__setitem__("openemr_called", True),
        )
        monkeypatch.setattr(registration, "delete_keypair", lambda account_id: captured.__setitem__("keypair", account_id))

        registration.deregister_zoom_account("acct-delete-no-openemr")
        record = ZoomAccount.query.filter_by(account_id="acct-delete-no-openemr").first()

    assert captured["openemr_called"] is False
    assert captured["keypair"] == "acct-delete-no-openemr"
    assert record is None


# ---------------------------------------------------------------------------
# _enable_openemr_client — direct DB UPDATE on oauth_clients.is_enabled
# ---------------------------------------------------------------------------


def _make_fake_engine(rowcount: int = 1, raise_exc: Exception | None = None):
    class FakeResult:
        def __init__(self, rc):
            self.rowcount = rc

    captured = {"calls": []}

    class FakeConn:
        def execute(self, query, params):
            captured["calls"].append({"sql": str(query), "params": params})
            if raise_exc is not None:
                raise raise_exc
            return FakeResult(rowcount)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    return FakeEngine(), captured


def test_enable_openemr_client_updates_row_and_writes_audit(app, monkeypatch):
    engine, captured = _make_fake_engine(rowcount=1)
    audits = []
    monkeypatch.setattr(registration, "get_openemr_db_engine", lambda: engine)
    monkeypatch.setattr(
        registration,
        "write_audit_log",
        lambda **kwargs: audits.append(kwargs),
    )

    with app.app_context():
        registration._enable_openemr_client("acct-1", "openemr-client-1")

    assert len(captured["calls"]) == 1
    assert "UPDATE oauth_clients" in captured["calls"][0]["sql"]
    assert "is_enabled = 1" in captured["calls"][0]["sql"]
    assert captured["calls"][0]["params"] == {"client_id": "openemr-client-1"}

    assert len(audits) == 1
    assert audits[0]["event_type"] == "openemr.client_enabled"
    assert audits[0]["success"] is True
    assert audits[0]["zoom_account_id"] == "acct-1"
    assert audits[0]["detail"] == {"openemr_client_id": "openemr-client-1"}


def test_enable_openemr_client_raises_and_audits_when_no_row_matches(app, monkeypatch):
    engine, _ = _make_fake_engine(rowcount=0)
    audits = []
    monkeypatch.setattr(registration, "get_openemr_db_engine", lambda: engine)
    monkeypatch.setattr(
        registration,
        "write_audit_log",
        lambda **kwargs: audits.append(kwargs),
    )

    with app.app_context():
        with pytest.raises(RuntimeError, match="matched 0 rows"):
            registration._enable_openemr_client("acct-1", "missing-client-id")

    assert len(audits) == 1
    assert audits[0]["event_type"] == "openemr.client_enable_failed"
    assert audits[0]["success"] is False
    assert audits[0]["zoom_account_id"] == "acct-1"
    assert "matched 0 rows" in audits[0]["error_message"]


def test_enable_openemr_client_raises_and_audits_on_db_exception(app, monkeypatch):
    engine, _ = _make_fake_engine(raise_exc=RuntimeError("db down"))
    audits = []
    monkeypatch.setattr(registration, "get_openemr_db_engine", lambda: engine)
    monkeypatch.setattr(
        registration,
        "write_audit_log",
        lambda **kwargs: audits.append(kwargs),
    )

    with app.app_context():
        with pytest.raises(RuntimeError, match="db down"):
            registration._enable_openemr_client("acct-1", "openemr-client-1")

    assert len(audits) == 1
    assert audits[0]["event_type"] == "openemr.client_enable_failed"
    assert audits[0]["success"] is False
    assert audits[0]["error_message"] == "db down"


def test_register_zoom_account_rolls_back_when_enable_client_fails(app, monkeypatch):
    """When auto-enable fails, registration deregisters from OpenEMR and cleans
    up keypair — no Flask DB row should remain, and the caller sees the error."""
    deregister_calls = []
    keypair_cleanup = {}

    monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
    monkeypatch.setattr(
        registration,
        "_register_with_openemr",
        lambda account_id, contact_email: {
            "client_id": "openemr-client-fail",
            "client_secret": "openemr-client-secret",
            "registration_access_token": "registration-token",
            "registration_client_uri": "https://openemr.public/oauth2/default/client/abc",
        },
    )
    monkeypatch.setattr(
        registration,
        "_enable_openemr_client",
        lambda zoom_account_id, openemr_client_id: (_ for _ in ()).throw(RuntimeError("enable failed")),
    )
    monkeypatch.setattr(
        registration,
        "_deregister_from_openemr",
        lambda uri, token: deregister_calls.append((uri, token)),
    )
    monkeypatch.setattr(
        registration,
        "delete_keypair",
        lambda account_id: keypair_cleanup.__setitem__("account_id", account_id),
    )

    with app.app_context():
        with pytest.raises(RuntimeError, match="enable failed"):
            registration.register_zoom_account(
                None,
                "acct-enable-fail",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                None,
                None,
                "admin@example.com",
            )

        record = ZoomAccount.query.filter_by(account_id="acct-enable-fail").first()

    assert deregister_calls == [("https://openemr.public/oauth2/default/client/abc", "registration-token")]
    assert keypair_cleanup["account_id"] == "acct-enable-fail"
    assert record is None
