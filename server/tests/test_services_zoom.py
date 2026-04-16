from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import requests

from app.services import zoom


def test_build_basic_auth_header():
    header = zoom._build_basic_auth_header("client", "secret")
    assert header == "Basic Y2xpZW50OnNlY3JldA=="


def test_fetch_zoom_token_posts_expected_request(monkeypatch):
    captured = {}

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

    monkeypatch.setattr(zoom.requests, "post", fake_post)
    monkeypatch.setattr(zoom, "ZOOM_TOKEN_URL", "https://zoom.example/token")

    token, expires_in, scope = zoom.fetch_zoom_token("acct-1", "cid", "csecret")

    assert token == "zoom-token"
    assert expires_in == 1200
    assert scope == "meeting:read"
    assert captured["url"] == "https://zoom.example/token"
    assert captured["params"] == {"grant_type": "account_credentials", "account_id": "acct-1"}
    assert captured["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert captured["headers"]["Authorization"].startswith("Basic ")
    assert captured["timeout"] == 10


def test_fetch_zoom_token_defaults(monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "zoom-token"}

    monkeypatch.setattr(zoom.requests, "post", lambda *args, **kwargs: DummyResponse())
    token, expires_in, scope = zoom.fetch_zoom_token("acct-1", "cid", "csecret")
    assert token == "zoom-token"
    assert expires_in == 3600
    assert scope == ""


def test_validate_zoom_credentials_true(monkeypatch):
    monkeypatch.setattr(zoom, "fetch_zoom_token", lambda *args: ("tok", 3600, "scope"))
    assert zoom.validate_zoom_credentials("acct-1", "cid", "sec") is True


def test_validate_zoom_credentials_false_on_http_error(monkeypatch):
    def _raise(*args):
        raise requests.HTTPError("bad credentials")

    monkeypatch.setattr(zoom, "fetch_zoom_token", _raise)
    assert zoom.validate_zoom_credentials("acct-1", "cid", "sec") is False


def test_validate_zoom_credentials_raises_on_network_error(monkeypatch):
    def _raise(*args):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(zoom, "fetch_zoom_token", _raise)

    with pytest.raises(requests.ConnectionError):
        zoom.validate_zoom_credentials("acct-1", "cid", "sec")


def test_get_zoom_token_uses_cache_if_more_than_5_minutes_left(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = SimpleNamespace(
        account_id="acct-1",
        client_id="cid",
        client_secret="sec",
        zoom_access_token="cached-token",
        zoom_token_expires_at=now + timedelta(seconds=301),
    )

    monkeypatch.setattr(zoom, "fetch_zoom_token", lambda *args: (_ for _ in ()).throw(AssertionError("no refresh expected")))
    monkeypatch.setattr(zoom, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        token = zoom.get_zoom_token(account)

    assert token == "cached-token"


def test_get_zoom_token_refreshes_when_threshold_reached(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = SimpleNamespace(
        account_id="acct-2",
        client_id="cid",
        client_secret="sec",
        zoom_access_token="cached-token",
        zoom_token_expires_at=now + timedelta(seconds=300),
    )
    committed = {"called": False}

    monkeypatch.setattr(zoom, "fetch_zoom_token", lambda *args: ("fresh-token", 900, "meeting:read"))
    monkeypatch.setattr(zoom.time, "time", lambda: 1000)
    monkeypatch.setattr(zoom, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        monkeypatch.setattr(zoom.db.session, "commit", lambda: committed.__setitem__("called", True))
        token = zoom.get_zoom_token(account)

    assert token == "fresh-token"
    assert account.zoom_access_token == "fresh-token"
    assert int(account.zoom_token_expires_at.timestamp()) == 1900
    assert committed["called"] is True


def test_get_zoom_token_handles_naive_expiry(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = SimpleNamespace(
        account_id="acct-3",
        client_id="cid",
        client_secret="sec",
        zoom_access_token="cached-token",
        zoom_token_expires_at=datetime(2026, 1, 1, 0, 10, 0),  # naive datetime
    )

    monkeypatch.setattr(zoom, "fetch_zoom_token", lambda *args: (_ for _ in ()).throw(AssertionError("no refresh expected")))
    monkeypatch.setattr(zoom, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        token = zoom.get_zoom_token(account)

    assert token == "cached-token"


def test_get_zoom_token_force_refresh(app, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    account = SimpleNamespace(
        account_id="acct-4",
        client_id="cid",
        client_secret="sec",
        zoom_access_token="cached-token",
        zoom_token_expires_at=now + timedelta(hours=1),
    )
    monkeypatch.setattr(zoom, "fetch_zoom_token", lambda *args: ("forced-token", 60, "scope"))
    monkeypatch.setattr(zoom.time, "time", lambda: 5000)
    monkeypatch.setattr(zoom, "datetime", SimpleNamespace(now=lambda tz=None: now, fromtimestamp=datetime.fromtimestamp))

    with app.app_context():
        monkeypatch.setattr(zoom.db.session, "commit", lambda: None)
        token = zoom.get_zoom_token(account, force_refresh=True)

    assert token == "forced-token"


def test_make_zoom_api_request_adds_authorization(monkeypatch):
    captured = {}

    class DummyResponse:
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

    monkeypatch.setattr(zoom, "get_zoom_token", lambda account: "zoom-token")
    monkeypatch.setattr(zoom.requests, "request", fake_request)
    monkeypatch.setattr(zoom, "ZOOM_API_BASE_URL", "https://api.zoom.test/v2")

    account = SimpleNamespace(account_id="acct")
    response = zoom.make_zoom_api_request("get", "/users/me", account, params={"page_size": 30})

    assert response == {"ok": True}
    assert captured["method"] == "GET"
    assert captured["url"] == "https://api.zoom.test/v2/users/me"
    assert captured["headers"]["Authorization"] == "Bearer zoom-token"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["timeout"] == 10
    assert captured["kwargs"]["params"] == {"page_size": 30}
