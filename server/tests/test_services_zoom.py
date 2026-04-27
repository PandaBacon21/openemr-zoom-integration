from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import requests

from app.services.zoom import zoom, zoom_auth


def _make_account(**overrides):
    return SimpleNamespace(
        account_id=overrides.get("account_id", "acct-1"),
        client_id=overrides.get("client_id", "cid"),
        client_secret=overrides.get("client_secret", "sec"),
        zoom_access_token=overrides.get("zoom_access_token"),
        zoom_token_expires_at=overrides.get("zoom_token_expires_at"),
    )


def test_build_basic_auth_header():
    header = zoom_auth._build_basic_auth_header("client", "secret")
    assert header == "Basic Y2xpZW50OnNlY3JldA=="


def test_fetch_zoom_token_posts_expected_request_and_persists(monkeypatch):
    captured = {}
    committed = {"called": False}
    account = _make_account(account_id="acct-1", client_id="client-id", client_secret="client-secret")

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "zoom-token", "expires_in": 1200, "scope": "meeting:read"}

    def fake_post(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr(zoom_auth.requests, "post", fake_post)
    monkeypatch.setattr(zoom_auth, "ZOOM_TOKEN_URL", "https://zoom.example/token")
    monkeypatch.setattr(zoom_auth.time, "time", lambda: 1000)
    monkeypatch.setattr(zoom_auth.db.session, "commit", lambda: committed.__setitem__("called", True))

    token, expires_in, scope = zoom_auth._fetch_zoom_token(account)

    assert token == "zoom-token"
    assert expires_in == 1200
    assert scope == "meeting:read"
    assert captured["url"] == "https://zoom.example/token"
    assert captured["params"] == {"grant_type": "account_credentials", "account_id": "acct-1"}
    assert captured["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert captured["headers"]["Authorization"].startswith("Basic ")
    assert captured["timeout"] == 10
    assert account.zoom_access_token == "zoom-token"
    assert int(account.zoom_token_expires_at.timestamp()) == 2200
    assert committed["called"] is True


def test_fetch_zoom_token_defaults(monkeypatch):
    account = _make_account()

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "zoom-token"}

    monkeypatch.setattr(zoom_auth.requests, "post", lambda *args, **kwargs: DummyResponse())
    monkeypatch.setattr(zoom_auth.time, "time", lambda: 2000)
    monkeypatch.setattr(zoom_auth.db.session, "commit", lambda: None)

    token, expires_in, scope = zoom_auth._fetch_zoom_token(account)

    assert token == "zoom-token"
    assert expires_in == 3600
    assert scope == ""
    assert int(account.zoom_token_expires_at.timestamp()) == 5600


def test_validate_zoom_credentials_true(monkeypatch):
    monkeypatch.setattr(zoom_auth, "_fetch_zoom_token", lambda account: ("tok", 3600, "scope"))
    assert zoom_auth.validate_zoom_credentials(_make_account()) is True


def test_validate_zoom_credentials_false_on_http_error(monkeypatch):
    def _raise(*args):
        raise requests.HTTPError("bad credentials")

    monkeypatch.setattr(zoom_auth, "_fetch_zoom_token", _raise)
    assert zoom_auth.validate_zoom_credentials(_make_account()) is False


def test_validate_zoom_credentials_raises_on_network_error(monkeypatch):
    def _raise(*args):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(zoom_auth, "_fetch_zoom_token", _raise)

    with pytest.raises(requests.ConnectionError):
        zoom_auth.validate_zoom_credentials(_make_account())


def test_get_zoom_token_uses_cache_if_more_than_5_minutes_left(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = _make_account(
        zoom_access_token="cached-token",
        zoom_token_expires_at=now + timedelta(seconds=301),
    )

    monkeypatch.setattr(zoom_auth, "_fetch_zoom_token", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no refresh expected")))
    monkeypatch.setattr(zoom_auth, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        token = zoom_auth.get_zoom_token(account)

    assert token == "cached-token"


def test_get_zoom_token_refreshes_when_threshold_reached(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = _make_account(
        account_id="acct-2",
        zoom_access_token="cached-token",
        zoom_token_expires_at=now + timedelta(seconds=300),
    )
    captured = {}

    def fake_fetch(acct, refresh=False):
        captured["refresh"] = refresh
        return "fresh-token", 900, "meeting:read"

    monkeypatch.setattr(zoom_auth, "_fetch_zoom_token", fake_fetch)
    monkeypatch.setattr(zoom_auth, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        token = zoom_auth.get_zoom_token(account)

    assert token == "fresh-token"
    assert captured["refresh"] is False


def test_get_zoom_token_handles_naive_expiry(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = _make_account(
        zoom_access_token="cached-token",
        zoom_token_expires_at=datetime(2026, 1, 1, 0, 10, 0),  # naive datetime
    )

    monkeypatch.setattr(zoom_auth, "_fetch_zoom_token", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no refresh expected")))
    monkeypatch.setattr(zoom_auth, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        token = zoom_auth.get_zoom_token(account)

    assert token == "cached-token"


def test_get_zoom_token_force_refresh_propagates_refresh_flag(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = _make_account(
        account_id="acct-4",
        zoom_access_token="cached-token",
        zoom_token_expires_at=now + timedelta(hours=1),
    )
    captured = {}

    def fake_fetch(acct, refresh=False):
        captured["refresh"] = refresh
        return "forced-token", 60, "scope"

    monkeypatch.setattr(zoom_auth, "_fetch_zoom_token", fake_fetch)
    monkeypatch.setattr(zoom_auth, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        token = zoom_auth.get_zoom_token(account, force_refresh=True)

    assert token == "forced-token"
    assert captured["refresh"] is True


def test_make_zoom_api_request_adds_authorization(monkeypatch):
    captured = {}

    class DummyResponse:
        status_code = 200
        content = b'{"ok": true}'

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    def fake_request(method, url, headers, timeout, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["kwargs"] = kwargs
        return DummyResponse()

    monkeypatch.setattr(zoom_auth, "get_zoom_token", lambda account: "zoom-token")
    monkeypatch.setattr(zoom_auth.requests, "request", fake_request)
    monkeypatch.setattr(zoom_auth, "ZOOM_API_BASE_URL", "https://api.zoom.test/v2")

    account = _make_account(account_id="acct")
    response = zoom_auth.make_zoom_api_request("get", "/users/me", account, params={"page_size": 30})

    assert response == {"ok": True}
    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.zoom.test/v2/users/me"
    assert captured["headers"]["Authorization"] == "Bearer zoom-token"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["timeout"] == 10
    assert captured["kwargs"]["params"] == {"page_size": 30}


def test_make_zoom_api_request_returns_empty_dict_for_204(monkeypatch):
    class DummyResponse:
        status_code = 204
        content = b""

        def raise_for_status(self):
            return None

        def json(self):
            raise AssertionError("json() should not be called for 204 response")

    monkeypatch.setattr(zoom_auth, "get_zoom_token", lambda account: "zoom-token")
    monkeypatch.setattr(zoom_auth.requests, "request", lambda *args, **kwargs: DummyResponse())
    monkeypatch.setattr(zoom_auth, "ZOOM_API_BASE_URL", "https://api.zoom.test/v2")

    account = _make_account(account_id="acct")
    response = zoom_auth.make_zoom_api_request("delete", "/meetings/123", account)

    assert response == {}


def test_get_zoom_meeting_returns_payload(monkeypatch):
    monkeypatch.setattr(
        zoom,
        "make_zoom_api_request",
        lambda method, endpoint, zoom_account: {"id": "123", "topic": "Telehealth"},
    )

    result = zoom.get_zoom_meeting(_make_account(), "123")

    assert result == {"id": "123", "topic": "Telehealth"}


def test_get_zoom_meeting_returns_none_on_404(monkeypatch):
    response = requests.Response()
    response.status_code = 404
    error = requests.HTTPError("not found")
    error.response = response

    monkeypatch.setattr(
        zoom,
        "make_zoom_api_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(error),
    )

    assert zoom.get_zoom_meeting(_make_account(), "123") is None


def test_delete_zoom_meeting_returns_true_on_success(monkeypatch):
    captured = {}

    def fake_make_request(method, endpoint, zoom_account):
        captured["method"] = method
        captured["endpoint"] = endpoint
        return {}

    monkeypatch.setattr(zoom, "make_zoom_api_request", fake_make_request)

    assert zoom.delete_zoom_meeting(_make_account(), "123") is True
    assert captured["method"] == "DELETE"
    assert captured["endpoint"] == "/meetings/123"


def test_delete_zoom_meeting_returns_false_on_404(monkeypatch):
    response = requests.Response()
    response.status_code = 404
    error = requests.HTTPError("not found")
    error.response = response

    monkeypatch.setattr(
        zoom,
        "make_zoom_api_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(error),
    )

    assert zoom.delete_zoom_meeting(_make_account(), "123") is False


def test_update_zoom_meeting_builds_expected_payload(monkeypatch):
    captured = {}
    account = _make_account(account_id="acct-1")
    account.timezone = "America/Denver"

    match = SimpleNamespace(
        provider_mapping=SimpleNamespace(openemr_provider_name="Dr Jane Doe"),
        payload={
            "eid": 999,
            "pid": 1,
            "title": "Follow-up",
            "comments": "Bring records",
            "appointment_date": "20260420",
            "appointment_time": "10:00",
            "duration_minutes": 45,
        },
    )

    monkeypatch.setattr(zoom, "get_patient", lambda acct, pid: {"last_name": "Smith"})

    def fake_make_zoom_api_request(method, endpoint, zoom_account, **kwargs):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["zoom_account"] = zoom_account
        captured["json"] = kwargs["json"]
        return {}

    monkeypatch.setattr(zoom, "make_zoom_api_request", fake_make_zoom_api_request)

    zoom.update_zoom_meeting(account, "123", match)

    assert captured["method"] == "PATCH"
    assert captured["endpoint"] == "/meetings/123"
    assert captured["zoom_account"] == account
    assert captured["json"]["topic"] == "Telehealth | Dr Jane Doe | Smith | Follow-up"
    assert captured["json"]["agenda"] == "Bring records"
    assert captured["json"]["duration"] == 45
    assert captured["json"]["timezone"] == "America/Denver"
    assert captured["json"]["start_time"] == "2026-04-20T10:00:00"


def test_update_zoom_meeting_raises_on_unparseable_datetime():
    account = _make_account(account_id="acct-1")
    account.timezone = "America/Denver"
    match = SimpleNamespace(
        provider_mapping=SimpleNamespace(openemr_provider_name="Dr Jane Doe"),
        payload={
            "appointment_date": "bad-date",
            "appointment_time": "bad-time",
        },
    )

    with pytest.raises(ValueError, match="Could not parse appointment datetime for update"):
        zoom.update_zoom_meeting(account, "123", match)
