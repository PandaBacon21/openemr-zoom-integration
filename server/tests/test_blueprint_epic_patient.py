"""Tests for the Epic PatientLookUp(2012) endpoint and supporting services.

ZCC sends JSON despite Epic's published XML spec. UserID/UserIDType are
per-account Epic background service credentials, not the individual agent.
The cache is keyed by the normalized caller phone number, not by UserID.

OpenEMR's MariaDB is mocked via monkeypatching `get_openemr_db_engine` at
the patient_search module's import binding.
"""

import json
from datetime import date
from xml.etree import ElementTree as ET

import pytest

from app.extensions import db
from app.models import AccountConfig, AuditLog, ZoomAccount
from app.services.epic import lookup_cache, token_store
from app.services.epic.constants import EPIC_XML_NAMESPACE
from app.services.epic.lookup_cache import get_cached_lookup


TEST_ACCOUNT_ID = "epic-patient-acct"
LOOKUP_PATH = f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/api/epic/2012/EMPI/Patient/PATIENTLOOKUP/Lookup"

_NS = {"e": EPIC_XML_NAMESPACE}


@pytest.fixture(autouse=True)
def reset_caches():
    token_store._tokens.clear()
    lookup_cache._cache.clear()
    yield
    token_store._tokens.clear()
    lookup_cache._cache.clear()


def _seed_account(app, *, epic_enabled: bool = True) -> None:
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
        db.session.commit()


def _mint_token() -> str:
    token, _ = token_store.issue_token(TEST_ACCOUNT_ID)
    return token


def _post(client, body: dict, *, token: str | None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return client.post(LOOKUP_PATH, json=body, headers=headers)


# ---------------------------------------------------------------------------
# Fake MariaDB engine
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeRow:
    def __init__(self, **data):
        self._mapping = data


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
        self.last_sql = None
        self.last_params = None

    def execute(self, sql, params=None):
        self.last_sql = str(sql)
        self.last_params = params
        return _FakeResult(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, rows):
        self._rows = rows
        self.last_conn = None

    def connect(self):
        self.last_conn = _FakeConn(self._rows)
        return self.last_conn


def _patch_engine(monkeypatch, rows: list[dict]) -> _FakeEngine:
    engine = _FakeEngine([_FakeRow(**r) for r in rows])
    monkeypatch.setattr(
        "app.services.epic.patient_search.get_openemr_db_engine",
        lambda: engine,
    )
    return engine


def _row(**overrides) -> dict:
    base = {
        "pid": 100,
        "pubpid": "100",
        "uuid_hex": "ac0e9b1f9a5b4e6d8c2a1f3b7d4e5f60",
        "fname": "James",
        "mname": "A",
        "lname": "Harrison",
        "title": "Mr.",
        "DOB": date(1978, 3, 14),
        "sex": "Male",
        "street": "412 Elm Street",
        "city": "Denver",
        "state": "CO",
        "postal_code": "80201",
        "phone_cell": "303-555-0101",
        "phone_home": "",
        "email": "james.harrison@example.org",
        "ssn_last4": "1100",
    }
    base.update(overrides)
    return base


def _audit_details(app, event_type) -> list[dict]:
    with app.app_context():
        rows = AuditLog.query.filter_by(event_type=event_type).all()
        return [json.loads(r.detail) if r.detail else {} for r in rows]


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_phone_only_single_match(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "UserIDType": "dev",
        "Address": {"PhoneNumbers": "303-555-0101"},
    }, token=_mint_token())

    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/xml")
    root = ET.fromstring(resp.data)
    patients = root.findall("e:Patients/e:Patient", _NS)
    assert len(patients) == 1
    name = patients[0].find("e:Name", _NS)
    assert name is not None and name.text == "Harrison, James"

    resolved = _audit_details(app, "epic_zcc.patient_lookup_resolved")
    assert resolved[-1]["match_count"] == 1
    assert resolved[-1]["queried_fields"] == ["phone"]


def test_phone_or_search_returns_multiple_patients(app, client, monkeypatch):
    """OR semantics: one phone shared by mom and kid → both returned."""
    _seed_account(app)
    _patch_engine(monkeypatch, [
        _row(pid=151, pubpid="151", fname="Linda", lname="Chen", phone_cell="617-555-0151"),
        _row(pid=152, pubpid="152", fname="Maya", lname="Chen", phone_cell="617-555-0151"),
    ])

    resp = _post(client, {
        "UserID": "zoomineer",
        "Address": {"PhoneNumbers": "617-555-0151"},
    }, token=_mint_token())

    assert resp.status_code == 200
    patients = ET.fromstring(resp.data).findall("e:Patients/e:Patient", _NS)
    assert len(patients) == 2


def test_phone_list_accepted(app, client, monkeypatch):
    """Address.PhoneNumbers may also be a JSON array."""
    _seed_account(app)
    _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "Address": {"PhoneNumbers": ["303-555-0101"]},
    }, token=_mint_token())

    assert resp.status_code == 200
    patients = ET.fromstring(resp.data).findall("e:Patients/e:Patient", _NS)
    assert len(patients) == 1


def test_dob_only(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "DateOfBirth": "1978-03-14",
    }, token=_mint_token())

    assert resp.status_code == 200
    resolved = _audit_details(app, "epic_zcc.patient_lookup_resolved")
    assert resolved[-1]["queried_fields"] == ["dob"]


def test_patient_id_as_mrn(app, client, monkeypatch):
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "PatientID": "100",
        "PatientIDType": "EPI",
    }, token=_mint_token())

    assert resp.status_code == 200
    assert engine.last_conn.last_params["patient_id"] == "100"
    assert "pubpid" in engine.last_conn.last_sql


def test_patient_id_as_fhir(app, client, monkeypatch):
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "PatientID": "ac0e9b1f9a5b4e6d8c2a1f3b7d4e5f60",
        "PatientIDType": "FHIR",
    }, token=_mint_token())

    assert resp.status_code == 200
    assert "HEX(uuid)" in engine.last_conn.last_sql


def test_ssn_last4_masked_in_response(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "NationalIdentifier": "xxx-xx-1100",
    }, token=_mint_token())

    assert resp.status_code == 200
    masked = ET.fromstring(resp.data).find("e:Patients/e:Patient/e:NationalIdentifier", _NS)
    assert masked is not None and masked.text == "xxx-xx-1100"


def test_phone_or_dob_combines_with_or(app, client, monkeypatch):
    """Both criteria sent: SQL combines with OR, not AND."""
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "Address": {"PhoneNumbers": "303-555-0101"},
        "DateOfBirth": "1978-03-14",
    }, token=_mint_token())

    assert resp.status_code == 200
    assert " OR " in engine.last_conn.last_sql
    assert " AND " not in engine.last_conn.last_sql.upper().replace("WHERE ", "").split("LIMIT", 1)[0]


# ---------------------------------------------------------------------------
# Faults
# ---------------------------------------------------------------------------

def test_insufficient_criteria_fault(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _post(client, {"UserID": "zoomineer"}, token=_mint_token())

    assert resp.status_code == 400
    code = ET.fromstring(resp.data).find("e:Code", _NS)
    assert code is not None and code.text == "INSUFFICIENT-CRITERIA"
    failed = _audit_details(app, "epic_zcc.patient_lookup_failed")
    assert any(d.get("reason") == "insufficient_criteria" for d in failed)


def test_missing_user_id_fault(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _post(client, {"Address": {"PhoneNumbers": "303-555-0101"}}, token=_mint_token())

    assert resp.status_code == 400
    code = ET.fromstring(resp.data).find("e:Code", _NS)
    assert code is not None and code.text == "INVALID-USER"
    failed = _audit_details(app, "epic_zcc.patient_lookup_failed")
    assert any(d.get("reason") == "missing_user" for d in failed)


def test_malformed_json(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {_mint_token()}"}
    resp = client.post(LOOKUP_PATH, data=b"{not-valid-json", headers=headers)

    assert resp.status_code == 400
    failed = _audit_details(app, "epic_zcc.patient_lookup_failed")
    assert any(d.get("reason") == "malformed_xml" for d in failed)


def test_bearer_missing(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _post(client, {"UserID": "zoomineer", "Address": {"PhoneNumbers": "303-555-0101"}}, token=None)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cache — keyed by normalized caller phone, not by UserID
# ---------------------------------------------------------------------------

def test_cache_populated_after_lookup(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [_row()])

    resp = _post(client, {
        "UserID": "zoomineer",
        "Address": {"PhoneNumbers": "303-555-0101"},
    }, token=_mint_token())
    assert resp.status_code == 200

    # Cache key is the normalized 10-digit phone, not the UserID.
    cached = get_cached_lookup(TEST_ACCOUNT_ID, "3035550101")
    assert cached is not None
    assert len(cached["rows"]) == 1
    assert cached["rows"][0]["pubpid"] == "100"


def test_no_match_still_writes_cache(app, client, monkeypatch):
    """Empty result is still cached so RC3 can distinguish 'lookup ran, no match'."""
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _post(client, {
        "UserID": "zoomineer",
        "Address": {"PhoneNumbers": "999-999-9999"},
    }, token=_mint_token())

    assert resp.status_code == 200
    patients = ET.fromstring(resp.data).findall("e:Patients/e:Patient", _NS)
    assert patients == []

    cached = get_cached_lookup(TEST_ACCOUNT_ID, "9999999999")
    assert cached is not None
    assert cached["rows"] == []
