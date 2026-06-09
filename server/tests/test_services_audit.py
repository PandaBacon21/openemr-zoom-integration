import json


def test_write_audit_log_persists_entry_and_normalizes_context_fields(app):
    from app.models import AuditLog
    from app.services.audit import write_audit_log

    with app.app_context():
        write_audit_log(
            event_type="meeting.created",
            success=True,
            zoom_account_id="acct-1",
            openemr_appointment_id=999,
            openemr_encounter_number=555001,
            openemr_user_id=10,
            openemr_patient_id=1,
            zoom_meeting_id=123456789,
            detail={"event": "appointment.set", "appointment_type": 27},
        )

        entry = AuditLog.query.one()

    assert entry.event_type == "meeting.created"
    assert entry.success is True
    assert entry.zoom_account_id == "acct-1"
    assert entry.openemr_appointment_id == "999"
    assert entry.openemr_encounter_number == "555001"
    assert entry.openemr_user_id == "10"
    assert entry.openemr_patient_id == "1"
    assert entry.zoom_meeting_id == "123456789"
    assert json.loads(entry.detail) == {"event": "appointment.set", "appointment_type": 27}
    assert entry.occurred_at is not None


def test_write_audit_log_swallows_session_errors_and_rolls_back(app, monkeypatch):
    from app.extensions import db
    from app.models import AuditLog
    from app.services.audit import write_audit_log

    rollback_calls = {"count": 0}

    def _raise_on_add(_entry):
        raise RuntimeError("db add failed")

    def _count_rollback():
        rollback_calls["count"] += 1

    with app.app_context():
        monkeypatch.setattr(db.session, "add", _raise_on_add)
        monkeypatch.setattr(db.session, "rollback", _count_rollback)

        write_audit_log(
            event_type="meeting.create_failed",
            success=False,
            zoom_account_id="acct-fail",
            openemr_appointment_id=999,
            error_message="boom",
            detail={"step": "add"},
        )

        assert rollback_calls["count"] == 1
        assert AuditLog.query.count() == 0
