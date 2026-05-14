from types import SimpleNamespace

import pytest
import requests

from app.services.openemr import provider
from app.services.openemr.appointments import appointment


def test_get_practitioners_bundle_dedupes_and_normalizes(app, monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "entry": [
                    {
                        "resource": {
                            "id": "pract-1",
                            "active": True,
                            "name": [{"prefix": ["Dr"], "given": ["Jane"], "family": "Doe"}],
                            "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1234567890"}],
                            "telecom": [{"system": "email", "value": "jane@example.com"}],
                        }
                    },
                    {
                        "resource": {
                            "id": "pract-1",  # duplicate id should be ignored
                            "active": False,
                            "name": [{"given": ["Duplicate"], "family": "Provider"}],
                        }
                    },
                    {
                        "resource": {
                            "id": "pract-2",
                            "active": True,
                            "name": [{"given": ["John"], "family": "Smith"}],
                        }
                    },
                ]
            }

    def fake_get(url, headers, params, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse()

    class FakeResult:
        def __init__(self, row):
            self._row = row

        def fetchone(self):
            return self._row

    class FakeConn:
        def execute(self, query, params):
            if params["npi"] == "1234567890":
                return FakeResult(
                    SimpleNamespace(id=10, facility_id=1, facility_name="Zoomly Medical Center")
                )
            return FakeResult(None)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(provider, "get_openemr_token", lambda account: "openemr-token")
    monkeypatch.setattr(provider.requests, "get", fake_get)
    monkeypatch.setattr(provider, "get_openemr_db_engine", lambda: FakeEngine())

    with app.app_context():
        providers = provider.get_practitioners(
            SimpleNamespace(account_id="acct-1"),
            search="doe",
        )

    assert captured["url"] == "http://openemr.internal/apis/default/fhir/Practitioner"
    assert captured["headers"]["Authorization"] == "Bearer openemr-token"
    assert captured["params"] == {"name": "doe"}
    assert captured["timeout"] == 10

    assert providers == [
        {
            "fhir_id": "pract-1",
            "active": True,
            "first_name": "Jane",
            "last_name": "Doe",
            "full_name": "Dr Jane Doe",
            "npi": "1234567890",
            "email": "jane@example.com",
            "user_id": 10,
            "facility_id": 1,
            "facility_name": "Zoomly Medical Center",
        },
        {
            "fhir_id": "pract-2",
            "active": True,
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
            "npi": None,
            "email": None,
            "user_id": None,
            "facility_id": None,
            "facility_name": None,
        },
    ]


def test_get_practitioners_single_resource_fetch(app, monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "pract-99",
                "active": True,
                "name": [{"given": ["Elena"], "family": "Rodriguez"}],
            }

    def fake_get(url, headers, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return DummyResponse()

    monkeypatch.setattr(provider, "get_openemr_token", lambda account: "openemr-token")
    monkeypatch.setattr(provider.requests, "get", fake_get)

    with app.app_context():
        providers = provider.get_practitioners(
            SimpleNamespace(account_id="acct-1"),
            practitioner_id="pract-99",
        )

    assert captured["url"] == "http://openemr.internal/apis/default/fhir/Practitioner/pract-99"
    assert captured["params"] == {}
    assert providers == [
        {
            "fhir_id": "pract-99",
            "active": True,
            "first_name": "Elena",
            "last_name": "Rodriguez",
            "full_name": "Elena Rodriguez",
            "npi": None,
            "email": None,
            "user_id": None,
            "facility_id": None,
            "facility_name": None,
        }
    ]


def test_get_practitioners_propagates_http_error(app, monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            raise requests.HTTPError("openemr 500")

    monkeypatch.setattr(provider, "get_openemr_token", lambda account: "openemr-token")
    monkeypatch.setattr(provider.requests, "get", lambda *args, **kwargs: DummyResponse())

    with app.app_context():
        with pytest.raises(requests.HTTPError, match="openemr 500"):
            provider.get_practitioners(SimpleNamespace(account_id="acct-1"))


def test_normalize_practitioner_defaults_for_missing_fields():
    normalized = provider._normalize_practitioner({})

    assert normalized == {
        "fhir_id": None,
        "active": False,
        "first_name": "",
        "last_name": "",
        "full_name": "",
        "npi": None,
        "email": None,
        "user_id": None,
        "facility_id": None,
        "facility_name": None,
    }


def test_get_appointment_types_returns_transformed_rows(monkeypatch):
    captured = {}

    class FakeConn:
        def execute(self, query):
            captured["query"] = str(query)
            return [
                SimpleNamespace(
                    pc_catid=1,
                    pc_catname="New Patient",
                    pc_catdesc="Initial consult",
                    pc_duration=1800,
                    pc_catcolor="#33AA55",
                ),
                SimpleNamespace(
                    pc_catid=2,
                    pc_catname="Follow-up",
                    pc_catdesc="Established patient follow-up",
                    pc_duration=900,
                    pc_catcolor="#4477CC",
                ),
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    result = appointment.get_appointment_types_list()

    assert "FROM openemr_postcalendar_categories" in captured["query"]
    assert result == [
        {
            "id": "1",
            "name": "New Patient",
            "description": "Initial consult",
            "duration_seconds": 1800,
            "color": "#33AA55",
        },
        {
            "id": "2",
            "name": "Follow-up",
            "description": "Established patient follow-up",
            "duration_seconds": 900,
            "color": "#4477CC",
        },
    ]


def test_get_appointment_types_returns_empty_list_when_no_rows(monkeypatch):
    class FakeConn:
        def execute(self, query):
            return []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment.get_appointment_types_list() == []


def test_get_appointment_details_returns_row(monkeypatch):
    captured = {}

    class FakeConn:
        def execute(self, query, params):
            captured["query"] = str(query)
            captured["params"] = params
            return SimpleNamespace(
                fetchone=lambda: SimpleNamespace(pc_pid=1, pc_aid=10, pc_facility=4, pc_catid=27)
            )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    details = appointment.get_appointment_details(999)

    assert "FROM openemr_postcalendar_events" in captured["query"]
    assert captured["params"] == {"eid": 999}
    assert details == {
        "pid": 1,
        "provider_id": 10,
        "facility_id": 4,
        "pc_catid": 27,
    }


def test_get_appointment_details_returns_none_when_missing(monkeypatch):
    class FakeConn:
        def execute(self, query, params):
            return SimpleNamespace(fetchone=lambda: None)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment.get_appointment_details(999) is None


def test_get_appointment_details_returns_none_on_exception(monkeypatch):
    class FakeConn:
        def execute(self, query, params):
            raise RuntimeError("db blew up")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment.get_appointment_details(999) is None


def test_write_zoom_urls_to_appointment_updates_website_with_start_url(monkeypatch):
    captured = {}

    class FakeResult:
        rowcount = 1

    class FakeConn:
        def execute(self, query, params):
            captured["query"] = str(query)
            captured["params"] = params
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    success = appointment.write_zoom_urls_to_appointment(
        eid=999,
        start_url="https://zoom.example/start/999",
        join_url="https://zoom.example/join/999",
    )

    assert success is True
    assert "SET" in captured["query"]
    assert "pc_website" in captured["query"]
    assert captured["params"] == {
        "website": "https://zoom.example/start/999",
        "eid": 999,
    }


def test_write_zoom_urls_to_appointment_returns_false_when_eid_not_found(monkeypatch):
    class FakeResult:
        rowcount = 0

    class FakeConn:
        def execute(self, query, params):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    success = appointment.write_zoom_urls_to_appointment(
        eid=999,
        start_url="https://zoom.example/start/999",
        join_url="https://zoom.example/join/999",
    )

    assert success is False


def test_write_zoom_urls_to_appointment_returns_false_on_exception(monkeypatch):
    class FakeConn:
        def execute(self, query, params):
            raise RuntimeError("db write failed")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    success = appointment.write_zoom_urls_to_appointment(
        eid=999,
        start_url="https://zoom.example/start/999",
        join_url="https://zoom.example/join/999",
    )

    assert success is False


def test_update_appointment_status_updates_row(monkeypatch):
    captured = {}

    class FakeResult:
        rowcount = 1

    class FakeConn:
        def execute(self, query, params):
            captured["query"] = str(query)
            captured["params"] = params
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment.update_appointment_status(123, "@") is True
    assert "pc_apptstatus" in captured["query"]
    assert captured["params"] == {"status": "@", "eid": 123}


def test_update_appointment_status_returns_false_when_eid_missing(monkeypatch):
    class FakeResult:
        rowcount = 0

    class FakeConn:
        def execute(self, query, params):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment.update_appointment_status(123, "x") is False


def test_update_appointment_status_returns_false_on_exception(monkeypatch):
    class FakeConn:
        def execute(self, query, params):
            raise RuntimeError("db failure")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(appointment, "get_openemr_db_engine", lambda: FakeEngine())

    assert appointment.update_appointment_status(123, "x") is False
