from types import SimpleNamespace

import requests

from app.services.registration import reg_verification


def test_verify_openemr_token_for_account_returns_true_on_success(monkeypatch):
    account = SimpleNamespace(account_id="acct-1")
    captured = {}

    def fake_get_openemr_token(zoom_account, *args, **kwargs):
        captured["account"] = zoom_account
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "token"

    monkeypatch.setattr(reg_verification, "get_openemr_token", fake_get_openemr_token)

    assert reg_verification.verify_openemr_token_for_account(account) is True
    assert captured["account"] is account
    # Verify must use the regular cached path now that clients are auto-enabled
    # at registration time — no force_refresh kwarg should be passed.
    assert captured["args"] == ()
    assert captured["kwargs"] == {}


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


def test_verify_writes_success_audit(monkeypatch):
    account = SimpleNamespace(account_id="acct-audit-ok")
    calls: list[dict] = []
    monkeypatch.setattr(reg_verification, "get_openemr_token", lambda *_, **__: "token")
    monkeypatch.setattr(reg_verification, "write_audit_log", lambda **kwargs: calls.append(kwargs))

    assert reg_verification.verify_openemr_token_for_account(account) is True
    audit = next(c for c in calls if c["event_type"] == "openemr.token_verify_success")
    assert audit["success"] is True
    assert audit["zoom_account_id"] == "acct-audit-ok"


def test_verify_writes_failed_audit_on_http_error(monkeypatch):
    account = SimpleNamespace(account_id="acct-audit-http")
    calls: list[dict] = []

    def _raise(*_, **__):
        err = requests.HTTPError("unauthorized")
        err.response = SimpleNamespace(status_code=401)
        raise err

    monkeypatch.setattr(reg_verification, "get_openemr_token", _raise)
    monkeypatch.setattr(reg_verification, "write_audit_log", lambda **kwargs: calls.append(kwargs))

    assert reg_verification.verify_openemr_token_for_account(account) is False
    audit = next(c for c in calls if c["event_type"] == "openemr.token_verify_failed")
    assert audit["success"] is False
    assert audit["zoom_account_id"] == "acct-audit-http"
    assert audit["detail"] == {"status_code": 401}


def test_verify_writes_failed_audit_on_unexpected_exception(monkeypatch):
    account = SimpleNamespace(account_id="acct-audit-runtime")
    calls: list[dict] = []

    def _raise(*_, **__):
        raise RuntimeError("boom")

    monkeypatch.setattr(reg_verification, "get_openemr_token", _raise)
    monkeypatch.setattr(reg_verification, "write_audit_log", lambda **kwargs: calls.append(kwargs))

    assert reg_verification.verify_openemr_token_for_account(account) is False
    audit = next(c for c in calls if c["event_type"] == "openemr.token_verify_failed")
    assert audit["detail"] == {"stage": "unexpected"}
