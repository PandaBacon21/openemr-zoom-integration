from types import SimpleNamespace

from app.extensions import db
from app.models import AppointmentTypeFilter, ProviderMapping, ZoomAccount
from app.services import appointment_processor


BASE_PAYLOAD = {
    "event": "appointment.set",
    "eid": 999,
    "pid": 1,
    "provider_id": 10,
    "category_id": 27,
    "appointment_date": "20260420",
    "appointment_time": "10:00",
    "appt_status": "^",
    "facility_id": 1,
    "comments": "Test appointment",
    "fired_at": "2026-04-19T14:00:00+00:00",
}


def _create_account(account_id: str, *, is_active: bool = True) -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path=f"/tmp/keys/{account_id}/private.pem",
        kid=f"zoomly-{account_id}",
        timezone="America/Denver",
        is_active=is_active,
    )
    db.session.add(account)
    db.session.commit()
    return account


def _create_provider_mapping(account: ZoomAccount, npi: str = "1234567890") -> ProviderMapping:
    mapping = ProviderMapping(
        zoom_account_id=account.id,
        openemr_fhir_id="pract-1",
        openemr_provider_npi=npi,
        openemr_provider_name="Dr Jane Doe",
        zoom_user_id="u-1",
        zoom_user_email="jane@example.com",
        zoom_user_name="Dr Jane Doe",
        zoom_user_type=2,
        is_active=True,
    )
    db.session.add(mapping)
    db.session.commit()
    return mapping


def _create_type_filter(account: ZoomAccount, type_id: str) -> AppointmentTypeFilter:
    f = AppointmentTypeFilter(
        zoom_account_id=account.id,
        openemr_type_id=type_id,
        openemr_type_name=f"Type {type_id}",
    )
    db.session.add(f)
    db.session.commit()
    return f


def test_lookup_npi_for_provider_id_returns_none_when_no_user(monkeypatch):
    class FakeResult:
        def fetchone(self):
            return None

    class FakeConn:
        def execute(self, query, params):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(appointment_processor, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment_processor._lookup_npi_for_provider_id(10) is None


def test_lookup_npi_for_provider_id_returns_none_when_npi_blank(monkeypatch):
    class FakeResult:
        def fetchone(self):
            return SimpleNamespace(npi="")

    class FakeConn:
        def execute(self, query, params):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(appointment_processor, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment_processor._lookup_npi_for_provider_id(10) is None


def test_lookup_npi_for_provider_id_returns_npi(monkeypatch):
    captured = {}

    class FakeResult:
        def fetchone(self):
            return SimpleNamespace(npi="1234567890")

    class FakeConn:
        def execute(self, query, params):
            captured["params"] = params
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(appointment_processor, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment_processor._lookup_npi_for_provider_id(10) == "1234567890"
    assert captured["params"] == {"uid": 10}


def test_filter_appointment_event_drops_when_provider_missing():
    payload = dict(BASE_PAYLOAD)
    payload.pop("provider_id")
    assert appointment_processor.filter_appointment_event(payload) == []


def test_filter_appointment_event_drops_by_provider_id(app, monkeypatch):
    payload = dict(BASE_PAYLOAD)
    payload["provider_id"] = 99

    monkeypatch.setattr(
        appointment_processor,
        "_lookup_npi_for_provider_id",
        lambda provider_id: "1234567890" if provider_id == 10 else None,
    )

    with app.app_context():
        assert appointment_processor.filter_appointment_event(payload) == []


def test_filter_appointment_event_matches_when_no_type_filters(app, monkeypatch):
    monkeypatch.setattr(appointment_processor, "_lookup_npi_for_provider_id", lambda provider_id: "1234567890")

    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        mapping = _create_provider_mapping(account, npi="1234567890")

        payload = dict(BASE_PAYLOAD)
        payload["category_id"] = 99  # no filters configured => all types pass
        matches = appointment_processor.filter_appointment_event(payload)

    assert len(matches) == 1
    assert matches[0].zoom_account.account_id == "acct-1"
    assert matches[0].provider_mapping.id == mapping.id
    assert matches[0].payload["eid"] == 999


def test_filter_appointment_event_drops_by_category_id(app, monkeypatch):
    monkeypatch.setattr(appointment_processor, "_lookup_npi_for_provider_id", lambda provider_id: "1234567890")

    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_provider_mapping(account, npi="1234567890")
        _create_type_filter(account, "27")

        payload = dict(BASE_PAYLOAD)
        payload["category_id"] = 99
        assert appointment_processor.filter_appointment_event(payload) == []


def test_filter_appointment_event_matches_allowed_category(app, monkeypatch):
    monkeypatch.setattr(appointment_processor, "_lookup_npi_for_provider_id", lambda provider_id: "1234567890")

    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_provider_mapping(account, npi="1234567890")
        _create_type_filter(account, "27")

        payload = dict(BASE_PAYLOAD)
        payload["category_id"] = 27
        matches = appointment_processor.filter_appointment_event(payload)

    assert len(matches) == 1
    assert matches[0].zoom_account.account_id == "acct-1"
