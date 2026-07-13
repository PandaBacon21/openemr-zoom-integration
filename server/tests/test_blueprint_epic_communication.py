"""Tests for Epic ReceiveCommunication3 screen-pop dispatch."""

import json
from datetime import date

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


def _cache_rows(
    rows: list[dict],
    queried_fields: list[str] | None = None,
    phone: str = "3035550101",
) -> None:
    """Seed the lookup cache keyed by normalized caller phone (not agent ID)."""
    lookup_cache.cache_lookup(
        TEST_ACCOUNT_ID,
        phone,
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


def _provider_row(**overrides) -> dict:
    base = {"openemr_user_id": 16, "first_name": "Michael", "last_name": "Chen"}
    base.update(overrides)
    return base


def _cache_provider_rows(rows: list[dict], phone: str = "3035550101") -> None:
    """Seed the provider-namespaced cache (populated by Practitioner.Search)."""
    lookup_cache.cache_lookup(
        TEST_ACCOUNT_ID, phone, rows, ["identifier"], kind="provider"
    )


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


def _provider_payload(**overrides) -> dict:
    """RC3 payload for a provider call: LookupType=Provider + an NPI LookupID."""
    base = _payload(LookupType="Provider", LookupID={"ID": "1223334444", "Type": "NPI"})
    base.update(overrides)
    return base


def test_provider_lookup_npi_match_pops_address_book(app, client, monkeypatch):
    _seed_account(app)
    monkeypatch.setattr(
        "app.services.epic.communication.find_address_book_providers",
        lambda identifier, id_type=None: [{"openemr_user_id": 42, "lname": "OConnor"}],
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(client, _provider_payload(), token=_mint_token())

    assert resp.status_code == 200
    assert resp.get_json() == {"EpicCallID": "call-123"}
    event = q.get_nowait()
    assert event == {
        "type": "navigate",
        "target": "address_book",
        "matched_on": "provider",
        "openemr_provider_user_id": "42",
        "caller_number": "+13035550101",
    }
    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")[-1]
    assert pushed["identifier_type"] == "NPI"
    assert pushed["lookup_source"] == "rc3_identifier"
    assert pushed["provider_match_count"] == 1


def test_provider_lookup_no_match_opens_address_book(app, client, monkeypatch):
    _seed_account(app)
    monkeypatch.setattr(
        "app.services.epic.communication.find_address_book_providers",
        lambda identifier, id_type=None: [],
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _provider_payload(LookupID={"ID": "9999999999", "Type": "NPI"}),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["target"] == "address_book"
    assert event["matched_on"] == "provider_no_match"
    assert event["openemr_provider_user_id"] is None


def test_provider_lookup_missing_identifier_skips_search(app, client, monkeypatch):
    # ZCC serializes a missing NPI as the literal string "undefined" — treat it
    # as no identifier: no DB search, just open the Address Book.
    _seed_account(app)
    calls = {"n": 0}

    def _fake_find(identifier, id_type=None):
        calls["n"] += 1
        return []

    monkeypatch.setattr(
        "app.services.epic.communication.find_address_book_providers", _fake_find
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _provider_payload(LookupID={"ID": "undefined", "Type": "NPI"}),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["target"] == "address_book"
    assert event["matched_on"] == "provider_no_match"
    assert calls["n"] == 0


def test_provider_lookup_falls_back_to_cache_when_no_identifier(app, client):
    # No usable RC3 identifier, but the provider cache (Practitioner.Search,
    # future) has an entry under the caller phone -> use it.
    _seed_account(app)
    _cache_provider_rows([_provider_row(openemr_user_id=16)])
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _provider_payload(LookupID={"ID": "undefined", "Type": "NPI"}),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["target"] == "address_book"
    assert event["matched_on"] == "provider"
    assert event["openemr_provider_user_id"] == "16"


def test_provider_lookup_type_skips_patient_path(app, client, monkeypatch):
    # LookupType=Provider takes the Address Book path even if a patient cache
    # entry exists for the caller — a provider call is never a chart pop.
    _seed_account(app)
    _cache_rows([_row()])
    monkeypatch.setattr(
        "app.services.epic.communication.find_address_book_providers",
        lambda identifier, id_type=None: [{"openemr_user_id": 42}],
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(client, _provider_payload(), token=_mint_token())

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["target"] == "address_book"
    assert q.empty()


def test_outbound_call_pops_calling_modal(app, client):
    # ContactType=Outgoing (click-to-dial) pops the small "Calling…" modal for
    # the dialing agent and does NOT navigate to a chart — no patient lookup.
    _seed_account(app)
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(ContactType="Outgoing", LookupID=None, CallerPhoneNumber="+13032413176"),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event == {
        "type": "navigate",
        "target": "outbound_call",
        "matched_on": "outbound_call",
        "caller_number": "+13032413176",
    }
    assert q.empty()
    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")[-1]
    assert pushed["target"] == "outbound_call"
    assert pushed["caller_number"] == "+13032413176"


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


def test_received_audit_captures_lookup_type_and_raw_request(app, client, monkeypatch):
    """The receive_communication_received audit records LookupType + the caller
    number and the verbatim body — the values driving the RC3 provider branch."""
    _seed_account(app)
    # Isolate the route's intake audit from the handler (no DB search needed).
    monkeypatch.setattr(
        "app.blueprints.epic.communication_routes.process_receive_communication",
        lambda *a, **k: None,
    )

    resp = _post(
        client,
        _payload(LookupType="Provider", CallerPhoneNumber="+13035550142"),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    received = _audit_details(app, "epic_zcc.receive_communication_received")[-1]
    assert received["lookup_type"] == "Provider"
    assert received["caller_number"] == "+13035550142"
    assert "Provider" in received["raw_request"]


def test_receive_communication_unknown_agent_returns_ack_and_audit(app, client):
    _seed_account(app, with_mapping=False)
    _cache_rows([_row()])

    resp = _post(client, _payload(), token=_mint_token())

    assert resp.status_code == 200
    assert resp.get_json() == {"EpicCallID": "call-123"}
    failed = _audit_details(app, "epic_zcc.receive_communication_failed")
    assert any(d.get("reason") == "unknown_agent" for d in failed)


def test_receive_communication_no_lookup_criteria_is_audited(app, client):
    # No PatientLookUp cache, no LookupID, no phone — should fail gracefully.
    _seed_account(app)
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(LookupID=None, CallerPhoneNumber=None, DialedPhoneNumber=None),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    assert q.empty()
    failed = _audit_details(app, "epic_zcc.receive_communication_failed")
    assert any(d.get("reason") == "no_lookup_criteria" for d in failed)


def test_receive_communication_phone_no_match_dispatches_search_navigate(app, client, monkeypatch):
    # No PatientLookUp cache, no LookupID; phone lookup returns no results — dispatches
    # no_match navigate so JS can open the new patient entry form.
    _seed_account(app)
    monkeypatch.setattr(
        "app.services.epic.communication.search_patients",
        lambda criteria: ([], ["phone"]),
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(client, _payload(LookupID=None), token=_mint_token())

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["type"] == "navigate"
    assert "openemr_patient_id" not in event
    assert "candidates" not in event
    assert event["caller_number"] == "+13035550101"
    assert event["matched_on"] == "no_match"
    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")
    assert pushed[-1]["matched_on"] == "no_match"


def test_receive_communication_phone_lookup_single_match_pops_patient(app, client, monkeypatch):
    # No PatientLookUp cache, no LookupID; phone lookup returns exactly one match.
    _seed_account(app)
    monkeypatch.setattr(
        "app.services.epic.communication.search_patients",
        lambda criteria: ([_row(pid=100, _matched_on=["phone"])], ["phone"]),
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(client, _payload(LookupID=None), token=_mint_token())

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["type"] == "navigate"
    assert event["openemr_patient_id"] == "100"
    assert event["matched_on"] == "phone"
    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")
    assert pushed[-1]["recipient_id"] == TEST_ZCC_USER_ID


def test_receive_communication_dob_lookup_pops_patient(app, client, monkeypatch):
    # ZCC sends DOB via LookupInformation without calling PatientLookUp first.
    # Should resolve patient by DOB and dispatch navigate.
    _seed_account(app)
    monkeypatch.setattr(
        "app.services.epic.communication.search_patients",
        lambda criteria: ([_row(pid=105, _matched_on=["dob"])], ["dob"]),
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(
            LookupID=None,
            LookupInformation="1985-03-15",
            LookupInformationType="DOB",
        ),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["type"] == "navigate"
    assert event["openemr_patient_id"] == "105"
    assert event["matched_on"] == "dob"
    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")
    assert pushed[-1]["matched_on"] == "dob"


def test_receive_communication_patient_not_in_cache_returns_ack_and_audit(app, client):
    # Two candidates from PatientLookUp — RC3 must pick one. MRN "999" matches
    # neither, so the call fails with patient_not_in_cache. (A single-candidate
    # cache always uses the one row directly without discrimination.)
    _seed_account(app)
    _cache_rows([_row(pid=100, pubpid="100"), _row(pid=101, pubpid="101", uuid_hex="b" * 32)])
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


def test_receive_communication_dob_cache_discriminates_single_match(app, client):
    # PatientLookUp ran with DOB+phone -> cache written keyed by phone.
    # ZCC RC3 echoes DOB as the highest-priority identifier.
    # _patient_id_matches must handle DOB type so the cached row is found.
    _seed_account(app)
    _cache_rows([_row(DOB=date(1991, 8, 27))])
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(LookupID=None, LookupInformation="1991-08-27", LookupInformationType="DOB"),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["type"] == "navigate"
    assert event["openemr_patient_id"] == "100"


def test_receive_communication_ss_cache_discriminates_single_match(app, client):
    # PatientLookUp ran with SS+phone -> cache written keyed by phone.
    # ZCC RC3 echoes SS (last 4) as the highest-priority identifier.
    # _patient_id_matches must handle SS type so the cached row is found.
    _seed_account(app)
    _cache_rows([_row(ssn_last4="6789")])
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(LookupID=None, LookupInformation="6789", LookupInformationType="SS"),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["type"] == "navigate"
    assert event["openemr_patient_id"] == "100"


def test_receive_communication_multi_match_cache_dispatches_picker(app, client):
    # Two PatientLookUp candidates both match phone — RC3 discriminator (PH) hits
    # both rows. Picker event must carry both candidates with matched_fields.
    _seed_account(app)
    _cache_rows([
        _row(pid=100, pubpid="100", phone_cell="+13035550101", _matched_on=["phone"]),
        _row(pid=101, pubpid="101", uuid_hex="b" * 32, phone_cell="+13035550101", _matched_on=["phone"]),
    ])
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(LookupID={"ID": "+13035550101", "Type": "PH"}),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["type"] == "navigate"
    assert event["matched_on"] == "multi_match"
    assert "openemr_patient_id" not in event
    candidates = event["candidates"]
    assert len(candidates) == 2
    assert {c["pid"] for c in candidates} == {"100", "101"}
    for c in candidates:
        assert c["matched_fields"] == ["phone"]
    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")
    assert pushed[-1]["matched_on"] == "multi_match"
    assert pushed[-1]["match_count"] == 2


def test_receive_communication_direct_ambiguous_dispatches_picker(app, client, monkeypatch):
    # No cache; direct phone search returns 2 matches — picker must be dispatched.
    _seed_account(app)
    rows = [
        _row(pid=100, pubpid="100", phone_cell="+13035550101", _matched_on=["phone"]),
        _row(pid=101, pubpid="101", uuid_hex="b" * 32, phone_cell="+13035550101", _matched_on=["phone"]),
    ]
    monkeypatch.setattr(
        "app.services.epic.communication.search_patients",
        lambda criteria: (rows, ["phone"]),
    )
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(client, _payload(LookupID=None), token=_mint_token())

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["type"] == "navigate"
    assert event["matched_on"] == "multi_match"
    assert "openemr_patient_id" not in event
    candidates = event["candidates"]
    assert len(candidates) == 2
    assert {c["pid"] for c in candidates} == {"100", "101"}
    for c in candidates:
        assert c["matched_fields"] == ["phone"]
    pushed = _audit_details(app, "epic_zcc.receive_communication_pushed")
    assert pushed[-1]["matched_on"] == "multi_match"


def test_outbound_ignores_patient_cache_and_pops_calling_modal(app, client):
    # Even with a patient cache entry for the caller phone, an outbound
    # click-to-dial (ContactType=Outgoing) pops the "Calling…" modal and never
    # navigates to a chart.
    _seed_account(app)
    _cache_rows([_row()], phone="3035550101")
    q = screenpop_dispatch.subscribe(TEST_ACCOUNT_ID, TEST_OPENEMR_USER_ID)

    resp = _post(
        client,
        _payload(
            LookupID=None,
            ContactType="Outgoing",
            CallerPhoneNumber="+13035550101",  # dialed patient number
            DialedPhoneNumber="+17195817290",  # ZCC agent-side number
        ),
        token=_mint_token(),
    )

    assert resp.status_code == 200
    event = q.get_nowait()
    assert event["target"] == "outbound_call"
    assert event["caller_number"] == "+13035550101"
    assert "openemr_patient_id" not in event
    assert q.empty()
