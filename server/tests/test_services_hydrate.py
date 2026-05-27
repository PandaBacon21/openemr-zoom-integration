"""Tests for the Sprint 13 demo hydration orchestrator (S13-04b)."""

import json
from datetime import date, time
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import (
    AccountConfig,
    AppointmentTypeFilter,
    AuditLog,
    MeetingRecord,
    ProviderMapping,
    ZoomAccount,
)
from app.services import hydrate as hydrate_service


# --- fixtures ---------------------------------------------------------------

def _create_account(account_id: str = "acct-hydrate") -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path="/tmp/private.pem",
        kid=f"zoomly-{account_id}",
        is_active=True,
    )
    db.session.add(account)
    db.session.add(AccountConfig(account_id=account_id, timezone="America/Denver"))
    db.session.commit()
    return account


def _create_mapping(
    account_id: str,
    *,
    openemr_provider_id: str,
    openemr_facility_id: int | None = 2,
    npi: str | None = None,
) -> ProviderMapping:
    mapping = ProviderMapping(
        zoom_account_id=account_id,
        openemr_fhir_id=f"fhir-{openemr_provider_id}",
        openemr_provider_npi=npi or f"npi-{openemr_provider_id}",
        openemr_provider_id=openemr_provider_id,
        openemr_provider_name=f"Dr {openemr_provider_id}",
        zoom_user_id=f"user-{openemr_provider_id}",
        zoom_user_email=f"u{openemr_provider_id}@example.com",
        zoom_user_name=f"User {openemr_provider_id}",
        zoom_user_type=2,
        openemr_facility_id=openemr_facility_id,
        openemr_facility_name="Zoomly Medical Center - MA" if openemr_facility_id else None,
        is_active=True,
    )
    db.session.add(mapping)
    db.session.commit()
    return mapping


def _patch_all_dependencies(monkeypatch, *,
                            specialty_categories,
                            patients,
                            existing_appts=None,
                            category_id_map=None,
                            generated_eids=None,
                            meeting_result=None):
    """
    Patch every external dependency hydrate.py touches. Returns the captured
    calls dict so tests can introspect what was invoked.
    """
    if existing_appts is None:
        existing_appts = []
    if category_id_map is None:
        category_id_map = {
            "Zoom Behavioral Health": 20,
            "Zoom Chronic Care": 21,
            "Zoom New Patient": 22,
            "Zoom Preventive": 23,
            "Zoom MAT (Suboxone)": 24,
        }
    if generated_eids is None:
        generated_eids = iter([1001, 1002, 1003, 1004])
    if meeting_result is None:
        meeting_result = {
            "account_id": "acct-hydrate",
            "zoom_meeting_id": "z-meeting-id",
            "zoom_join_url": "https://zoom.example/join/z-meeting-id",
            "zoom_start_url": "https://zoom.example/start/z-meeting-id",
        }

    captured = {
        "generate_calls": [],
        "create_meeting_calls": [],
    }

    monkeypatch.setattr(
        "app.services.hydrate.get_provider_specialty_categories",
        lambda provider_id: list(specialty_categories),
    )
    monkeypatch.setattr(
        "app.services.hydrate.get_provider_patients",
        lambda provider_id: list(patients),
    )
    monkeypatch.setattr(
        "app.services.hydrate.get_provider_appointments_in_window",
        lambda provider_id, start, end: list(existing_appts),
    )
    monkeypatch.setattr(
        "app.services.hydrate._load_category_id_map",
        lambda: dict(category_id_map),
    )

    def fake_generate(**kwargs):
        captured["generate_calls"].append(kwargs)
        return next(generated_eids)

    def fake_create_meeting(match, payload):
        captured["create_meeting_calls"].append({"match": match, "payload": dict(payload)})
        return dict(meeting_result)

    monkeypatch.setattr("app.services.hydrate.generate_future_appointment", fake_generate)
    monkeypatch.setattr("app.services.hydrate.create_meeting_for_appointment", fake_create_meeting)

    return captured


# --- helpers ----------------------------------------------------------------

def _three_patients():
    return [
        {"pid": 100, "fname": "James",  "lname": "Harrison", "dob": "1978-03-14", "sex": "Male"},
        {"pid": 108, "fname": "Thomas", "lname": "Walsh",    "dob": "1969-08-19", "sex": "Male"},
        {"pid": 112, "fname": "Omar",   "lname": "Hassan",   "dob": "1975-03-29", "sex": "Male"},
    ]


# --- tests ------------------------------------------------------------------

def test_hydrate_all_missing_creates_four_appointments_and_meetings(app, monkeypatch):
    """Provider has zero appts in the window → 4 created + 4 meetings minted."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")

        captured = _patch_all_dependencies(
            monkeypatch,
            specialty_categories=["Zoom Chronic Care", "Zoom New Patient", "Zoom Preventive"],
            patients=_three_patients(),
        )

        summary = hydrate_service.hydrate_future_meetings(account)

    assert summary["providers_processed"] == 1
    assert summary["providers_skipped"] == []
    assert summary["appointments_created"] == 4
    assert summary["meetings_created"] == 4
    assert summary["meetings_backfilled"] == 0
    assert summary["errors"] == []
    assert len(captured["generate_calls"]) == 4
    assert len(captured["create_meeting_calls"]) == 4

    # Patient round-robin: slot[0..2] → patients[0..2], slot[3] wraps to patients[0]
    pids = [call["patient_pid"] for call in captured["generate_calls"]]
    assert pids == [100, 108, 112, 100]

    # Category round-robin: cycles through PC categories
    category_names = [call["category_name"] for call in captured["generate_calls"]]
    assert category_names == [
        "Zoom Chronic Care", "Zoom New Patient", "Zoom Preventive", "Zoom Chronic Care"
    ]

    # create_meeting payload carries all the fields create_zoom_meeting needs —
    # without these, create_zoom_meeting raises ValueError("Missing appointment_date...")
    for call in captured["create_meeting_calls"]:
        p = call["payload"]
        assert "appointment_date" in p, "appointment_date required by create_zoom_meeting"
        assert "appointment_time" in p, "appointment_time required by create_zoom_meeting"
        assert "title" in p
        assert "duration_minutes" in p
        # Date format is YYYY-MM-DD; time format is HH:MM (Zoom service parses both)
        assert len(p["appointment_date"]) == 10
        assert p["appointment_time"].count(":") == 1


def test_hydrate_all_present_noop(app, monkeypatch):
    """Provider already has 4 appts with MeetingRecords → no work done."""
    with app.app_context():
        account = _create_account()
        mapping = _create_mapping(account.account_id, openemr_provider_id="10")

        # Compute the same slot grid the orchestrator will compute
        slot_dates = hydrate_service._next_two_weekdays(date.today())
        existing_appts = []
        for d in slot_dates:
            for t in [time(9, 0), time(14, 0)]:
                eid_str = f"{d.isoformat()}-{t.isoformat()}"
                existing_appts.append({
                    "pc_eid": eid_str, "pc_pid": 100, "pc_aid": 10,
                    "pc_eventDate": d, "pc_startTime": t,
                    "pc_duration": 1800, "pc_catid": 21,
                    "pc_apptstatus": "-", "pc_website": "https://zoom.example/join/x",
                    "pc_title": "Telehealth", "pc_hometext": "",
                })
                # Seed MeetingRecord for each
                db.session.add(MeetingRecord(
                    zoom_account_id=account.account_id,
                    zoom_meeting_id=f"zm-{eid_str}",
                    openemr_appointment_id=str(eid_str),
                    openemr_provider_id="10",
                    status="created",
                ))
        db.session.commit()

        captured = _patch_all_dependencies(
            monkeypatch,
            specialty_categories=["Zoom Chronic Care", "Zoom New Patient", "Zoom Preventive"],
            patients=_three_patients(),
            existing_appts=existing_appts,
        )

        summary = hydrate_service.hydrate_future_meetings(account)

    assert summary["providers_processed"] == 1
    assert summary["appointments_created"] == 0
    assert summary["meetings_created"] == 0
    assert summary["meetings_backfilled"] == 0
    assert captured["generate_calls"] == []
    assert captured["create_meeting_calls"] == []


def test_hydrate_backfill_when_appt_exists_without_meeting(app, monkeypatch):
    """Appointment is present at slot[0] but no MeetingRecord → backfill the meeting only."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")

        slot_dates = hydrate_service._next_two_weekdays(date.today())
        existing_appts = [{
            "pc_eid": 5555, "pc_pid": 100, "pc_aid": 10,
            "pc_eventDate": slot_dates[0], "pc_startTime": time(9, 0),
            "pc_duration": 1800, "pc_catid": 21,
            "pc_apptstatus": "-", "pc_website": None,
            "pc_title": "Existing telehealth slot",
            "pc_hometext": "Follow-up",
        }]

        captured = _patch_all_dependencies(
            monkeypatch,
            specialty_categories=["Zoom Chronic Care", "Zoom New Patient", "Zoom Preventive"],
            patients=_three_patients(),
            existing_appts=existing_appts,
        )

        summary = hydrate_service.hydrate_future_meetings(account)

    assert summary["appointments_created"] == 3   # the other 3 slots got new appts
    assert summary["meetings_created"] == 3
    assert summary["meetings_backfilled"] == 1
    # backfill carries the existing eid (5555), patient 100, status "-", plus
    # the existing pc_title and the slot's date/time
    backfill_payloads = [c["payload"] for c in captured["create_meeting_calls"] if c["payload"]["eid"] == 5555]
    assert len(backfill_payloads) == 1
    bp = backfill_payloads[0]
    assert bp["pid"] == 100
    assert bp["title"] == "Existing telehealth slot"
    assert bp["appointment_time"] == "09:00"
    assert bp["duration_minutes"] == 30  # 1800 sec // 60


def test_hydrate_skips_provider_with_unknown_specialty(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")

        captured = _patch_all_dependencies(
            monkeypatch,
            specialty_categories=[],  # provider not in SPECIALTY_TO_CATEGORIES
            patients=_three_patients(),
        )

        summary = hydrate_service.hydrate_future_meetings(account)

    assert summary["providers_processed"] == 0
    assert len(summary["providers_skipped"]) == 1
    assert summary["providers_skipped"][0]["reason"] == "unknown_specialty"
    assert captured["generate_calls"] == []


def test_hydrate_skips_provider_with_no_patients(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")

        captured = _patch_all_dependencies(
            monkeypatch,
            specialty_categories=["Zoom Chronic Care"],
            patients=[],
        )

        summary = hydrate_service.hydrate_future_meetings(account)

    assert summary["providers_skipped"][0]["reason"] == "no_patients"
    assert captured["generate_calls"] == []


def test_hydrate_respects_account_appointment_type_filter(app, monkeypatch):
    """Account filter excludes the BH provider's only category → provider skipped."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="12")

        # SE has filtered to PC-only categories — BH provider has no match
        db.session.add(AppointmentTypeFilter(
            zoom_account_id=account.account_id, openemr_type_id="21",  # Zoom Chronic Care
            openemr_type_name="Zoom Chronic Care",
        ))
        db.session.commit()

        captured = _patch_all_dependencies(
            monkeypatch,
            specialty_categories=["Zoom Behavioral Health"],  # cat_id=20 — not in filter
            patients=_three_patients(),
        )

        summary = hydrate_service.hydrate_future_meetings(account)

    assert summary["providers_skipped"][0]["reason"] == "no_matching_categories"
    assert captured["generate_calls"] == []


def test_hydrate_emits_started_and_completed_audits(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        _patch_all_dependencies(
            monkeypatch,
            specialty_categories=["Zoom Chronic Care", "Zoom New Patient", "Zoom Preventive"],
            patients=_three_patients(),
        )

        hydrate_service.hydrate_future_meetings(account)

        started = AuditLog.query.filter_by(event_type="demo.hydrate_started").all()
        completed = AuditLog.query.filter_by(event_type="demo.hydrate_completed").all()
        meeting_created = AuditLog.query.filter_by(event_type="demo.future_meeting_created").all()

    assert len(started) == 1
    assert len(completed) == 1
    assert started[0].zoom_account_id == "acct-hydrate"
    completed_detail = json.loads(completed[0].detail)
    assert completed_detail["providers_processed"] == 1
    assert completed_detail["meetings_created"] == 4
    assert len(meeting_created) == 4


def test_hydrate_records_error_when_meeting_creation_fails(app, monkeypatch):
    """create_meeting_for_appointment returns {"error": ...} → counted in summary."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        _patch_all_dependencies(
            monkeypatch,
            specialty_categories=["Zoom Chronic Care"],
            patients=_three_patients()[:1],
            meeting_result={"error": "Zoom API down"},
        )

        summary = hydrate_service.hydrate_future_meetings(account)

    assert summary["appointments_created"] == 4
    assert summary["meetings_created"] == 0
    assert len(summary["errors"]) == 4
    assert all(err["stage"] == "create_meeting" for err in summary["errors"])
    assert all(err["error"] == "Zoom API down" for err in summary["errors"])


# --- pure-function helpers --------------------------------------------------

def test_next_two_weekdays_skips_weekend():
    # Friday → Mon, Tue
    fri = date(2026, 5, 22)  # 2026-05-22 is a Friday
    assert fri.weekday() == 4
    out = hydrate_service._next_two_weekdays(fri)
    assert out == [date(2026, 5, 25), date(2026, 5, 26)]  # Mon, Tue

    # Saturday → Mon, Tue
    sat = date(2026, 5, 23)
    out = hydrate_service._next_two_weekdays(sat)
    assert out == [date(2026, 5, 25), date(2026, 5, 26)]

    # Wednesday → Thu, Fri
    wed = date(2026, 5, 20)
    out = hydrate_service._next_two_weekdays(wed)
    assert out == [date(2026, 5, 21), date(2026, 5, 22)]


def test_find_existing_appt_for_slot_matches_exactly():
    appts = [
        {"pc_eid": 1, "pc_eventDate": date(2026, 5, 22), "pc_startTime": time(9, 0)},
        {"pc_eid": 2, "pc_eventDate": date(2026, 5, 22), "pc_startTime": time(14, 0)},
    ]
    assert hydrate_service._find_existing_appt_for_slot(appts, date(2026, 5, 22), time(9, 0))["pc_eid"] == 1
    assert hydrate_service._find_existing_appt_for_slot(appts, date(2026, 5, 22), time(10, 0)) is None
