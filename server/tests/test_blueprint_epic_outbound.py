"""Tests for Epic-ZCC outbound initiate-call routing."""

import hashlib
import hmac
import json

import jwt
import pytest

from app.extensions import db
from app.models import AccountConfig, AuditLog, UserMapping, ZoomAccount
from app.services.keys import generate_keypair


TEST_ACCOUNT_ID = "epic-outbound-acct"
TEST_OPENEMR_USER_ID = "42"
TEST_ZCC_USER_ID = "zcc-agent-42"
OUTBOUND_PATH = f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/cti/initiate-call"


@pytest.fixture(autouse=True)
def configure_outbound(app):
    app.config["OPENEMR_FLASK_SECRET"] = "outbound-secret"
    app.config["APP_PUBLIC_URL"] = "https://bridge.example"


def _seed_account(
    app,
    *,
    backend_url: str | None = "us01cciapi.zoom.us",
    with_mapping: bool = True,
    mapping_openemr_user_id: str = TEST_OPENEMR_USER_ID,
    mapping_zcc_user_id: str | None = TEST_ZCC_USER_ID,
    epic_client_id: str | None = "epic-client-id",
    epic_kid: str | None = "ABCDEF0123456789ABCDEF0123456789",
) -> None:
    with app.app_context():
        private_key_path, _ = generate_keypair(TEST_ACCOUNT_ID)
        db.session.add(ZoomAccount(
            account_id=TEST_ACCOUNT_ID,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=private_key_path,
            kid=f"zoomly-{TEST_ACCOUNT_ID}",
            epic_zcc_client_id=epic_client_id,
            epic_kid=epic_kid,
            is_active=True,
        ))
        db.session.add(AccountConfig(
            account_id=TEST_ACCOUNT_ID,
            timezone="America/New_York",
            epic_zcc_enabled=True,
            epic_zcc_backend_url=backend_url,
        ))
        if with_mapping:
            db.session.add(UserMapping(
                zoom_account_id=TEST_ACCOUNT_ID,
                is_provider=False,
                is_zcc_agent=True,
                openemr_user_id=mapping_openemr_user_id,
                zoom_user_email="agent@example.org",
                zoom_user_name="Agent Example",
                zcc_user_id=mapping_zcc_user_id,
                is_active=True,
            ))
        db.session.commit()


class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text
        self.headers: dict = {}

    def json(self):
        import json as _json
        return _json.loads(self.text)


def _signed_post(client, app, payload: dict, *, signature: str | None = None):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if signature is None:
        secret = app.config["OPENEMR_FLASK_SECRET"]
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return client.post(
        OUTBOUND_PATH,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Zoomly-Signature": signature,
        },
    )


def _payload(**overrides) -> dict:
    base = {
        "phone": "+13035550101",
        "openemr_user_id": TEST_OPENEMR_USER_ID,
        "openemr_patient_id": "100",
        "patient_name": "Harrison, James",
    }
    base.update(overrides)
    return base


def _audit_details(app, event_type) -> list[dict]:
    with app.app_context():
        rows = AuditLog.query.filter_by(event_type=event_type).all()
        return [json.loads(r.detail) if r.detail else {} for r in rows]


def test_initiate_call_posts_signed_request_to_zcc(app, client, monkeypatch):
    _seed_account(app)
    captured = {}

    def fake_post(url, json, headers, timeout):
        # Echo EpicCallID back as PhoneSystemCallID, matching ZCC's real behaviour.
        epic_call_id = json["InitiateCallRequest"]["EpicCallID"]
        captured.update({
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        })
        return _FakeResponse(202, f'{{"PhoneSystemCallID":"{epic_call_id}"}}')

    monkeypatch.setattr("app.services.epic.outbound_zcc.requests.post", fake_post)

    resp = _signed_post(client, app, _payload())

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "zcc_status_code": 202}
    assert captured["url"] == (
        f"https://us01cciapi.zoom.us/v1/cci/epic/initiate-call?accId={TEST_ACCOUNT_ID}"
    )

    body = captured["json"]
    assert set(body.keys()) == {"InitiateCallRequest"}
    inner = body["InitiateCallRequest"]
    assert inner["PhoneAgentID"] == TEST_ZCC_USER_ID
    assert inner["OriginPhoneExtension"] == ""
    assert inner["PhoneNumber"] == "+13035550101"
    epic_call_id = inner["EpicCallID"]
    assert epic_call_id  # non-empty UUID generated per call
    assert captured["timeout"] == 10

    auth = captured["headers"]["Authorization"]
    assert auth.startswith("Bearer ")
    token = auth.removeprefix("Bearer ")
    header = jwt.get_unverified_header(token)
    assert header["kid"] == "ABCDEF0123456789ABCDEF0123456789"
    assert header["jku"] == (
        f"https://bridge.example/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/"
        "oauth2/keys/1/ABCDEF0123456789ABCDEF0123456789"
    )
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["iss"] == f"https://bridge.example/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth"
    assert claims["sub"] == "epic-client-id"
    assert claims["aud"] == captured["url"]

    # Outbound call cache should be keyed by ZCC user ID so ReceiveCommunication3
    # can pop the patient using the recipient_id it carries.
    from app.services.epic.outbound_call_cache import get_outbound_call
    assert get_outbound_call(TEST_ACCOUNT_ID, TEST_ZCC_USER_ID) == "100"

    initiated = _audit_details(app, "epic_zcc.click_to_dial_initiated")
    assert initiated[-1]["agent_id"] == TEST_ZCC_USER_ID
    assert initiated[-1]["zcc_status_code"] == 202
    assert initiated[-1]["epic_call_id"] == epic_call_id
    assert initiated[-1]["phone_system_call_id"] == epic_call_id
    assert initiated[-1]["has_patient_context"] is True


def test_initiate_call_rejects_bad_signature(app, client):
    _seed_account(app)

    resp = _signed_post(client, app, _payload(), signature="bad")

    assert resp.status_code == 401
    failed = _audit_details(app, "epic_zcc.click_to_dial_failed")
    assert failed[-1]["reason"] == "invalid_signature"


def test_initiate_call_requires_active_agent_mapping(app, client):
    _seed_account(app, with_mapping=False)

    resp = _signed_post(client, app, _payload())

    assert resp.status_code == 403
    failed = _audit_details(app, "epic_zcc.click_to_dial_failed")
    assert failed[-1]["reason"] == "unknown_agent"


def test_initiate_call_requires_backend_url(app, client):
    _seed_account(app, backend_url=None)

    resp = _signed_post(client, app, _payload())

    assert resp.status_code == 400
    failed = _audit_details(app, "epic_zcc.click_to_dial_failed")
    assert failed[-1]["reason"] == "missing_backend_url"


def test_initiate_call_surfaces_zcc_validation_error_with_phone_redacted(app, client, monkeypatch):
    _seed_account(app)

    def fake_post(url, json, headers, timeout):
        return _FakeResponse(400, '{"error":"bad phone +13035550101 / 13035550101"}')

    monkeypatch.setattr("app.services.epic.outbound_zcc.requests.post", fake_post)

    resp = _signed_post(client, app, _payload())

    assert resp.status_code == 502
    failed = _audit_details(app, "epic_zcc.click_to_dial_failed")
    assert failed[-1]["reason"] == "upstream_error"
    assert failed[-1]["status_code"] == 400
    assert "+13035550101" not in failed[-1]["body_snippet"]
    assert "13035550101" not in failed[-1]["body_snippet"]
    assert "[phone]" in failed[-1]["body_snippet"]
