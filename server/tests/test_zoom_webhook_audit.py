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
            lambda eid, pid, provider_id: None,
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
    assert write_call["detail"] == {"ehr_context": False}


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
            lambda eid, pid, provider_id: None,
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
            lambda eid, pid, provider_id: None,
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
