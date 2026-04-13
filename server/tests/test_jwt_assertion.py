import uuid

import jwt

from app.auth import jwt_assertion
from app.auth.jwks import load_private_key


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


def test_get_openemr_token_returns_cached_token(app, monkeypatch):
    with app.app_context():
        jwt_assertion._token_cache["access_token"] = "cached-token"
        jwt_assertion._token_cache["expires_at"] = 1000

        monkeypatch.setattr(jwt_assertion.time, "time", lambda: 950)
        monkeypatch.setattr(
            jwt_assertion,
            "exchange_assertion_for_token",
            lambda *_: (_ for _ in ()).throw(AssertionError("network call not expected")),
        )

        token = jwt_assertion.get_openemr_token()

    assert token == "cached-token"


def test_get_openemr_token_refreshes_and_caches(app, monkeypatch):
    captured = {}

    def fake_exchange(client_id, token_endpoint, audience, scopes, key_path, key_id):
        captured["client_id"] = client_id
        captured["token_endpoint"] = token_endpoint
        captured["audience"] = audience
        captured["scopes"] = scopes
        captured["key_path"] = key_path
        captured["key_id"] = key_id
        return "fresh-token", 120

    monkeypatch.setattr(jwt_assertion.time, "time", lambda: 1000)
    monkeypatch.setattr(jwt_assertion, "exchange_assertion_for_token", fake_exchange)

    with app.app_context():
        token = jwt_assertion.get_openemr_token(force_refresh=True)

    assert token == "fresh-token"
    assert jwt_assertion._token_cache["access_token"] == "fresh-token"
    assert jwt_assertion._token_cache["expires_at"] == 1120
    assert captured["client_id"] == app.config["OPENEMR_CLIENT_ID"]
    assert captured["token_endpoint"] == "http://openemr.internal/oauth2/default/token"
    assert captured["audience"] == "https://openemr.public/oauth2/default/token"
    assert captured["scopes"] == [
        "system/Patient.read",
        "system/Appointment.read",
        "system/Appointment.write",
        "system/Encounter.read",
        "system/Encounter.write",
    ]
    assert captured["key_path"] == app.config["JWKS_PRIVATE_PATH"]
    assert captured["key_id"] == app.config["KEY_ID"]
