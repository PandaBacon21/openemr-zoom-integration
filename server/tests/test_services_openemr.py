from types import SimpleNamespace

import pytest
import requests

from server.app.services.openemr import openemr


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
                return FakeResult(SimpleNamespace(id=10))
            return FakeResult(None)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(openemr, "get_openemr_token", lambda account: "openemr-token")
    monkeypatch.setattr(openemr.requests, "get", fake_get)
    monkeypatch.setattr("app.extensions.get_openemr_db_engine", lambda: FakeEngine())

    with app.app_context():
        providers = openemr.get_practitioners(
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
            "users_id": 10,
        },
        {
            "fhir_id": "pract-2",
            "active": True,
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
            "npi": None,
            "email": None,
            "users_id": None,
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

    monkeypatch.setattr(openemr, "get_openemr_token", lambda account: "openemr-token")
    monkeypatch.setattr(openemr.requests, "get", fake_get)

    with app.app_context():
        providers = openemr.get_practitioners(
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
            "users_id": None,
        }
    ]


def test_get_practitioners_propagates_http_error(app, monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            raise requests.HTTPError("openemr 500")

    monkeypatch.setattr(openemr, "get_openemr_token", lambda account: "openemr-token")
    monkeypatch.setattr(openemr.requests, "get", lambda *args, **kwargs: DummyResponse())

    with app.app_context():
        with pytest.raises(requests.HTTPError, match="openemr 500"):
            openemr.get_practitioners(SimpleNamespace(account_id="acct-1"))


def test_normalize_practitioner_defaults_for_missing_fields():
    normalized = openemr._normalize_practitioner({})

    assert normalized == {
        "fhir_id": None,
        "active": False,
        "first_name": "",
        "last_name": "",
        "full_name": "",
        "npi": None,
        "email": None,
        "users_id": None,
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

    monkeypatch.setattr("app.extensions.get_openemr_db_engine", lambda: FakeEngine())

    result = openemr.get_appointment_types()

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

    monkeypatch.setattr("app.extensions.get_openemr_db_engine", lambda: FakeEngine())

    assert openemr.get_appointment_types() == []


def test_write_zoom_urls_to_appointment_updates_hometext_and_website(monkeypatch):
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

    monkeypatch.setattr("app.extensions.get_openemr_db_engine", lambda: FakeEngine())

    success = openemr.write_zoom_urls_to_appointment(
        eid=999,
        start_url="https://zoom.example/start/999",
        join_url="https://zoom.example/join/999",
    )

    assert success is True
    assert "SET" in captured["query"]
    assert "pc_hometext" in captured["query"]
    assert "pc_website" in captured["query"]
    assert captured["params"] == {
        "hometext": "Zoom Meeting: https://zoom.example/start/999",
        "website": "https://zoom.example/join/999",
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

    monkeypatch.setattr("app.extensions.get_openemr_db_engine", lambda: FakeEngine())

    success = openemr.write_zoom_urls_to_appointment(
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

    monkeypatch.setattr("app.extensions.get_openemr_db_engine", lambda: FakeEngine())

    success = openemr.write_zoom_urls_to_appointment(
        eid=999,
        start_url="https://zoom.example/start/999",
        join_url="https://zoom.example/join/999",
    )

    assert success is False
