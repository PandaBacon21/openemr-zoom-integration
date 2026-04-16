import requests
import pytest

from app.extensions import db
from app.models import ZoomAccount
from app.services import registration


def _create_account(account_id: str, *, is_active: bool = True, **overrides) -> ZoomAccount:
    account = ZoomAccount(
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
    assert captured["json"]["jwks_uri"] == "http://localhost:5000/.well-known/jwks.json"
    assert captured["json"]["redirect_uris"] == ["http://localhost:5000/callback"]
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["timeout"] == 15


def test_deregister_from_openemr_swallows_errors(monkeypatch):
    def fake_delete(*args, **kwargs):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(registration.requests, "delete", fake_delete)

    registration._deregister_from_openemr("http://openemr.internal/client/1", "token")


def test_register_zoom_account_rejects_invalid_zoom_credentials(app, monkeypatch):
    monkeypatch.setattr(registration, "validate_zoom_credentials", lambda *args: False)

    with app.app_context():
        with pytest.raises(ValueError, match="Zoom credential validation failed"):
            registration.register_zoom_account(
                "acct-invalid",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                "admin@example.com",
            )


def test_register_zoom_account_rejects_duplicate_active(app, monkeypatch):
    with app.app_context():
        _create_account("acct-dup", is_active=True)
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda *args: True)

        with pytest.raises(ValueError, match="already registered and active"):
            registration.register_zoom_account(
                "acct-dup",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                "admin@example.com",
            )


def test_register_zoom_account_replaces_inactive_record(app, monkeypatch):
    with app.app_context():
        _create_account("acct-inactive", is_active=False)
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda *args: True)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
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

        account = registration.register_zoom_account(
            "acct-inactive",
            "zoom-client-id",
            "zoom-client-secret",
            "webhook-secret",
            "admin@example.com",
        )
        records = ZoomAccount.query.filter_by(account_id="acct-inactive").all()

    assert len(records) == 1
    assert records[0].id == account.id
    assert account.is_active is True


def test_register_zoom_account_cleans_up_keys_when_openemr_registration_fails(app, monkeypatch):
    cleanup_called = {}

    with app.app_context():
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda *args: True)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
        monkeypatch.setattr(registration, "_register_with_openemr", lambda *args: (_ for _ in ()).throw(requests.HTTPError("bad request")))
        monkeypatch.setattr(registration, "delete_keypair", lambda account_id: cleanup_called.__setitem__("account_id", account_id))

        with pytest.raises(requests.HTTPError):
            registration.register_zoom_account(
                "acct-openemr-fail",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                "admin@example.com",
            )

        record = ZoomAccount.query.filter_by(account_id="acct-openemr-fail").first()

    assert cleanup_called["account_id"] == "acct-openemr-fail"
    assert record is None


def test_register_zoom_account_rolls_back_and_cleans_keys_on_db_failure(app, monkeypatch):
    cleanup_called = {}
    rollback_called = {"called": False}

    with app.app_context():
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda *args: True)
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
        monkeypatch.setattr(registration, "delete_keypair", lambda account_id: cleanup_called.__setitem__("account_id", account_id))
        monkeypatch.setattr(registration.db.session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("db write failed")))
        monkeypatch.setattr(registration.db.session, "rollback", lambda: rollback_called.__setitem__("called", True))

        with pytest.raises(RuntimeError, match="db write failed"):
            registration.register_zoom_account(
                "acct-db-fail",
                "zoom-client-id",
                "zoom-client-secret",
                "webhook-secret",
                "admin@example.com",
            )

    assert cleanup_called["account_id"] == "acct-db-fail"
    assert rollback_called["called"] is True


def test_register_zoom_account_success_persists_and_normalizes_client_uri(app, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(registration, "validate_zoom_credentials", lambda *args: True)
        monkeypatch.setattr(registration, "generate_keypair", lambda account_id: (f"/tmp/{account_id}/private.pem", f"zoomly-{account_id}"))
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

        account = registration.register_zoom_account(
            "acct-success",
            "zoom-client-id",
            "zoom-client-secret",
            "webhook-secret",
            "admin@example.com",
        )

        stored = ZoomAccount.query.filter_by(account_id="acct-success").first()

    assert account.account_id == "acct-success"
    assert account.openemr_client_id == "openemr-client-id"
    assert account.kid == "zoomly-acct-success"
    assert account.openemr_registration_client_uri == "http://openemr.internal/oauth2/default/client/abc"
    assert stored is not None


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
