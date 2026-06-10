"""Tests for Epic ReceiveCommunication3 screen-pop dispatch."""

import json

import pytest

from app.extensions import db
from app.models import AccountConfig, AuditLog, UserMapping, ZoomAccount
from app.services.epic import lookup_cache, screenpop_dispatch, token_store


TEST_ACCOUNT_ID = "epic-communication-acct"
TEST_OPENEMR_USER_ID = "42"
TEST_ZCC_USER_ID = "zcc-agent-42"
COMMUNICATION_PATH = (
    f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth"
    "/api/epic/2023/Common/Utility/RECEIVECOMMUNICATION3/ReceiveCommunication3"
)


@pytest.fixture(autouse=True)
def reset_epic_state():
    token_store._tokens.clear()
    lookup_cache._cache.clear()
    screenpop_dispatch._subscribers.clear()
    yield
    token_store._tokens.clear()
    lookup_cache._cache.clear()
    screenpop_dispatch._subscribers.clear()


def _seed_account(app, *, with_mapping: bool = True, epic_enabled: bool = True) -> None:
    with app.app_context():
        db.session.add(ZoomAccount(
            account_id=TEST_ACCOUNT_ID,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{TEST_ACCOUNT_ID}/private.pem",
            kid=f"zoomly-{TEST_ACCOUNT_ID}",
            is_active=True,
        ))
        db.session.add(AccountConfig(
            account_id=TEST_ACCOUNT_ID,
            timezone="America/New_York",
            epic_zcc_enabled=epic_enabled,
        ))
        if with_mapping:
            db.session.add(UserMapping(
                zoom_account_id=TEST_ACCOUNT_ID,
                is_provider=False,
                is_zcc_agent=True,
                openemr_user_id=TEST_OPENEMR_USER_ID,
                zoom_user_email="agent@example.org",
                zoom_user_name="Agent Example",
                zcc_user_id=TEST_ZCC_USER_ID,
                is_active=True,
            ))
        db.session.commit()


def _mint_token() -> str:
    token, _ = token_store.issue_token(TEST_ACCOUNT_ID)
    return token


def _post(client, payload: dict, *, token: str | None):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return client.post(COMMUNICATION_PATH, json=payload, headers=headers)


def _cache_rows(rows: list[dict], queried_fields: list[str] | None = None) -> None:
    lookup_cache.cache_lookup(
        TEST_ACCOUNT_ID,
        TEST_OPENEMR_USER_ID,
        rows,
        queried_fields or ["phone"],
    )


def _row(**overrides) -> dict:
    base = {
        "pid": 100,
        "pubpid": "100",
        "uuid_hex": "ac0e9b1f9a5b4e6d8c2a1f3b7d4e5f60",
        "_matched_on": ["phone"],
    }
    base.update(overrides)
    return base


def _payload(**overrides) -> dict:
    base = {
        "RecipientID": TEST_ZCC_USER_ID,
        "RecipientIDType": "External",
        "LookupType": "Patient",
        "LookupID": {"ID": "100", "Type": "MRN"},
        "CallID": "call-123",
        "ContactType": "Incoming",
        "CommunicationType": "Phone",
        "CallerPhoneNumber": "+13035550101",
        "DialedPhoneNumber": "+13035550199",
        "PhoneSystemID": {"ID": "zoomly-phone", "Type": "External"},
    }
    base.update(overrides)
    return base


def _audit_details(app, event_type) -> list[dict]:
    with app.app_context():
        rows = AuditLog.query.filter_by(event_type=event_type).all()
        return [json.loads(r.detail) if r.detail else {} for r in rows]


def test_receive_communication_pushes_cached_match_to_subscriber(app, client):
    _seed_account(app)
    _cache_rows([_row()])
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)
    other_account_q = screenpop_dispatch.subscribe("other-account", TEST_OPENEMR_USER_ID)

    resp = _post(client, _payload(), token=_mint_token())

    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/json")
    assert resp.get_json() == {"EpicCallID": "call-123"}

    event = q.get_nowait()
    assert event == {
        "type": "navigate",
        "openemr_patient_id": "100",
        "matched_on": "phone",
        "caller_number": "+13035550101",
    }

    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")
    assert pushed[-1]["recipient_id"] == TEST_ZCC_USER_ID
    assert pushed[-1]["subscriber_count"] == 1
    assert other_account_q.empty()


def test_receive_communication_selects_patient_from_multi_match_cache(app, client):
    _seed_account(app)
    _cache_rows([
        _row(pid=100, pubpid="100"),
        _row(pid=151, pubpid="151", uuid_hex="f" * 32, _matched_on=["mrn"]),
    ])
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(LookupID={"ID": "151", "Type": "MRN"}),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["openemr_patient_id"] == "151"
    assert event["matched_on"] == "mrn"


def test_receive_communication_unknown_agent_returns_ack_and_audit(app, client):
    _seed_account(app, with_mapping=False)
    _cache_rows([_row()])

    resp = _post(client, _payload(), token=_mint_token())

    assert resp.status_code == 200
    assert resp.get_json() == {"EpicCallID": "call-123"}
    failed = _audit_details(app, "epic_zcc.receive_communication_failed")
    assert any(d.get("reason") == "unknown_agent" for d in failed)


def test_receive_communication_no_cached_lookup_returns_ack_and_audit(app, client):
    _seed_account(app)
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(client, _payload(), token=_mint_token())

    assert resp.status_code == 200
    assert q.empty()
    failed = _audit_details(app, "epic_zcc.receive_communication_failed")
    assert any(d.get("reason") == "no_cached_lookup" for d in failed)


def test_receive_communication_patient_not_in_cache_returns_ack_and_audit(app, client):
    _seed_account(app)
    _cache_rows([_row(pid=100, pubpid="100")])
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(LookupID={"ID": "999", "Type": "MRN"}),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    assert q.empty()
    failed = _audit_details(app, "epic_zcc.receive_communication_failed")
    assert any(d.get("reason") == "patient_not_in_cache" for d in failed)


def test_receive_communication_missing_bearer_returns_401(app, client):
    _seed_account(app)

    resp = _post(client, _payload(), token=None)

    assert resp.status_code == 401


def test_receive_communication_missing_recipient_returns_fault(app, client):
    _seed_account(app)
    payload = _payload()
    payload.pop("RecipientID")

    resp = _post(client, payload, token=_mint_token())

    assert resp.status_code == 400
    assert resp.get_json()["ErrorCode"] == "NO-USER-ID"
    failed = _audit_details(app, "epic_zcc.receive_communication_failed")
    assert any(d.get("reason") == "missing_recipient" for d in failed)
