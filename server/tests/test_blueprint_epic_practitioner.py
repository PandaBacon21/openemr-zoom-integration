"""Tests for the Epic FHIR R4 Practitioner.Search endpoint."""

import json

import pytest

from app.extensions import db
from app.models import AccountConfig, AuditLog, ZoomAccount
from app.services.epic import lookup_cache, token_store


TEST_ACCOUNT_ID = "epic-practitioner-acct"
PRACTITIONER_PATH = (
    f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/api/FHIR/R4/Practitioner"
)


@pytest.fixture(autouse=True)
def reset_token_store():
    token_store._tokens.clear()
    yield
    token_store._tokens.clear()


@pytest.fixture(autouse=True)
def reset_lookup_cache():
    lookup_cache._cache.clear()
    yield
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


def _get(client, query_string: dict | None = None, *, token: str | None):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return client.get(PRACTITIONER_PATH, query_string=query_string or {}, headers=headers)


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
        "app.services.epic.practitioner_search.get_openemr_db_engine",
        lambda: engine,
    )
    return engine


def _row(**overrides) -> dict:
    base = {
        "openemr_user_id": 16,
        "fhir_id": "ac0e9b1f9a5b4e6d8c2a1f3b7d4e5f60",
        "fname": "Michael",
        "mname": "",
        "lname": "Chen",
        "title": "Dr.",
        "email": "michael.chen@example.org",
        "npi": "1234567896",
        "active": 1,
        "facility_id": 1,
        "facility_name": "Zoomly Medical Center Mountain",
        "physician_type": "MD",
        "specialty": "Internal Medicine",
    }
    base.update(overrides)
    return base


def _audit_details(app, event_type) -> list[dict]:
    with app.app_context():
        rows = AuditLog.query.filter_by(event_type=event_type).all()
        return [json.loads(r.detail) if r.detail else {} for r in rows]


def _outcome_code(body: dict) -> str:
    return body["issue"][0]["details"]["coding"][0]["code"]


def test_identifier_npi_returns_practitioner_bundle(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [_row()])

    resp = _get(client, {"identifier": "1234567896"}, token=_mint_token())

    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/fhir+json")
    body = resp.get_json()
    assert body["resourceType"] == "Bundle"
    assert body["type"] == "searchset"
    assert body["total"] == 1

    resource = body["entry"][0]["resource"]
    assert resource["resourceType"] == "Practitioner"
    assert resource["id"] == "ac0e9b1f9a5b4e6d8c2a1f3b7d4e5f60"
    assert resource["active"] is True
    assert resource["name"][0]["family"] == "Chen"
    assert resource["name"][0]["given"] == ["Michael"]
    assert resource["telecom"] == [{"system": "email", "value": "michael.chen@example.org"}]
    assert {
        "use": "usual",
        "type": {"text": "NPI"},
        "system": "http://hl7.org/fhir/sid/us-npi",
        "value": "1234567896",
    } in resource["identifier"]

    resolved = _audit_details(app, "epic_zcc.practitioner_lookup_resolved")
    assert resolved[-1]["match_count"] == 1
    assert resolved[-1]["search_type"] == "identifier"


def test_identifier_with_system_prefix_uses_npi_and_ignores_other_params(app, client, monkeypatch):
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row()])

    resp = _get(
        client,
        {
            "identifier": "http://hl7.org/fhir/sid/us-npi|1234567896",
            "family": "Wrong",
        },
        token=_mint_token(),
    )

    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1
    assert engine.last_conn.last_params["identifier_value"] == "1234567896"
    assert "u.npi = :identifier_value" in engine.last_conn.last_sql
    where_sql = engine.last_conn.last_sql.split("WHERE", 1)[1].split("ORDER BY", 1)[0]
    assert "u.lname" not in where_sql


def test_family_and_given_search(app, client, monkeypatch):
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row()])

    resp = _get(client, {"family": "chen", "given": "michael"}, token=_mint_token())

    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1
    assert engine.last_conn.last_params["family"] == "%chen%"
    assert engine.last_conn.last_params["given"] == "%michael%"
    assert "LOWER(u.lname) LIKE :family" in engine.last_conn.last_sql
    assert "LOWER(u.fname) LIKE :given" in engine.last_conn.last_sql


def test_name_search(app, client, monkeypatch):
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row()])

    resp = _get(client, {"name": "Michael Chen"}, token=_mint_token())

    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1
    assert engine.last_conn.last_params["name"] == "%michael chen%"


def test_no_match_returns_empty_bundle(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _get(client, {"identifier": "9999999999"}, token=_mint_token())

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 0
    assert body["entry"] == []


def test_missing_minimum_search_params_returns_operation_outcome(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _get(client, {"address-city": "Denver"}, token=_mint_token())

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["resourceType"] == "OperationOutcome"
    assert _outcome_code(body) == "4110"
    failed = _audit_details(app, "epic_zcc.practitioner_lookup_failed")
    assert any(d.get("reason") == "missing_search_parameters" for d in failed)


def test_given_without_family_returns_operation_outcome(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _get(client, {"given": "Michael"}, token=_mint_token())

    assert resp.status_code == 400
    assert _outcome_code(resp.get_json()) == "4111"
    failed = _audit_details(app, "epic_zcc.practitioner_lookup_failed")
    assert any(d.get("reason") == "given_without_family" for d in failed)


def test_bearer_missing(app, client, monkeypatch):
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _get(client, {"identifier": "1234567896"}, token=None)

    assert resp.status_code == 401


def test_identifier_tax_id_oid_searches_federaltaxid_and_returns_tin(app, client, monkeypatch):
    """TIN search via the Epic OID system matches federaltaxid (digits) and the
    bundle returns a TIN identifier per spec."""
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row(federaltaxid="84-1000016")])

    resp = _get(
        client,
        {"identifier": "urn:oid:2.16.840.1.113883.4.4|84-1000016"},
        token=_mint_token(),
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert engine.last_conn.last_params["tin_digits"] == "841000016"
    assert "REGEXP_REPLACE(u.federaltaxid" in engine.last_conn.last_sql
    assert {
        "use": "usual",
        "type": {"text": "TIN"},
        "system": "urn:oid:2.16.840.1.113883.4.4",
        "value": "84-1000016",
    } in body["entry"][0]["resource"]["identifier"]


def test_identifier_tin_token_searches_federaltaxid(app, client, monkeypatch):
    """The friendly TIN|<value> token form also targets federaltaxid."""
    _seed_account(app)
    engine = _patch_engine(monkeypatch, [_row(federaltaxid="84-1000016")])

    resp = _get(client, {"identifier": "TIN|841000016"}, token=_mint_token())

    assert resp.status_code == 200
    assert engine.last_conn.last_params["tin_digits"] == "841000016"
    assert "REGEXP_REPLACE(u.federaltaxid" in engine.last_conn.last_sql


def test_lookup_caches_provider_by_own_phone(app, client, monkeypatch):
    """A matched provider is cached under its own phone digits (kind='provider')
    so ReceiveCommunication3 can resolve the pop by CallerPhoneNumber — even
    though the search was by NPI (spec-faithful; no phone search param)."""
    _seed_account(app)
    _patch_engine(monkeypatch, [_row(phonecell="303-555-0199")])

    resp = _get(client, {"identifier": "1234567896"}, token=_mint_token())

    assert resp.status_code == 200
    cached = lookup_cache.get_cached_lookup(TEST_ACCOUNT_ID, "3035550199", kind="provider")
    assert cached is not None
    assert len(cached["rows"]) == 1
    assert str(cached["rows"][0]["openemr_user_id"]) == "16"
    # Not stored under the patient namespace.
    assert lookup_cache.get_cached_lookup(TEST_ACCOUNT_ID, "3035550199") is None

    resolved = _audit_details(app, "epic_zcc.practitioner_lookup_resolved")
    assert resolved[-1]["provider_cache_keys"] >= 1


def test_lookup_without_provider_phone_caches_nothing(app, client, monkeypatch):
    """No stored phone on the matched provider → no cache key (graceful)."""
    _seed_account(app)
    _patch_engine(monkeypatch, [_row()])

    resp = _get(client, {"identifier": "1234567896"}, token=_mint_token())

    assert resp.status_code == 200
    resolved = _audit_details(app, "epic_zcc.practitioner_lookup_resolved")
    assert resolved[-1]["provider_cache_keys"] == 0


def test_phone_is_not_a_search_parameter(app, client, monkeypatch):
    """Spec-faithful: phone alone is not a valid Practitioner.Search key, so it
    falls through to the missing-parameters OperationOutcome."""
    _seed_account(app)
    _patch_engine(monkeypatch, [])

    resp = _get(client, {"phone": "3035550142"}, token=_mint_token())

    assert resp.status_code == 400
    assert _outcome_code(resp.get_json()) == "4110"
