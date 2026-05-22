"""Tests for the Sprint 13 past locked-encounter seeder (S13-05)."""

import json
from datetime import date, time
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import (
    AccountConfig,
    AuditLog,
    ProviderMapping,
    ZoomAccount,
)
from app.services.openemr.encounter import past_encounter


# --- fixtures ---------------------------------------------------------------

def _create_account(account_id: str = "acct-past") -> ZoomAccount:
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


def _create_mapping(account_id: str, *, openemr_provider_id: str = "10") -> ProviderMapping:
    mapping = ProviderMapping(
        zoom_account_id=account_id,
        openemr_fhir_id=f"fhir-{openemr_provider_id}",
        openemr_provider_npi=f"npi-{openemr_provider_id}",
        openemr_provider_id=openemr_provider_id,
        openemr_provider_name=f"Dr {openemr_provider_id}",
        zoom_user_id=f"user-{openemr_provider_id}",
        zoom_user_email=f"u{openemr_provider_id}@example.com",
        zoom_user_name=f"User {openemr_provider_id}",
        zoom_user_type=2,
        openemr_facility_id=2,
        is_active=True,
    )
    db.session.add(mapping)
    db.session.commit()
    return mapping


def _patch_happy_path(monkeypatch, *,
                      specialty_categories=None,
                      patients=None,
                      existing_8am_appt=None,
                      seed_marker_present=False,
                      category_id=20,
                      generate_eid=5001,
                      encounter_number=900001,
                      write_note_ok=True,
                      list_id=777):
    """
    Patch every external dependency past_encounter touches. Returns the
    captured-calls dict so tests can introspect what was invoked.
    """
    if specialty_categories is None:
        specialty_categories = ["Zoom Chronic Care"]
    if patients is None:
        patients = [{"pid": 100, "fname": "James", "lname": "Harrison", "dob": "1978-03-14", "sex": "Male"}]

    captured = {
        "generate_appointment": [],
        "update_status": [],
        "create_encounter": [],
        "write_note": [],
        "find_or_create_problem": [],
        "link_issue": [],
        "billing": [],
        "esign": [],
        "attach_care_plan": [],
        "attach_clinical_instructions": [],
        "esign_all_forms": [],
    }

    monkeypatch.setattr(
        "app.services.openemr.encounter.past_encounter._seed_marker_exists_today",
        lambda: seed_marker_present,
    )
    monkeypatch.setattr(
        "app.services.openemr.encounter.past_encounter.get_provider_specialty_categories",
        lambda pid: list(specialty_categories),
    )
    monkeypatch.setattr(
        "app.services.openemr.encounter.past_encounter.get_provider_patients",
        lambda pid: list(patients),
    )
    monkeypatch.setattr(
        "app.services.openemr.encounter.past_encounter._lookup_provider_facility",
        lambda pid: 2,
    )
    monkeypatch.setattr(
        "app.services.openemr.encounter.past_encounter._lookup_category_id",
        lambda name: category_id,
    )
    monkeypatch.setattr(
        "app.services.openemr.encounter.past_encounter.get_provider_appointments_in_window",
        lambda pid, start, end: [existing_8am_appt] if existing_8am_appt else [],
    )
    # By default tests run as if NO demo patient exists, so the orchestrator
    # falls through to get_provider_patients[0]. Tests that want to exercise
    # the demo-patient path patch _find_demo_patient_for_provider separately.
    monkeypatch.setattr(
        "app.services.openemr.encounter.past_encounter._find_demo_patient_for_provider",
        lambda pid: None,
    )

    def fake_generate(**kwargs):
        captured["generate_appointment"].append(kwargs)
        return generate_eid

    def fake_update_status(eid, status):
        captured["update_status"].append({"eid": eid, "status": status})
        return True

    def fake_create_encounter(**kwargs):
        captured["create_encounter"].append(kwargs)
        return encounter_number

    def fake_write_note(**kwargs):
        captured["write_note"].append(kwargs)
        return write_note_ok

    def fake_find_or_create_problems(pid):
        captured["find_or_create_problem"].append(pid)
        # Return one list_id per demo problem (mirrors plural return shape)
        return [list_id, list_id + 1, list_id + 2, list_id + 3, list_id + 4]

    def fake_link_issue(pid, list_id_arg, encounter):
        captured["link_issue"].append({"pid": pid, "list_id": list_id_arg, "encounter": encounter})

    def fake_billing_rows(pid, encounter, provider_id):
        captured["billing"].append({"pid": pid, "encounter": encounter, "provider_id": provider_id})

    def fake_esign(encounter, uid):
        captured["esign"].append({"encounter": encounter, "uid": uid})

    def fake_attach_care_plan(**kwargs):
        captured["attach_care_plan"].append(kwargs)

    def fake_attach_clinical_instructions(**kwargs):
        captured["attach_clinical_instructions"].append(kwargs)

    def fake_esign_all_forms(encounter, uid):
        captured["esign_all_forms"].append({"encounter": encounter, "uid": uid})

    monkeypatch.setattr("app.services.openemr.encounter.past_encounter.generate_future_appointment", fake_generate)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter.update_appointment_status", fake_update_status)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._create_locked_demo_encounter", fake_create_encounter)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter.write_note_to_encounter", fake_write_note)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter.get_provider_username", lambda pid: f"user{pid}")
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._find_or_create_demo_problems", fake_find_or_create_problems)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._link_issue_to_encounter", fake_link_issue)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._insert_billing_rows", fake_billing_rows)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._esign_encounter", fake_esign)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._attach_care_plan_form", fake_attach_care_plan)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._attach_clinical_instructions_form", fake_attach_clinical_instructions)
    monkeypatch.setattr("app.services.openemr.encounter.past_encounter._esign_all_attached_forms", fake_esign_all_forms)

    return captured


# --- happy path -------------------------------------------------------------

def test_seed_creates_encounter_when_8am_is_free(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        captured = _patch_happy_path(monkeypatch)

        summary = past_encounter.seed_past_locked_encounters(account)

    assert summary["past_encounters_created"] == 1
    assert summary["past_encounters_skipped_today"] is False
    assert summary["past_encounter_skips"] == []
    assert summary["past_encounter_errors"] == []

    # Verifies the full pipeline ran in order
    assert len(captured["generate_appointment"]) == 1
    assert captured["generate_appointment"][0]["slot_time"] == time(8, 0)
    assert captured["generate_appointment"][0]["status"] == ">"  # checked out
    assert len(captured["create_encounter"]) == 1
    assert len(captured["write_note"]) == 1
    assert captured["write_note"][0]["note_writeback_mode"] == "both"
    # 5 ICDs in DEMO_ICD_PROBLEMS → 5 issue_encounter linkages
    assert len(captured["link_issue"]) == 5
    assert captured["link_issue"][0]["list_id"] == 777
    assert captured["link_issue"][-1]["list_id"] == 781  # 777 + 4
    # _insert_billing_rows is called once (inserts multiple internally)
    assert len(captured["billing"]) == 1
    assert len(captured["esign"]) == 1
    assert captured["esign"][0]["encounter"] == 900001

    # New: supplementary forms each attached once + per-form esign batch fired
    assert len(captured["attach_care_plan"]) == 1
    assert len(captured["attach_clinical_instructions"]) == 1
    assert captured["attach_care_plan"][0]["encounter"] == 900001
    assert captured["attach_care_plan"][0]["pid"] == 100
    assert len(captured["esign_all_forms"]) == 1
    assert captured["esign_all_forms"][0]["encounter"] == 900001


def test_seed_prefers_demo_patient_over_provider_patients(app, monkeypatch):
    """When the demo seed has run, _find_demo_patient_for_provider returns
    the dedicated diabetes target; the orchestrator should use it instead of
    falling through to get_provider_patients()[0]."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        captured = _patch_happy_path(monkeypatch)

        # Override the default (None) with an explicit demo patient
        monkeypatch.setattr(
            "app.services.openemr.encounter.past_encounter._find_demo_patient_for_provider",
            lambda pid: {"pid": 151, "fname": "Sarah", "lname": "Chen", "dob": "1972-04-15", "sex": "Female"},
        )

        past_encounter.seed_past_locked_encounters(account)

    # Demo patient pid=151 wins, not the get_provider_patients() pid=100
    assert captured["generate_appointment"][0]["patient_pid"] == 151
    assert captured["link_issue"][0]["pid"] == 151
    assert captured["billing"][0]["pid"] == 151


def test_seed_uses_existing_pending_8am_appointment(app, monkeypatch):
    """Existing 8am appt in '-' Pending state → flip to Checked Out + use it."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        existing = {
            "pc_eid": 999, "pc_pid": 100, "pc_aid": 10,
            "pc_eventDate": date.today(), "pc_startTime": time(8, 0),
            "pc_duration": 1800, "pc_catid": 20,
            "pc_apptstatus": "-",  # Pending
            "pc_website": None, "pc_title": "", "pc_hometext": "",
        }
        captured = _patch_happy_path(monkeypatch, existing_8am_appt=existing)

        summary = past_encounter.seed_past_locked_encounters(account)

    assert summary["past_encounters_created"] == 1
    assert captured["generate_appointment"] == []  # no new appt
    assert captured["update_status"] == [{"eid": 999, "status": ">"}]
    assert captured["create_encounter"][0]["eid"] == 999


def test_seed_skips_when_8am_is_already_checked_out(app, monkeypatch):
    """Existing 8am appt already past the Pending phase → skip with reason."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        existing = {
            "pc_eid": 999, "pc_pid": 100, "pc_aid": 10,
            "pc_eventDate": date.today(), "pc_startTime": time(8, 0),
            "pc_duration": 1800, "pc_catid": 20,
            "pc_apptstatus": ">",  # Checked Out
            "pc_website": None, "pc_title": "", "pc_hometext": "",
        }
        captured = _patch_happy_path(monkeypatch, existing_8am_appt=existing)

        summary = past_encounter.seed_past_locked_encounters(account)

    assert summary["past_encounters_created"] == 0
    assert summary["past_encounter_skips"] == [
        {"openemr_provider_id": "10", "reason": "8am_slot_occupied"}
    ]
    assert captured["create_encounter"] == []


def test_global_per_day_guard_skips_everything(app, monkeypatch):
    """If any seed-marker encounter already exists today → entire pass skipped."""
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        _create_mapping(account.account_id, openemr_provider_id="11")
        captured = _patch_happy_path(monkeypatch, seed_marker_present=True)

        summary = past_encounter.seed_past_locked_encounters(account)

        assert summary["past_encounters_skipped_today"] is True
        assert summary["past_encounters_created"] == 0
        # Guard fired before any per-provider work
        assert captured["generate_appointment"] == []
        assert captured["create_encounter"] == []

        audits = AuditLog.query.filter_by(event_type="demo.past_encounters_skipped_today").all()
        assert len(audits) == 1


def test_seed_skips_provider_with_unknown_specialty(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        captured = _patch_happy_path(monkeypatch, specialty_categories=[])

        summary = past_encounter.seed_past_locked_encounters(account)

    assert summary["past_encounter_skips"] == [
        {"openemr_provider_id": "10", "reason": "unknown_specialty"}
    ]
    assert captured["create_encounter"] == []


def test_seed_skips_provider_with_no_patients(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        captured = _patch_happy_path(monkeypatch, patients=[])

        summary = past_encounter.seed_past_locked_encounters(account)

    assert summary["past_encounter_skips"] == [
        {"openemr_provider_id": "10", "reason": "no_patients"}
    ]
    assert captured["create_encounter"] == []


def test_seed_honors_soap_only_writeback_mode(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        account.config.note_writeback_mode = "soap_only"
        db.session.commit()
        _create_mapping(account.account_id, openemr_provider_id="10")
        captured = _patch_happy_path(monkeypatch)

        past_encounter.seed_past_locked_encounters(account)

    # write_note_to_encounter receives the mode — it does the form-mode branching
    assert captured["write_note"][0]["note_writeback_mode"] == "soap_only"


def test_seed_records_error_when_write_note_fails(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        captured = _patch_happy_path(monkeypatch, write_note_ok=False)

        summary = past_encounter.seed_past_locked_encounters(account)

    assert summary["past_encounters_created"] == 0
    assert len(summary["past_encounter_errors"]) == 1
    assert summary["past_encounter_errors"][0]["stage"] == "write_note"
    # E-sign should NOT have fired since write_note failed.
    # Same goes for the supplementary forms — they hang off a successful note.
    assert captured["esign"] == []
    assert captured["esign_all_forms"] == []
    assert captured["attach_care_plan"] == []
    assert captured["attach_clinical_instructions"] == []


def test_seed_emits_per_encounter_audit_with_context(app, monkeypatch):
    with app.app_context():
        account = _create_account()
        _create_mapping(account.account_id, openemr_provider_id="10")
        _patch_happy_path(monkeypatch)

        past_encounter.seed_past_locked_encounters(account)

        audits = AuditLog.query.filter_by(event_type="demo.past_encounter_seeded").all()
        assert len(audits) == 1
        row = audits[0]
        assert row.zoom_account_id == "acct-past"
        assert row.openemr_provider_id == "10"
        assert row.openemr_patient_id == "100"
        assert row.openemr_encounter_number == "900001"
        assert json.loads(row.detail)["category_name"] == "Zoom Chronic Care"


def test_get_note_for_category_returns_placeholder_for_now():
    from app.services.openemr.encounter.sample_notes import (
        get_care_plan_for_category,
        get_clinical_instructions_for_category,
        get_note_for_category,
        PAST_ENCOUNTER_NOTE,
        PAST_ENCOUNTER_CARE_PLAN,
        PAST_ENCOUNTER_CLINICAL_INSTRUCTIONS,
    )
    # All categories currently return the same body
    assert get_note_for_category("Zoom Behavioral Health") == PAST_ENCOUNTER_NOTE
    assert get_note_for_category("Zoom Chronic Care") == PAST_ENCOUNTER_NOTE
    assert get_note_for_category("Zoom MAT (Suboxone)") == PAST_ENCOUNTER_NOTE
    # Care plan + clinical instructions get patient_name / date / provider_name
    # substituted, so equality against the raw template isn't useful — instead
    # confirm the substitution actually fires.
    rendered_care_plan = get_care_plan_for_category(
        "Zoom Chronic Care", patient_name="Test Patient", date="May 22, 2026", provider_name="Dr. Test"
    )
    assert "Test Patient" in rendered_care_plan
    assert "May 22, 2026" in rendered_care_plan
    assert "Dr. Test" in rendered_care_plan
    rendered_ci = get_clinical_instructions_for_category(
        "Zoom Chronic Care", patient_name="Test Patient", date="May 22, 2026", provider_name="Dr. Test"
    )
    assert "Test Patient" in rendered_ci
    # SOAP body hits the standard headers so parse_soap_sections recognizes it
    assert "Chief Complaint" in PAST_ENCOUNTER_NOTE
    assert "Assessment" in PAST_ENCOUNTER_NOTE
    assert "Plan" in PAST_ENCOUNTER_NOTE
    # Template placeholders intact (so format() substitution works)
    assert "{patient_name}" in PAST_ENCOUNTER_CARE_PLAN
    assert "{patient_name}" in PAST_ENCOUNTER_CLINICAL_INSTRUCTIONS
