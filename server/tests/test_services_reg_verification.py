from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import requests

from app.extensions import db
from app.models import ZoomAccount
from app.services.registration import reg_verification


def _create_account(account_id: str, *, is_active: bool = True, **overrides) -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id=overrides.get("client_id", "zoom-client-id"),
        client_secret=overrides.get("client_secret", "zoom-client-secret"),
        webhook_secret=overrides.get("webhook_secret", "zoom-webhook-secret"),
        openemr_client_id=overrides.get("openemr_client_id", "openemr-client-id"),
        private_key_path=overrides.get("private_key_path", "/tmp/private.pem"),
        kid=overrides.get("kid", f"zoomly-{account_id}"),
        openemr_access_token=overrides.get("openemr_access_token"),
        openemr_token_expires_at=overrides.get("openemr_token_expires_at"),
        is_active=is_active,
    )
    db.session.add(account)
    db.session.commit()
    return account


def test_verify_openemr_token_for_account_returns_true_on_success(monkeypatch):
    account = SimpleNamespace(account_id="acct-1")
    captured = {}

    def fake_get_openemr_token(zoom_account, force_refresh=False):
        captured["account"] = zoom_account
        captured["force_refresh"] = force_refresh
        return "token"

    monkeypatch.setattr(reg_verification, "get_openemr_token", fake_get_openemr_token)

    assert reg_verification.verify_openemr_token_for_account(account) is True
    assert captured["account"] is account
    assert captured["force_refresh"] is True


def test_verify_openemr_token_for_account_returns_false_on_401(monkeypatch):
    account = SimpleNamespace(account_id="acct-1")

    def _raise(*args, **kwargs):
        err = requests.HTTPError("unauthorized")
        err.response = SimpleNamespace(status_code=401)
        raise err

    monkeypatch.setattr(reg_verification, "get_openemr_token", _raise)

    assert reg_verification.verify_openemr_token_for_account(account) is False


def test_verify_openemr_token_for_account_returns_false_on_unexpected_http_error(monkeypatch):
    account = SimpleNamespace(account_id="acct-1")

    def _raise(*args, **kwargs):
        err = requests.HTTPError("server error")
        err.response = SimpleNamespace(status_code=500)
        raise err

    monkeypatch.setattr(reg_verification, "get_openemr_token", _raise)

    assert reg_verification.verify_openemr_token_for_account(account) is False


def test_verify_openemr_token_for_account_returns_false_on_non_http_exception(monkeypatch):
    account = SimpleNamespace(account_id="acct-1")

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(reg_verification, "get_openemr_token", _raise)

    assert reg_verification.verify_openemr_token_for_account(account) is False


def test_check_pending_registrations_no_pending_does_not_schedule(app, monkeypatch):
    captured = {"add_job_called": False}

    monkeypatch.setattr(
        "app.extensions.scheduler.add_job",
        lambda *args, **kwargs: captured.__setitem__("add_job_called", True),
    )
    monkeypatch.setattr(
        reg_verification,
        "verify_openemr_token_for_account",
        lambda account: (_ for _ in ()).throw(AssertionError("should not verify when no pending")),
    )

    reg_verification.check_pending_registrations(app)

    assert captured["add_job_called"] is False


def test_check_pending_registrations_reschedules_when_accounts_still_pending(app, monkeypatch):
    with app.app_context():
        _create_account("acct-pending", openemr_access_token=None, openemr_token_expires_at=None)

    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    captured = {}

    monkeypatch.setattr(
        reg_verification,
        "datetime",
        SimpleNamespace(now=lambda tz=None: fixed_now),
    )
    monkeypatch.setattr(reg_verification, "verify_openemr_token_for_account", lambda account: False)

    def fake_add_job(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.extensions.scheduler.add_job", fake_add_job)

    reg_verification.check_pending_registrations(app)

    assert captured["func"] == reg_verification.check_pending_registrations
    assert captured["args"] == [app]
    assert captured["trigger"] == "date"
    assert captured["id"] == "check_pending_registrations"
    assert captured["replace_existing"] is True
    assert captured["run_date"] == fixed_now + timedelta(minutes=5)


def test_check_pending_registrations_does_not_reschedule_when_all_verified(app, monkeypatch):
    with app.app_context():
        _create_account("acct-pending", openemr_access_token=None, openemr_token_expires_at=None)

    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    captured = {"add_job_called": False}

    monkeypatch.setattr(
        reg_verification,
        "datetime",
        SimpleNamespace(now=lambda tz=None: fixed_now),
    )

    def fake_verify(account):
        account.openemr_access_token = "verified-token"
        account.openemr_token_expires_at = fixed_now + timedelta(minutes=10)
        db.session.commit()
        return True

    monkeypatch.setattr(reg_verification, "verify_openemr_token_for_account", fake_verify)
    monkeypatch.setattr(
        "app.extensions.scheduler.add_job",
        lambda *args, **kwargs: captured.__setitem__("add_job_called", True),
    )

    reg_verification.check_pending_registrations(app)

    assert captured["add_job_called"] is False


def test_trigger_verification_scheduler_schedules_immediate_check(app, monkeypatch):
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    captured = {}

    monkeypatch.setattr(
        reg_verification,
        "datetime",
        SimpleNamespace(now=lambda tz=None: fixed_now),
    )

    def fake_add_job(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.extensions.scheduler.add_job", fake_add_job)

    reg_verification.trigger_verification_scheduler(app)

    assert captured["func"] == reg_verification.check_pending_registrations
    assert captured["args"] == [app]
    assert captured["trigger"] == "date"
    assert captured["run_date"] == fixed_now
    assert captured["id"] == "check_pending_registrations"
    assert captured["replace_existing"] is True
