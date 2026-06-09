"""Tests for the Epic-style ZCC CTI token endpoint and bearer helper.

Covers /oauth2/token (JWT verification, replay protection, audit) and the
verify_bearer_token_in_store() guard that protects downstream Epic-shaped
endpoints (PatientLookUp / Practitioner / ReceiveCommunication3).
"""

import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

# ENABLE_EPIC_ZCC=true is set in conftest.py (must be there because
# Config.ENABLE_EPIC_ZCC is cached at config.py import time).

from app.extensions import db
from app.models import AccountConfig, AuditLog, ZoomAccount
from app.services.epic import inbound_jwt, token_store
from app.services.epic.constants import EPIC_DEFAULT_SCOPES


TEST_ACCOUNT_ID = "epic-test-acct"
TEST_KID = "zoom-test-kid"
TEST_ISS = "epic-zcc-test-client"
TRUSTED_JKU = "https://zoom.us/cci/jwks.json"
TOKEN_PATH = f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/oauth2/token"
EXPECTED_AUDIENCE = f"http://localhost:5000{TOKEN_PATH}"


def _seed_account(app, *, epic_enabled: bool = True, is_active: bool = True) -> None:
    with app.app_context():
        account = ZoomAccount(
            account_id=TEST_ACCOUNT_ID,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{TEST_ACCOUNT_ID}/private.pem",
            kid=f"zoomly-{TEST_ACCOUNT_ID}",
            is_active=is_active,
        )
        db.session.add(account)
        db.session.add(
            AccountConfig(
                account_id=TEST_ACCOUNT_ID,
                timezone="America/New_York",
                epic_zcc_enabled=epic_enabled,
            )
        )
        db.session.commit()


@pytest.fixture
def rsa_keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def reset_epic_state():
    """Clear in-memory JWKS cache, replay set, and token store between tests."""
    inbound_jwt._jwks_cache.clear()
    inbound_jwt._jti_seen.clear()
    token_store._tokens.clear()
    yield
    inbound_jwt._jwks_cache.clear()
    inbound_jwt._jti_seen.clear()
    token_store._tokens.clear()


@pytest.fixture
def stub_jwks(monkeypatch, rsa_keypair):
    """Stub the JWKS fetch to return our test public key under TEST_KID."""

    class _StubSigningKey:
        def __init__(self, public_key):
            self.key = public_key

    class _StubClient:
        def __init__(self, public_key):
            self._key = public_key

        def get_signing_key(self, kid):
            if kid != TEST_KID:
                raise jwt.PyJWKClientError(f"no key for kid={kid}")
            return _StubSigningKey(self._key)

    def _fake_fetch(jku):
        return _StubClient(rsa_keypair.public_key())

    monkeypatch.setattr(inbound_jwt, "_fetch_jwks", _fake_fetch)


def _sign(rsa_keypair, *, claims_override=None, header_override=None, alg="RS384", key=None):
    """Sign a JWT with sensible defaults for the happy path; override anything
    you want to break.
    """
    now = int(time.time())
    claims = {
        "iss": TEST_ISS,
        "sub": TEST_ISS,
        "aud": EXPECTED_AUDIENCE,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + 300,
    }
    if claims_override:
        claims.update(claims_override)

    headers = {"kid": TEST_KID, "alg": alg, "jku": TRUSTED_JKU}
    if header_override:
        headers.update(header_override)

    signing_key = key if key is not None else rsa_keypair
    return jwt.encode(claims, signing_key, algorithm=alg, headers=headers)


def _post_token(client, assertion):
    return client.post(
        TOKEN_PATH,
        data={
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        },
        content_type="application/x-www-form-urlencoded",
    )


def _audit_details(app, event_type):
    """Return a list of detail dicts for all audit rows of the given event."""
    with app.app_context():
        rows = AuditLog.query.filter_by(event_type=event_type).all()
        return [json.loads(r.detail) if r.detail else {} for r in rows]


def _audit_rows(app, event_type):
    """Return raw AuditLog rows (use when zoom_account_id is needed)."""
    with app.app_context():
        return AuditLog.query.filter_by(event_type=event_type).all()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_token_endpoint_happy_path(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    assertion = _sign(rsa_keypair)

    resp = _post_token(client, assertion)

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["token_type"] == "bearer"
    assert payload["scope"] == EPIC_DEFAULT_SCOPES
    assert payload["expires_in"] == 3600
    assert payload["access_token"]

    issued = _audit_rows(app, "epic_zcc.token_issued")
    assert len(issued) == 1
    assert issued[0].zoom_account_id == TEST_ACCOUNT_ID
    detail = json.loads(issued[0].detail)
    assert detail["iss"] == TEST_ISS
    assert detail["expires_in"] == 3600


# ---------------------------------------------------------------------------
# Negative cases on the JWT
# ---------------------------------------------------------------------------

def test_token_endpoint_expired_jwt(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    now = int(time.time())
    assertion = _sign(rsa_keypair, claims_override={"iat": now - 3600, "exp": now - 60})

    resp = _post_token(client, assertion)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_grant"
    failed = _audit_details(app, "epic_zcc.token_request_failed")
    assert any(d.get("reason") == "expired" for d in failed)


def test_token_endpoint_bad_signature(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    # Sign with a different key — stubbed JWKS only knows rsa_keypair.public_key()
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assertion = _sign(rsa_keypair, key=attacker_key)

    resp = _post_token(client, assertion)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_grant"
    failed = _audit_details(app, "epic_zcc.token_request_failed")
    assert any(d.get("reason") == "bad_signature" for d in failed)


def test_token_endpoint_replay_rejected(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    jti = str(uuid.uuid4())
    assertion = _sign(rsa_keypair, claims_override={"jti": jti})

    first = _post_token(client, assertion)
    second = _post_token(client, assertion)

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.get_json()["error"] == "invalid_grant"
    failed = _audit_details(app, "epic_zcc.token_request_failed")
    assert any(d.get("reason") == "replay" for d in failed)


def test_token_endpoint_aud_mismatch(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    assertion = _sign(rsa_keypair, claims_override={"aud": "https://other.example/token"})

    resp = _post_token(client, assertion)

    assert resp.status_code == 400
    failed = _audit_details(app, "epic_zcc.token_request_failed")
    assert any(d.get("reason") == "aud_mismatch" for d in failed)


def test_token_endpoint_iss_sub_mismatch(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    assertion = _sign(rsa_keypair, claims_override={"sub": "different-subject"})

    resp = _post_token(client, assertion)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid_client"
    failed = _audit_details(app, "epic_zcc.token_request_failed")
    assert any(d.get("reason") == "iss_sub_mismatch" for d in failed)


def test_token_endpoint_unsupported_alg(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    # HS256 is rejected before we even hit the JWKS — caught by alg allowlist.
    assertion = jwt.encode(
        {
            "iss": TEST_ISS, "sub": TEST_ISS, "aud": EXPECTED_AUDIENCE,
            "jti": str(uuid.uuid4()), "iat": int(time.time()), "exp": int(time.time()) + 300,
        },
        "shared-secret",
        algorithm="HS256",
        headers={"kid": TEST_KID, "jku": TRUSTED_JKU},
    )

    resp = _post_token(client, assertion)

    assert resp.status_code == 400
    failed = _audit_details(app, "epic_zcc.token_request_failed")
    assert any(d.get("reason") == "alg_unsupported" for d in failed)


def test_token_endpoint_untrusted_jku(app, client, rsa_keypair, stub_jwks):
    _seed_account(app)
    assertion = _sign(rsa_keypair, header_override={"jku": "https://evil.example.com/jwks.json"})

    resp = _post_token(client, assertion)

    assert resp.status_code == 400
    failed = _audit_details(app, "epic_zcc.token_request_failed")
    assert any(d.get("reason") == "jku_untrusted" for d in failed)


# ---------------------------------------------------------------------------
# Account resolution
# ---------------------------------------------------------------------------

def test_token_endpoint_unknown_account(app, client, rsa_keypair, stub_jwks):
    # No _seed_account — path account doesn't exist
    assertion = _sign(rsa_keypair)
    resp = _post_token(client, assertion)
    assert resp.status_code == 404


def test_token_endpoint_cti_disabled(app, client, rsa_keypair, stub_jwks):
    _seed_account(app, epic_enabled=False)
    assertion = _sign(rsa_keypair)
    resp = _post_token(client, assertion)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Token store
# ---------------------------------------------------------------------------

def test_token_store_round_trip():
    token, expires_in = token_store.issue_token(TEST_ACCOUNT_ID)
    assert expires_in == 3600
    assert token_store.validate_token(token) == TEST_ACCOUNT_ID


def test_token_store_expired_returns_none(monkeypatch):
    token, _ = token_store.issue_token(TEST_ACCOUNT_ID)
    # Fast-forward time past expiry
    real_time = time.time
    monkeypatch.setattr(token_store.time, "time", lambda: real_time() + 7200)
    assert token_store.validate_token(token) is None


# ---------------------------------------------------------------------------
# Bearer helper
# ---------------------------------------------------------------------------

def test_bearer_helper_accepts_valid_token(app, client, rsa_keypair, stub_jwks):
    """End-to-end: mint token via /oauth2/token, then validate it via the
    helper inside a synthetic request context."""
    from app.blueprints.auth.auth_helpers import verify_bearer_token_in_store
    from flask import g

    _seed_account(app)
    resp = _post_token(client, _sign(rsa_keypair))
    access_token = resp.get_json()["access_token"]

    with app.test_request_context(
        TOKEN_PATH,
        headers={"Authorization": f"Bearer {access_token}"},
    ):
        # Manually populate view_args so the path-account check runs
        from flask import request
        request.view_args = {"zoom_account_id": TEST_ACCOUNT_ID}
        assert verify_bearer_token_in_store() is None
        assert g.bearer_zoom_account_id == TEST_ACCOUNT_ID


def test_bearer_helper_rejects_missing_header(app):
    from app.blueprints.auth.auth_helpers import verify_bearer_token_in_store

    with app.test_request_context("/zoomly/x/interconnect-amcurprd-oauth/x"):
        result = verify_bearer_token_in_store()
        assert result is not None
        body, status = result
        assert status == 401
        assert body.get_json()["error"] == "invalid_token"


def test_bearer_helper_rejects_account_mismatch(app, rsa_keypair, stub_jwks):
    from app.blueprints.auth.auth_helpers import verify_bearer_token_in_store

    _seed_account(app)
    token, _ = token_store.issue_token(TEST_ACCOUNT_ID)
    with app.test_request_context(
        f"/zoomly/some-other-account/interconnect-amcurprd-oauth/x",
        headers={"Authorization": f"Bearer {token}"},
    ):
        from flask import request
        request.view_args = {"zoom_account_id": "some-other-account"}
        result = verify_bearer_token_in_store()
        assert result is not None
        body, status = result
        assert status == 401
        failed = _audit_details(app, "epic_zcc.bearer_token_invalid")
        assert any(d.get("reason") == "account_mismatch" for d in failed)


# ============================================================================
# S11-04 — Per-account JWKS endpoint and build_client_assertion jku kwarg
# ============================================================================


TEST_EPIC_KID = "F9658B7A027904FB43A16DB652A31A6C"
JWKS_PATH = f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/oauth2/keys/1/{TEST_EPIC_KID}"


def _seed_account_with_real_keypair(app, *, epic_kid: str | None = TEST_EPIC_KID) -> str:
    """Seed an active CTI account whose RSA keypair actually exists on disk.

    Writes the keypair into KEYS_BASE_DIR/<account_id>/ via generate_keypair so
    services/keys.py:load_private_key (which derives the path from the account
    ID) can resolve it. Returns the private_key_path stored on the model.
    """
    from app.services.keys import generate_keypair

    with app.app_context():
        private_path, _ = generate_keypair(TEST_ACCOUNT_ID)
        account = ZoomAccount(
            account_id=TEST_ACCOUNT_ID,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=private_path,
            kid=f"zoomly-{TEST_ACCOUNT_ID}",
            epic_kid=epic_kid,
            is_active=True,
        )
        db.session.add(account)
        db.session.add(
            AccountConfig(
                account_id=TEST_ACCOUNT_ID,
                timezone="America/New_York",
                epic_zcc_enabled=True,
            )
        )
        db.session.commit()
        return private_path


def test_jwks_endpoint_happy_path(app, client):
    _seed_account_with_real_keypair(app)

    resp = client.get(JWKS_PATH)

    assert resp.status_code == 200
    body = resp.get_json()
    assert isinstance(body.get("keys"), list)
    assert len(body["keys"]) == 1
    jwk = body["keys"][0]
    assert jwk["kid"] == TEST_EPIC_KID
    assert jwk["kty"] == "RSA"
    assert jwk["use"] == "sig"
    assert "n" in jwk and "e" in jwk

    fetched = _audit_rows(app, "epic_zcc.jwks_fetched")
    assert len(fetched) == 1
    detail = json.loads(fetched[0].detail)
    assert detail["kid"] == TEST_EPIC_KID
    assert detail["version"] == "1"


def test_jwks_endpoint_wrong_kid(app, client):
    _seed_account_with_real_keypair(app)

    resp = client.get(
        f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/oauth2/keys/1/some-other-kid"
    )

    assert resp.status_code == 404


def test_jwks_endpoint_wrong_version(app, client):
    _seed_account_with_real_keypair(app)

    resp = client.get(
        f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/oauth2/keys/2/{TEST_EPIC_KID}"
    )

    assert resp.status_code == 404


def test_jwks_endpoint_account_without_epic_kid(app, client):
    """Account has CTI enabled but Initialize CTI button hasn't been pressed yet."""
    _seed_account_with_real_keypair(app, epic_kid=None)

    resp = client.get(JWKS_PATH)

    assert resp.status_code == 404


def test_jwks_endpoint_cti_disabled(app, client):
    """Blueprint-level gate: epic_zcc_enabled=False returns 404 even with the right kid."""
    from app.services.keys import generate_keypair

    with app.app_context():
        private_path, _ = generate_keypair(TEST_ACCOUNT_ID)
        db.session.add(ZoomAccount(
            account_id=TEST_ACCOUNT_ID,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            private_key_path=private_path,
            kid=f"zoomly-{TEST_ACCOUNT_ID}",
            epic_kid=TEST_EPIC_KID,
            is_active=True,
        ))
        db.session.add(AccountConfig(
            account_id=TEST_ACCOUNT_ID,
            timezone="America/New_York",
            epic_zcc_enabled=False,
        ))
        db.session.commit()

    resp = client.get(JWKS_PATH)
    assert resp.status_code == 404


def test_build_client_assertion_with_jku_header(app, tmp_path):
    """build_client_assertion adds jku to the JWT header when provided."""
    from app.auth.jwt_assertion import build_client_assertion
    from app.services.keys import generate_keypair

    with app.app_context():
        private_path, _ = generate_keypair(TEST_ACCOUNT_ID)
        jku_url = "https://zoom-bridge.example.us/zoomly/x/interconnect-amcurprd-oauth/oauth2/keys/1/abc"
        token = build_client_assertion(
            client_id="test-client",
            audience="https://example/token",
            key_path=private_path,
            key_id="kid-123",
            jku=jku_url,
        )
        header = jwt.get_unverified_header(token)
        assert header["kid"] == "kid-123"
        assert header["jku"] == jku_url


def test_build_client_assertion_without_jku_omits_header(app, tmp_path):
    """Existing OpenEMR call sites pass no jku — header must not contain it."""
    from app.auth.jwt_assertion import build_client_assertion
    from app.services.keys import generate_keypair

    with app.app_context():
        private_path, _ = generate_keypair(TEST_ACCOUNT_ID)
        token = build_client_assertion(
            client_id="test-client",
            audience="https://example/token",
            key_path=private_path,
            key_id="kid-123",
        )
        header = jwt.get_unverified_header(token)
        assert header["kid"] == "kid-123"
        assert "jku" not in header
