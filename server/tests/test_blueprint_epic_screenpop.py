"""Tests for Epic-ZCC OpenEMR screen-pop bootstrap and SSE stream."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, urlsplit

import pytest

from app.extensions import db
from app.models import AccountConfig, AuditLog, UserMapping, ZoomAccount
from app.services.epic import screenpop_dispatch
from app.services.epic.constants import EPIC_PATH_SLUG
from app.services.epic.screenpop_auth import make_screenpop_token


TEST_ACCOUNT_ID = "epic-screenpop-acct"
TEST_ACCOUNT_ID_2 = "epic-screenpop-acct-2"
DISABLED_ACCOUNT_ID = "epic-screenpop-disabled"
TEST_OPENEMR_USER_ID = "42"
OTHER_OPENEMR_USER_ID = "84"
BOOTSTRAP_PATH = "/zoomly/epic-zcc/screenpop/bootstrap"


@pytest.fixture(autouse=True)
def reset_screenpop_state(app):
    screenpop_dispatch._subscribers.clear()
    app.config["OPENEMR_FLASK_SECRET"] = "screenpop-secret"
    app.config["APP_PUBLIC_URL"] = "https://bridge.example"
    app.config["OPENEMR_PUBLIC_URL"] = "https://openemr.example"
    yield
    screenpop_dispatch._subscribers.clear()


def _seed_account(
    app,
    account_id: str,
    *,
    openemr_user_id: str = TEST_OPENEMR_USER_ID,
    epic_enabled: bool = True,
    active_mapping: bool = True,
    zcc_user_id: str | None = None,
) -> None:
    with app.app_context():
        db.session.add(ZoomAccount(
            account_id=account_id,
            client_id=f"zoom-client-{account_id}",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{account_id}/private.pem",
            kid=f"zoomly-{account_id}",
            is_active=True,
        ))
        db.session.add(AccountConfig(
            account_id=account_id,
            timezone="America/New_York",
            epic_zcc_enabled=epic_enabled,
        ))
        db.session.add(UserMapping(
            zoom_account_id=account_id,
            is_provider=False,
            is_zcc_agent=True,
            openemr_user_id=openemr_user_id,
            zoom_user_email=f"{openemr_user_id}-{account_id}@example.org",
            zoom_user_name="Agent Example",
            zcc_user_id=zcc_user_id if zcc_user_id is not None else f"zcc-{account_id}",
            is_active=active_mapping,
        ))
        db.session.commit()


def _signed_bootstrap(client, app, payload: dict, *, signature: str | None = None):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if signature is None:
        secret = app.config["OPENEMR_FLASK_SECRET"]
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return client.post(
        BOOTSTRAP_PATH,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Zoomly-Signature": signature,
        },
    )


def _stream_path(app, account_id: str, openemr_user_id: str, *, expires_at: int | None = None) -> str:
    expires_at = expires_at or int(time.time()) + 60
    token = make_screenpop_token(
        app.config["OPENEMR_FLASK_SECRET"],
        account_id,
        openemr_user_id,
        expires_at,
    )
    return (
        f"/zoomly/{account_id}/{EPIC_PATH_SLUG}/screenpop/stream"
        f"?openemr_user_id={openemr_user_id}&expires={expires_at}&token={token}"
    )


def _audit_details(app, event_type) -> list[dict]:
    with app.app_context():
        rows = AuditLog.query.filter_by(event_type=event_type).all()
        return [json.loads(r.detail) if r.detail else {} for r in rows]


def test_bootstrap_returns_streams_for_active_zcc_agent_mappings_only(app, client):
    _seed_account(app, TEST_ACCOUNT_ID)
    _seed_account(app, TEST_ACCOUNT_ID_2, openemr_user_id=OTHER_OPENEMR_USER_ID)
    _seed_account(app, DISABLED_ACCOUNT_ID, epic_enabled=False)

    resp = _signed_bootstrap(client, app, {"openemr_user_id": TEST_OPENEMR_USER_ID})

    assert resp.status_code == 200
    streams = resp.get_json()["streams"]
    assert len(streams) == 1
    assert streams[0]["account_id"] == TEST_ACCOUNT_ID
    assert streams[0]["url"].startswith(
        "https://openemr.example/interface/epic_cti/screenpop_stream.php?"
    )

    parsed = urlsplit(streams[0]["url"])
    params = parse_qs(parsed.query)
    assert params["account_id"] == [TEST_ACCOUNT_ID]
    assert params["openemr_user_id"] == [TEST_OPENEMR_USER_ID]
    assert int(params["expires"][0]) > int(time.time())
    assert params["token"][0]


def test_bootstrap_rejects_bad_signature(app, client):
    _seed_account(app, TEST_ACCOUNT_ID)

    resp = _signed_bootstrap(
        client,
        app,
        {"openemr_user_id": TEST_OPENEMR_USER_ID},
        signature="not-valid",
    )

    assert resp.status_code == 401
    failed = _audit_details(app, "epic_zcc.screenpop_subscribe_failed")
    assert failed[-1]["reason"] == "invalid_signature"


def test_stream_emits_account_scoped_navigate_event_and_unsubscribes(app, client):
    _seed_account(app, TEST_ACCOUNT_ID)
    _seed_account(app, TEST_ACCOUNT_ID_2)

    resp = client.get(
        _stream_path(app, TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID),
        buffered=False,
    )

    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/event-stream")
    assert (TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID) in screenpop_dispatch._subscribers

    other_count = screenpop_dispatch.dispatch(TEST_ACCOUNT_ID_2, TEST_OPENEMR_USER_ID, {
        "type": "navigate",
        "openemr_patient_id": "999",
    })
    assert other_count == 0

    sent_count = screenpop_dispatch.dispatch(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID, {
        "type": "navigate",
        "openemr_patient_id": "100",
        "matched_on": "phone",
        "caller_number": "+13035550101",
    })
    assert sent_count == 1

    text = ""
    for _ in range(3):
        chunk = next(resp.response)
        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
        if "event: navigate\n" in text:
            break
    assert "event: navigate\n" in text
    assert '"openemr_patient_id":"100"' in text
    assert '"caller_number":"+13035550101"' in text

    resp.close()
    assert (TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID) not in screenpop_dispatch._subscribers

    subscribed = _audit_details(app, "epic_zcc.screenpop_subscribed")
    assert subscribed[-1]["expires_at"]
    unsubscribed = _audit_details(app, "epic_zcc.screenpop_unsubscribed")
    assert unsubscribed[-1]["client_ip"]


def test_stream_rejects_expired_token(app, client):
    _seed_account(app, TEST_ACCOUNT_ID)

    resp = client.get(
        _stream_path(
            app,
            TEST_ACCOUNT_ID,
            TEST_OPENEMR_USER_ID,
            expires_at=int(time.time()) - 1,
        )
    )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.content_type
    assert b"event: auth_error" in resp.data
    failed = _audit_details(app, "epic_zcc.screenpop_subscribe_failed")
    assert failed[-1]["reason"] == "expired_token"


def test_stream_rejects_token_for_wrong_account(app, client):
    _seed_account(app, TEST_ACCOUNT_ID)
    expires_at = int(time.time()) + 60
    wrong_token = make_screenpop_token(
        app.config["OPENEMR_FLASK_SECRET"],
        TEST_ACCOUNT_ID_2,
        TEST_OPENEMR_USER_ID,
        expires_at,
    )
    path = (
        f"/zoomly/{TEST_ACCOUNT_ID}/{EPIC_PATH_SLUG}/screenpop/stream"
        f"?openemr_user_id={TEST_OPENEMR_USER_ID}&expires={expires_at}&token={wrong_token}"
    )

    resp = client.get(path)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.content_type
    assert b"event: auth_error" in resp.data
    failed = _audit_details(app, "epic_zcc.screenpop_subscribe_failed")
    assert failed[-1]["reason"] == "invalid_token"


def test_stream_rejects_user_without_active_mapping(app, client):
    _seed_account(app, TEST_ACCOUNT_ID, active_mapping=False)

    resp = client.get(_stream_path(app, TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID))

    assert resp.status_code == 403
    failed = _audit_details(app, "epic_zcc.screenpop_subscribe_failed")
    assert failed[-1]["reason"] == "mapping_not_active"
