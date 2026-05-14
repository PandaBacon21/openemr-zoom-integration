from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import jwt
import pytest
import requests

from app.auth import jwt_assertion
from app.auth.jwks import load_private_key


def _make_account(**overrides):
    return SimpleNamespace(
        account_id=overrides.get("account_id", "acct-1"),
        openemr_access_token=overrides.get("openemr_access_token"),
        openemr_token_expires_at=overrides.get("openemr_token_expires_at"),
        openemr_client_id=overrides.get("openemr_client_id", "openemr-client-id"),
        private_key_path=overrides.get("private_key_path", "/tmp/key.pem"),
        kid=overrides.get("kid", "zoomly-acct-1"),
    )


def test_build_client_assertion_claims_and_header(tmp_path):
    key_path = tmp_path / "keys" / "private.pem"
    token = jwt_assertion.build_client_assertion(
        client_id="client-123",
        audience="https://openemr.example/token",
        key_path=str(key_path),
        key_id="kid-1",
    )

    header = jwt.get_unverified_header(token)
    public_key = load_private_key(str(key_path)).public_key()
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS384"],
        audience="https://openemr.example/token",
    )

    uuid.UUID(payload["jti"])
    assert header["alg"] == "RS384"
    assert header["kid"] == "kid-1"
    assert payload["iss"] == "client-123"
    assert payload["sub"] == "client-123"
    assert payload["aud"] == "https://openemr.example/token"
    assert payload["exp"] - payload["iat"] == 300


def test_exchange_assertion_for_token_posts_expected_request(monkeypatch):
    captured = {}

    class DummyResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "token-abc", "expires_in": 600}

    def fake_build_assertion(client_id, audience, key_path, key_id):
        assert client_id == "client-123"
        assert audience == "https://public.example/token"
        assert key_path == "/tmp/key.pem"
        assert key_id == "kid-1"
        return "signed-assertion"

    def fake_post(url, data, headers, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr(jwt_assertion, "build_client_assertion", fake_build_assertion)
    monkeypatch.setattr(jwt_assertion.requests, "post", fake_post)

    token, expires_in = jwt_assertion.exchange_assertion_for_token(
        client_id="client-123",
        token_endpoint="https://internal.example/token",
        audience="https://public.example/token",
        scopes=["system/Patient.read", "system/Appointment.write"],
        key_path="/tmp/key.pem",
        key_id="kid-1",
    )

    assert token == "token-abc"
    assert expires_in == 600
    assert captured["url"] == "https://internal.example/token"
    assert captured["data"]["grant_type"] == "client_credentials"
    assert captured["data"]["client_assertion"] == "signed-assertion"
    assert captured["data"]["scope"] == "system/Patient.read system/Appointment.write"
    assert captured["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert captured["timeout"] == 10


def test_exchange_assertion_for_token_default_expiry(monkeypatch):
    class DummyResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "token-abc"}

    monkeypatch.setattr(jwt_assertion, "build_client_assertion", lambda *_: "signed-assertion")
    monkeypatch.setattr(jwt_assertion.requests, "post", lambda *_, **__: DummyResponse())

    _, expires_in = jwt_assertion.exchange_assertion_for_token(
        client_id="client-123",
        token_endpoint="https://internal.example/token",
        audience="https://public.example/token",
        scopes=["system/Patient.read"],
        key_path="/tmp/key.pem",
        key_id="kid-1",
    )

    assert expires_in == 300


def test_get_openemr_token_returns_cached_token_when_tzaware_valid(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = _make_account(
        openemr_access_token="cached-token",
        openemr_token_expires_at=now + timedelta(seconds=120),
    )

    monkeypatch.setattr(jwt_assertion, "datetime", SimpleNamespace(
        now=lambda tz=None: now,
        fromtimestamp=datetime.fromtimestamp,
    ))
    monkeypatch.setattr(
        jwt_assertion,
        "exchange_assertion_for_token",
        lambda *_: (_ for _ in ()).throw(AssertionError("network call not expected")),
    )

    from app.extensions import db
    monkeypatch.setattr(
        db.session,
        "commit",
        lambda: (_ for _ in ()).throw(AssertionError("db commit not expected")),
    )

    with app.app_context():
        token = jwt_assertion.get_openemr_token(account)

    assert token == "cached-token"


def test_get_openemr_token_force_refresh_bypasses_cache_and_persists(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = _make_account(
        openemr_access_token="cached-token",
        openemr_token_expires_at=now + timedelta(hours=1),
    )
    captured = {}
    committed = {"called": False}

    def fake_exchange(client_id, token_endpoint, audience, scopes, key_path, key_id):
        captured["client_id"] = client_id
        captured["token_endpoint"] = token_endpoint
        captured["audience"] = audience
        captured["scopes"] = scopes
        captured["key_path"] = key_path
        captured["key_id"] = key_id
        return "fresh-token", 120

    monkeypatch.setattr(jwt_assertion, "exchange_assertion_for_token", fake_exchange)
    monkeypatch.setattr(jwt_assertion.time, "time", lambda: 1000)
    monkeypatch.setattr(jwt_assertion, "datetime", SimpleNamespace(
        now=lambda tz=None: now,
        fromtimestamp=datetime.fromtimestamp,
    ))

    from app.extensions import db
    monkeypatch.setattr(db.session, "commit", lambda: committed.__setitem__("called", True))

    with app.app_context():
        token = jwt_assertion.get_openemr_token(account, force_refresh=True)

    assert token == "fresh-token"
    assert account.openemr_access_token == "fresh-token"
    assert int(account.openemr_token_expires_at.timestamp()) == 1120
    assert committed["called"] is True
    assert captured["client_id"] == account.openemr_client_id
    assert captured["token_endpoint"] == "http://openemr.internal/oauth2/default/token"
    assert captured["audience"] == "https://openemr.public/oauth2/default/token"
    assert captured["scopes"] == app.config["OPENEMR_SCOPES"]
    assert captured["key_path"] == account.private_key_path
    assert captured["key_id"] == account.kid


def test_get_openemr_token_handles_naive_expiry_as_utc(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = _make_account(
        openemr_access_token="cached-token",
        openemr_token_expires_at=datetime(2026, 1, 1, 0, 10, 0),  # naive datetime
    )

    monkeypatch.setattr(jwt_assertion, "datetime", SimpleNamespace(
        now=lambda tz=None: now,
        fromtimestamp=datetime.fromtimestamp,
    ))
    monkeypatch.setattr(
        jwt_assertion,
        "exchange_assertion_for_token",
        lambda *_: (_ for _ in ()).throw(AssertionError("network call not expected")),
    )

    with app.app_context():
        token = jwt_assertion.get_openemr_token(account)

    assert token == "cached-token"


def test_get_openemr_token_writes_refresh_failed_on_http_error(app, monkeypatch):
    captured: list[dict] = []
    account = _make_account(account_id="acct-token-http")

    def _raise(*_, **__):
        err = requests.HTTPError("forbidden")
        err.response = SimpleNamespace(
            status_code=403,
            text='{"error":"unauthorized_client"}',
            json=lambda: {"error": "unauthorized_client"},
        )
        raise err

    monkeypatch.setattr(jwt_assertion, "exchange_assertion_for_token", _raise)
    monkeypatch.setattr(jwt_assertion, "write_audit_log", lambda **kwargs: captured.append(kwargs))

    with app.app_context():
        with pytest.raises(requests.HTTPError):
            jwt_assertion.get_openemr_token(account)

    audit = next(c for c in captured if c["event_type"] == "openemr.token_refresh_failed")
    assert audit["zoom_account_id"] == "acct-token-http"
    assert audit["detail"]["status_code"] == 403
    assert audit["detail"]["oauth_error"] == "unauthorized_client"


def test_get_openemr_token_writes_refresh_failed_on_network_error(app, monkeypatch):
    captured: list[dict] = []
    account = _make_account(account_id="acct-token-net")

    def _raise(*_, **__):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(jwt_assertion, "exchange_assertion_for_token", _raise)
    monkeypatch.setattr(jwt_assertion, "write_audit_log", lambda **kwargs: captured.append(kwargs))

    with app.app_context():
        with pytest.raises(requests.ConnectionError):
            jwt_assertion.get_openemr_token(account)

    audit = next(c for c in captured if c["event_type"] == "openemr.token_refresh_failed")
    assert audit["zoom_account_id"] == "acct-token-net"
    assert audit["detail"] == {"stage": "network"}
