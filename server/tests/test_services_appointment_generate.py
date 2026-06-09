"""Tests for generate_future_appointment (Sprint 13 / S13-03)."""

import json
from datetime import date, time

import pytest

from app.models import AuditLog
from app.services.openemr.appointments import appointment as appt_service


class _FakeInsertEngine:
    """
    Mimics `engine.begin() -> conn.execute(...)` for an INSERT.

    Captures the params dict passed to execute so tests can assert on the
    derived fields (end_time, defaulted title, etc.) without needing a real DB.
    """

    def __init__(self, *, lastrowid: int = 12345, raise_on_execute: Exception | None = None):
        self.lastrowid = lastrowid
        self.raise_on_execute = raise_on_execute
        self.captured_params: dict | None = None

    def begin(self):
        outer = self

        class FakeResult:
            def __init__(self):
                self.lastrowid = outer.lastrowid

        class FakeConn:
            def execute(self, query, params):
                outer.captured_params = params
                if outer.raise_on_execute:
                    raise outer.raise_on_execute
                return FakeResult()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return FakeConn()


def _make_account(app_ctx):
    """Create the minimum Flask-side state needed for write_audit_log to persist."""
    from app.extensions import db
    from app.models import ZoomAccount, AccountConfig

    account = ZoomAccount(
        account_id="acct-hydrate",
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path="/tmp/private.pem",
        kid="zoomly-acct-hydrate",
        is_active=True,
    )
    db.session.add(account)
    db.session.add(AccountConfig(account_id="acct-hydrate", timezone="America/Denver"))
    db.session.commit()
    return account


def test_generate_future_appointment_inserts_row_and_returns_eid(app, monkeypatch):
    fake = _FakeInsertEngine(lastrowid=98765)
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: fake,
    )
    # upsert_patient_tracker runs after the INSERT and would clobber the
    # captured_params on the FakeInsertEngine — stub it out for these unit tests.
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.upsert_patient_tracker",
        lambda **kwargs: None,
    )

    with app.app_context():
        _make_account(app)
        eid = appt_service.generate_future_appointment(
            zoom_account_id="acct-hydrate",
            provider_user_id=10,
            facility_id=2,
            patient_pid=100,
            category_id=20,
            category_name="Zoom Behavioral Health",
            slot_date=date(2026, 5, 22),
            slot_time=time(9, 0),
        )

    assert eid == 98765
    assert fake.captured_params["provider_id"] == "10"
    assert fake.captured_params["pid"] == "100"
    assert fake.captured_params["category_id"] == 20
    assert fake.captured_params["facility_id"] == 2


def test_generate_future_appointment_computes_end_time_from_duration(app, monkeypatch):
    fake = _FakeInsertEngine()
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: fake,
    )
    # upsert_patient_tracker runs after the INSERT and would clobber the
    # captured_params on the FakeInsertEngine — stub it out for these unit tests.
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.upsert_patient_tracker",
        lambda **kwargs: None,
    )

    with app.app_context():
        _make_account(app)
        appt_service.generate_future_appointment(
            zoom_account_id="acct-hydrate",
            provider_user_id=10,
            facility_id=2,
            patient_pid=100,
            category_id=20,
            category_name="Zoom Behavioral Health",
            slot_date=date(2026, 5, 22),
            slot_time=time(9, 0),
            duration_seconds=1800,
        )

    assert fake.captured_params["start_time"] == time(9, 0)
    assert fake.captured_params["end_time"] == time(9, 30)


def test_generate_future_appointment_defaults_title_to_category_name(app, monkeypatch):
    fake = _FakeInsertEngine()
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: fake,
    )
    # upsert_patient_tracker runs after the INSERT and would clobber the
    # captured_params on the FakeInsertEngine — stub it out for these unit tests.
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.upsert_patient_tracker",
        lambda **kwargs: None,
    )

    with app.app_context():
        _make_account(app)
        appt_service.generate_future_appointment(
            zoom_account_id="acct-hydrate",
            provider_user_id=10,
            facility_id=2,
            patient_pid=100,
            category_id=20,
            category_name="Zoom Behavioral Health",
            slot_date=date(2026, 5, 22),
            slot_time=time(14, 0),
        )

    assert fake.captured_params["title"] == "Zoom Behavioral Health"


def test_generate_future_appointment_respects_overridden_title(app, monkeypatch):
    fake = _FakeInsertEngine()
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: fake,
    )
    # upsert_patient_tracker runs after the INSERT and would clobber the
    # captured_params on the FakeInsertEngine — stub it out for these unit tests.
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.upsert_patient_tracker",
        lambda **kwargs: None,
    )

    with app.app_context():
        _make_account(app)
        appt_service.generate_future_appointment(
            zoom_account_id="acct-hydrate",
            provider_user_id=10,
            facility_id=2,
            patient_pid=100,
            category_id=20,
            category_name="Zoom Behavioral Health",
            slot_date=date(2026, 5, 22),
            slot_time=time(14, 0),
            title="BH Follow-up",
        )

    assert fake.captured_params["title"] == "BH Follow-up"


def test_generate_future_appointment_writes_success_audit(app, monkeypatch):
    fake = _FakeInsertEngine(lastrowid=555)
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: fake,
    )
    # upsert_patient_tracker runs after the INSERT and would clobber the
    # captured_params on the FakeInsertEngine — stub it out for these unit tests.
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.upsert_patient_tracker",
        lambda **kwargs: None,
    )

    with app.app_context():
        _make_account(app)
        appt_service.generate_future_appointment(
            zoom_account_id="acct-hydrate",
            provider_user_id=10,
            facility_id=2,
            patient_pid=100,
            category_id=20,
            category_name="Zoom Behavioral Health",
            slot_date=date(2026, 5, 22),
            slot_time=time(9, 0),
        )

        audits = AuditLog.query.filter_by(event_type="demo.future_appointment_created").all()
        assert len(audits) == 1
        row = audits[0]
        assert row.success is True
        assert row.zoom_account_id == "acct-hydrate"
        assert row.openemr_appointment_id == "555"
        assert row.openemr_user_id == "10"
        assert row.openemr_patient_id == "100"
        detail = json.loads(row.detail)
        assert detail["category_name"] == "Zoom Behavioral Health"
        assert detail["slot_date"] == "2026-05-22"
        assert detail["facility_id"] == 2


def test_generate_future_appointment_returns_none_and_audits_failure(app, monkeypatch):
    fake = _FakeInsertEngine(raise_on_execute=RuntimeError("connection refused"))
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: fake,
    )
    # upsert_patient_tracker runs after the INSERT and would clobber the
    # captured_params on the FakeInsertEngine — stub it out for these unit tests.
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.upsert_patient_tracker",
        lambda **kwargs: None,
    )

    with app.app_context():
        _make_account(app)
        result = appt_service.generate_future_appointment(
            zoom_account_id="acct-hydrate",
            provider_user_id=10,
            facility_id=2,
            patient_pid=100,
            category_id=20,
            category_name="Zoom Behavioral Health",
            slot_date=date(2026, 5, 22),
            slot_time=time(9, 0),
        )
        assert result is None

        audits = AuditLog.query.filter_by(event_type="demo.future_appointment_create_failed").all()
        assert len(audits) == 1
        row = audits[0]
        assert row.success is False
        assert row.zoom_account_id == "acct-hydrate"
        assert row.openemr_user_id == "10"
        assert row.openemr_patient_id == "100"
        assert "connection refused" in (row.error_message or "")
        # detail still populated even on failure so we can debug which slot blew up
        assert json.loads(row.detail)["slot_time"] == "09:00:00"
