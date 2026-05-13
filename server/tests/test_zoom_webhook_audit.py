from app.extensions import db
from app.models import AccountConfig, MeetingPatient, MeetingRecord, ZoomAccount


def _create_account(account_id: str) -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id=f"client-{account_id}",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id=f"openemr-{account_id}",
        private_key_path=f"/tmp/{account_id}/private.pem",
        kid=f"zoomly-{account_id}",
        is_active=True,
    )
    db.session.add(account)
    db.session.commit()
    return account


def _create_meeting(
    account: ZoomAccount,
    *,
    meeting_id: str,
    appointment_id: str = "999",
    provider_id: str = "10",
    patient_id: str | None = "1",
) -> MeetingRecord:
    record = MeetingRecord(
        zoom_account_id=account.account_id,
        zoom_meeting_id=meeting_id,
        zoom_start_url=f"https://zoom.example/start/{meeting_id}",
        zoom_join_url=f"https://zoom.example/join/{meeting_id}",
        openemr_appointment_id=appointment_id,
        openemr_provider_id=provider_id,
        status="created",
    )
    db.session.add(record)
    if patient_id is not None:
        db.session.add(
            MeetingPatient(
                zoom_meeting_id=meeting_id,
                openemr_patient_id=patient_id,
            )
        )
    db.session.commit()
    return record


def test_note_processing_audits_missing_patient_context(app, monkeypatch):
    with app.app_context():
        account = _create_account("acct-context-missing")
        _create_meeting(account, meeting_id="meet-context-missing", patient_id=None)
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            lambda account, note_id: {
                "note_title": "Zoom Clinical Note",
                "note_content": "Assessment\nStable",
            },
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _validate_and_process_note

        body, status = _validate_and_process_note(
            account=account,
            meeting_number="meet-context-missing",
            note_id="note-context-missing",
            note_title="Zoom Clinical Note",
        )

    assert status == 500
    assert body == {"status": "error", "reason": "missing patient or provider"}
    audit_call = next(call for call in calls if call["event_type"] == "note.context_missing")
    assert audit_call["success"] is False
    assert audit_call["zoom_account_id"] == "acct-context-missing"
    assert audit_call["zoom_meeting_id"] == "meet-context-missing"
    assert audit_call["zoom_note_id"] == "note-context-missing"
    assert audit_call["openemr_appointment_id"] == "999"
    assert audit_call["openemr_provider_id"] == "10"
    assert audit_call["openemr_patient_id"] is None
    assert audit_call["error_message"] == "missing patient or provider"
    assert audit_call["detail"] == {"ehr_context": False}


def test_note_processing_audits_write_failure_with_context(app, monkeypatch):
    with app.app_context():
        account = _create_account("acct-note-write")
        _create_meeting(account, meeting_id="meet-note-write")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            lambda account, note_id: {
                "note_title": "Zoom Clinical Note",
                "note_content": "Plan\nFollow up",
            },
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.find_encounter_for_appointment",
            lambda eid, pid, provider_id: (None, None),
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_appointment_details",
            lambda eid: {"facility_id": 1, "pc_catid": 27},
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.create_encounter",
            lambda **kwargs: 555001,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_provider_username",
            lambda provider_id: "provider-user",
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_note_to_encounter",
            lambda **kwargs: False,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _validate_and_process_note

        body, status = _validate_and_process_note(
            account=account,
            meeting_number="meet-note-write",
            note_id="note-write-failed",
            note_title="Zoom Clinical Note",
        )

    assert status == 500
    assert body == {
        "status": "write_failed",
        "encounter": 555001,
        "zoom_meeting_id": "meet-note-write",
    }
    retrieved_call = next(call for call in calls if call["event_type"] == "note.retrieved")
    assert retrieved_call["openemr_provider_id"] == "10"
    assert retrieved_call["openemr_patient_id"] == "1"
    write_call = next(call for call in calls if call["event_type"] == "note.write_failed")
    assert write_call["success"] is False
    assert write_call["openemr_appointment_id"] == "999"
    assert write_call["openemr_encounter_number"] == "555001"
    assert write_call["openemr_provider_id"] == "10"
    assert write_call["openemr_patient_id"] == "1"
    assert write_call["error_message"] == "OpenEMR note write failed"
    assert write_call["detail"] == {"ehr_context": False, "content_blank": False}


def test_note_processing_audits_encounter_failure_with_context(app, monkeypatch):
    with app.app_context():
        account = _create_account("acct-encounter-fail")
        _create_meeting(account, meeting_id="meet-encounter-fail")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            lambda account, note_id: {
                "note_title": "Zoom Clinical Note",
                "note_content": "Subjective\nDoing well",
            },
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.find_encounter_for_appointment",
            lambda eid, pid, provider_id: (None, None),
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_appointment_details",
            lambda eid: None,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _validate_and_process_note

        body, status = _validate_and_process_note(
            account=account,
            meeting_number="meet-encounter-fail",
            note_id="note-encounter-fail",
            note_title="Zoom Clinical Note",
        )

    assert status == 500
    assert body == {"status": "error", "reason": "could not find or create encounter"}
    audit_call = next(call for call in calls if call["event_type"] == "note.encounter_failed")
    assert audit_call["success"] is False
    assert audit_call["openemr_appointment_id"] == "999"
    assert audit_call["openemr_provider_id"] == "10"
    assert audit_call["openemr_patient_id"] == "1"
    assert audit_call["error_message"] == "could not find or create encounter"


def test_note_processing_uses_account_writeback_mode(app, monkeypatch):
    with app.app_context():
        account = _create_account("acct-note-mode")
        db.session.add(
            AccountConfig(
                account_id=account.account_id,
                timezone="America/Denver",
                note_writeback_mode="clinical_note_only",
            )
        )
        db.session.commit()
        _create_meeting(account, meeting_id="meet-note-mode")
        calls = []
        captured = {}

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            lambda account, note_id: {
                "note_title": "Zoom Clinical Note",
                "note_content": "Plan\nFollow up",
            },
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.find_encounter_for_appointment",
            lambda eid, pid, provider_id: (None, None),
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_appointment_details",
            lambda eid: {"facility_id": 1, "pc_catid": 27},
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.create_encounter",
            lambda **kwargs: 555101,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_provider_username",
            lambda provider_id: "provider-user",
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_note_to_encounter",
            lambda **kwargs: captured.update(kwargs) or True,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _validate_and_process_note

        body, status = _validate_and_process_note(
            account=account,
            meeting_number="meet-note-mode",
            note_id="note-mode",
            note_title="Zoom Clinical Note",
        )

    assert status == 200
    assert body == {
        "status": "written",
        "encounter": 555101,
        "zoom_meeting_id": "meet-note-mode",
    }
    assert captured["note_writeback_mode"] == "clinical_note_only"
    assert captured["provider_username"] == "provider-user"
    assert any(call["event_type"] == "note.written" for call in calls)


def test_waiting_room_arrival_audits_status_update_failure_with_context(app, monkeypatch):
    with app.app_context():
        account = _create_account("acct-waiting-room")
        _create_meeting(account, meeting_id="meet-waiting-room")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.update_appointment_status",
            lambda eid, status: False,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_appointment_details",
            lambda eid: None,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _handle_waiting_room_joined

        body, status = _handle_waiting_room_joined(
            {
                "event": "meeting.participant_joined_waiting_room",
                "payload": {
                    "object": {
                        "id": "meet-waiting-room",
                        "participant": {"user_name": "Patient One"},
                    }
                },
            },
            account,
        )

    assert status == 200
    assert body == {"status": "ok", "eid": "999"}
    audit_call = next(call for call in calls if call["event_type"] == "appointment.patient_arrived")
    assert audit_call["success"] is False
    assert audit_call["zoom_account_id"] == "acct-waiting-room"
    assert audit_call["openemr_appointment_id"] == "999"
    assert audit_call["openemr_provider_id"] == "10"
    assert audit_call["openemr_patient_id"] == "1"
    assert audit_call["zoom_meeting_id"] == "meet-waiting-room"
    assert audit_call["error_message"] == "OpenEMR appointment status update failed"
    assert audit_call["detail"] == {
        "participant": "Patient One",
        "trigger": "meeting.participant_joined_waiting_room",
    }


# ---------------------------------------------------------------------------
# _fetch_note_with_retry — retry-success audit (G-N2)
# ---------------------------------------------------------------------------

def test_fetch_note_with_retry_audits_when_succeeds_after_empty(app, monkeypatch):
    """G-N2: when content arrives non-empty on attempt > 1, write note.fetched_after_retry."""
    with app.app_context():
        account = _create_account("acct-retry-saves")
        calls = []

        responses = [
            {"note_content": ""},
            {"note_content": "Plan\nFollow up"},
        ]

        def fake_get(_account, _note_id):
            return responses.pop(0)

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            fake_get,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.time.sleep",
            lambda _seconds: None,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _fetch_note_with_retry

        result = _fetch_note_with_retry(
            account=account,
            note_id="note-retry-saves",
            max_attempts=3,
            delay_seconds=0,
        )

    assert result == {"note_content": "Plan\nFollow up"}
    retry_audit = next(c for c in calls if c["event_type"] == "note.fetched_after_retry")
    assert retry_audit["success"] is True
    assert retry_audit["zoom_account_id"] == "acct-retry-saves"
    assert retry_audit["zoom_note_id"] == "note-retry-saves"
    assert retry_audit["detail"] == {"attempts": 2, "max_attempts": 3}


def test_fetch_note_with_retry_does_not_audit_when_succeeds_first_attempt(app, monkeypatch):
    """G-N2 negative: no note.fetched_after_retry row when attempt 1 already returns content."""
    with app.app_context():
        account = _create_account("acct-retry-first")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            lambda _account, _note_id: {"note_content": "Plan\nFollow up"},
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.time.sleep",
            lambda _seconds: None,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _fetch_note_with_retry

        result = _fetch_note_with_retry(
            account=account,
            note_id="note-retry-first",
            max_attempts=3,
            delay_seconds=0,
        )

    assert result == {"note_content": "Plan\nFollow up"}
    assert not any(c["event_type"] == "note.fetched_after_retry" for c in calls)


# ---------------------------------------------------------------------------
# PR 4 — P2 cleanup tests
# ---------------------------------------------------------------------------

def test_waiting_room_audits_encounter_create_failed(app, monkeypatch):
    """G-A3: create_encounter returns None during waiting-room → encounter.create_failed audit."""
    with app.app_context():
        account = _create_account("acct-encounter-create-fail")
        _create_meeting(account, meeting_id="meet-encounter-create-fail")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.update_appointment_status",
            lambda eid, status: True,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_appointment_details",
            lambda eid: {"pid": 1, "provider_id": 10, "facility_id": 1, "pc_catid": 27},
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.create_encounter",
            lambda **kwargs: None,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        payload = {
            "event": "meeting.participant_joined_waiting_room",
            "payload": {"object": {
                "id": "meet-encounter-create-fail",
                "participant": {"user_name": "Patient X"},
            }},
        }

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _handle_waiting_room_joined
        body, status = _handle_waiting_room_joined(payload, account)

    assert status == 200
    encounter_fail = next(c for c in calls if c["event_type"] == "encounter.create_failed")
    assert encounter_fail["success"] is False
    assert encounter_fail["zoom_account_id"] == "acct-encounter-create-fail"
    assert encounter_fail["openemr_appointment_id"] == "999"
    assert encounter_fail["openemr_provider_id"] == "10"
    assert encounter_fail["openemr_patient_id"] == "1"
    assert encounter_fail["zoom_meeting_id"] == "meet-encounter-create-fail"
    assert encounter_fail["error_message"] == "create_encounter returned None"
    assert encounter_fail["detail"] == {"trigger": "waiting_room"}


def test_process_note_async_audits_when_account_inactive(app, monkeypatch):
    """G-N6: async job runs but account is inactive → note.dropped reason=account_inactive."""
    with app.app_context():
        account = _create_account("acct-inactive-async")
        account.is_active = False
        db.session.commit()
        calls = []

        def should_not_run(**_):
            raise AssertionError("should not run when account is inactive")

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers._validate_and_process_note",
            should_not_run,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from flask import current_app
        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _process_note_async

        _process_note_async(
            current_app._get_current_object(),
            account.account_id,
            "note-inactive",
            "meet-inactive",
            "title",
        )

    dropped = next(c for c in calls if c["event_type"] == "note.dropped")
    assert dropped["success"] is False
    assert dropped["zoom_account_id"] == "acct-inactive-async"
    assert dropped["zoom_meeting_id"] == "meet-inactive"
    assert dropped["zoom_note_id"] == "note-inactive"
    assert dropped["detail"] == {"reason": "account_inactive"}


def test_process_note_async_audits_unhandled_exception(app, monkeypatch):
    """G-N5: _validate_and_process_note raises inside async job → note.async_job_error audit."""
    with app.app_context():
        account = _create_account("acct-async-error")
        calls = []

        def boom(**_):
            raise RuntimeError("validation blew up")

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers._validate_and_process_note",
            boom,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from flask import current_app
        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _process_note_async

        _process_note_async(
            current_app._get_current_object(),
            account.account_id,
            "note-async-err",
            "meet-async",
            "title",
        )

    err = next(c for c in calls if c["event_type"] == "note.async_job_error")
    assert err["success"] is False
    assert err["zoom_account_id"] == "acct-async-error"
    assert err["zoom_meeting_id"] == "meet-async"
    assert err["zoom_note_id"] == "note-async-err"
    assert "validation blew up" in err["error_message"]


# ---------------------------------------------------------------------------
# PR 5 — encounter.claimed and encounter.created audits
# ---------------------------------------------------------------------------

def test_note_processing_audits_encounter_claimed_on_manual_fallback(app, monkeypatch):
    """G-N7: find_encounter_for_appointment source=manual_fallback → encounter.claimed audit."""
    with app.app_context():
        account = _create_account("acct-claimed")
        _create_meeting(account, meeting_id="meet-claimed")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            lambda account, note_id: {
                "note_title": "Zoom Clinical Note",
                "note_content": "Plan\nFollow up",
            },
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.find_encounter_for_appointment",
            lambda eid, pid, provider_id: (777001, "manual_fallback"),
        )
        # Stub the redundant external_id re-stamp engine call
        class _StubConn:
            def execute(self, *_args, **_kwargs):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

        class _StubEngine:
            def begin(self):
                return _StubConn()

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_openemr_db_engine",
            lambda: _StubEngine(),
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_provider_username",
            lambda provider_id: "provider-user",
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_note_to_encounter",
            lambda **kwargs: True,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _validate_and_process_note

        body, status = _validate_and_process_note(
            account=account,
            meeting_number="meet-claimed",
            note_id="note-claimed",
            note_title="Zoom Clinical Note",
        )

    assert status == 200
    claimed = next(c for c in calls if c["event_type"] == "encounter.claimed")
    assert claimed["success"] is True
    assert claimed["zoom_account_id"] == "acct-claimed"
    assert claimed["zoom_meeting_id"] == "meet-claimed"
    assert claimed["zoom_note_id"] == "note-claimed"
    assert claimed["openemr_encounter_number"] == "777001"
    assert claimed["detail"] == {"reason": "manual_fallback"}
    # No encounter.created should fire on the claim path
    assert not any(c["event_type"] == "encounter.created" for c in calls)


def test_note_processing_audits_encounter_created_on_new_encounter(app, monkeypatch):
    """G-N8: when find_encounter_for_appointment returns None and create_encounter succeeds,
    write encounter.created audit with trigger=note_processing."""
    with app.app_context():
        account = _create_account("acct-enc-created")
        _create_meeting(account, meeting_id="meet-enc-created")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_zoom_clinical_note",
            lambda account, note_id: {
                "note_title": "Zoom Clinical Note",
                "note_content": "Plan\nFollow up",
            },
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.find_encounter_for_appointment",
            lambda eid, pid, provider_id: (None, None),
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_appointment_details",
            lambda eid: {"facility_id": 1, "pc_catid": 27},
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.create_encounter",
            lambda **kwargs: 777002,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_provider_username",
            lambda provider_id: "provider-user",
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_note_to_encounter",
            lambda **kwargs: True,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _validate_and_process_note

        body, status = _validate_and_process_note(
            account=account,
            meeting_number="meet-enc-created",
            note_id="note-enc-created",
            note_title="Zoom Clinical Note",
        )

    assert status == 200
    created = next(c for c in calls if c["event_type"] == "encounter.created")
    assert created["success"] is True
    assert created["zoom_account_id"] == "acct-enc-created"
    assert created["zoom_meeting_id"] == "meet-enc-created"
    assert created["zoom_note_id"] == "note-enc-created"
    assert created["openemr_encounter_number"] == "777002"
    assert created["detail"] == {"trigger": "note_processing"}


def test_waiting_room_audits_encounter_created_on_success(app, monkeypatch):
    """G-N8 parity: waiting-room handler emits encounter.created on create success."""
    with app.app_context():
        account = _create_account("acct-wr-created")
        _create_meeting(account, meeting_id="meet-wr-created")
        calls = []

        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.update_appointment_status",
            lambda eid, status: True,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.get_appointment_details",
            lambda eid: {"pid": 1, "provider_id": 10, "facility_id": 1, "pc_catid": 27},
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.create_encounter",
            lambda **kwargs: 777003,
        )
        monkeypatch.setattr(
            "app.blueprints.webhooks.zoom.zoom_webhook_helpers.write_audit_log",
            lambda **kwargs: calls.append(kwargs),
        )

        payload = {
            "event": "meeting.participant_joined_waiting_room",
            "payload": {"object": {
                "id": "meet-wr-created",
                "participant": {"user_name": "Patient X"},
            }},
        }

        from app.blueprints.webhooks.zoom.zoom_webhook_helpers import _handle_waiting_room_joined
        body, status = _handle_waiting_room_joined(payload, account)

    assert status == 200
    created = next(c for c in calls if c["event_type"] == "encounter.created")
    assert created["success"] is True
    assert created["zoom_account_id"] == "acct-wr-created"
    assert created["openemr_appointment_id"] == "999"
    assert created["openemr_provider_id"] == "10"
    assert created["openemr_patient_id"] == "1"
    assert created["zoom_meeting_id"] == "meet-wr-created"
    assert created["openemr_encounter_number"] == "777003"
    assert created["detail"] == {"trigger": "waiting_room"}
