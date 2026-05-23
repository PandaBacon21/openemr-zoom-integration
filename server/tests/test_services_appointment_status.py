"""Tests for the forward-only mark_appointment_status state machine."""

import json
from types import SimpleNamespace

from app.extensions import db
from app.models import AccountConfig, AuditLog, ZoomAccount
from app.services.openemr.appointments.appointment import mark_appointment_status


class _CaptureStatusEngine:
    """
    Mimics SQLAlchemy engine for mark_appointment_status — supports SELECT
    (returns the canned current_status row) and UPDATE (records the call).
    """
    def __init__(self, current_status: str, pid: int = 100, eid_exists: bool = True):
        self.current_status = current_status
        self.pid = pid
        self.eid_exists = eid_exists
        self.updates: list[dict] = []

    def begin(self):
        outer = self

        class FakeResult:
            def __init__(self, row):
                self._row = row

            def fetchone(self):
                return self._row

        class FakeConn:
            def execute(self, query, params=None):
                q = str(query).strip().lower()
                if q.startswith("select"):
                    row = (
                        SimpleNamespace(pc_apptstatus=outer.current_status, pc_pid=outer.pid)
                        if outer.eid_exists else None
                    )
                    return FakeResult(row)
                # UPDATE
                outer.updates.append(dict(params))
                return FakeResult(None)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return FakeConn()


def _create_account_ctx(app, account_id: str = "acct-status"):
    """Minimum app context for write_audit_log to persist."""
    with app.app_context():
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


def test_forward_transition_pending_to_arrived(app, monkeypatch):
    engine = _CaptureStatusEngine(current_status="-")
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        _create_account_ctx.__wrapped__ if hasattr(_create_account_ctx, "__wrapped__") else None
        # Don't actually create account here; audit table accepts NULL account_id
        result = mark_appointment_status(999, "@", source="zoom_waiting_room")
        assert result is True
        # UPDATE was issued
        assert len(engine.updates) == 1
        assert engine.updates[0] == {"status": "@", "eid": 999}
        # Audit emitted
        audits = AuditLog.query.filter_by(event_type="appointment.status_arrived").all()
        assert len(audits) == 1
        detail = json.loads(audits[0].detail)
        assert detail["previous_status"] == "-"
        assert detail["new_status"] == "@"
        assert detail["source"] == "zoom_waiting_room"


def test_forward_transition_arrived_to_in_exam_room(app, monkeypatch):
    engine = _CaptureStatusEngine(current_status="@")
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        result = mark_appointment_status(999, "<", source="zoom_meeting_started")
        assert result is True
        assert len(engine.updates) == 1
        audits = AuditLog.query.filter_by(event_type="appointment.status_in_exam_room").all()
        assert len(audits) == 1


def test_forward_transition_in_exam_room_to_checked_out(app, monkeypatch):
    engine = _CaptureStatusEngine(current_status="<")
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        result = mark_appointment_status(999, ">", source="zoom_meeting_ended")
        assert result is True
        audits = AuditLog.query.filter_by(event_type="appointment.status_checked_out").all()
        assert len(audits) == 1


def test_no_op_when_target_equals_current(app, monkeypatch):
    """Re-firing the same trigger (e.g. meeting.started after Start button) is a no-op."""
    engine = _CaptureStatusEngine(current_status="@")
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        result = mark_appointment_status(999, "@", source="zoom_meeting_started")
        assert result is False
        assert engine.updates == []
        # No audit
        audits = AuditLog.query.filter_by(event_type="appointment.status_arrived").all()
        assert audits == []


def test_backward_transition_refused(app, monkeypatch):
    """In Exam Room → Arrived should NOT regress."""
    engine = _CaptureStatusEngine(current_status="<")
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        result = mark_appointment_status(999, "@", source="late_webhook")
        assert result is False
        assert engine.updates == []


def test_terminal_state_refuses_further_transitions(app, monkeypatch):
    """No Show (?) is terminal — refuses progress to anything."""
    engine = _CaptureStatusEngine(current_status="?")
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        assert mark_appointment_status(999, ">", source="zoom_meeting_ended") is False
        assert mark_appointment_status(999, "@", source="zoom_waiting_room") is False
        assert engine.updates == []


def test_checked_out_terminal(app, monkeypatch):
    """Checked Out — can't progress further. Anything 'before' is backward; anything 'after' has lower priority since > and ?/%/# are at boundary."""
    engine = _CaptureStatusEngine(current_status=">")
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        # > → < is backward, refuses
        assert mark_appointment_status(999, "<", source="late_start") is False
        # > → > is no-op (equal priority)
        assert mark_appointment_status(999, ">", source="duplicate_ended") is False
        assert engine.updates == []


def test_eid_not_found_returns_false(app, monkeypatch):
    engine = _CaptureStatusEngine(current_status="", eid_exists=False)
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        result = mark_appointment_status(999, "@", source="zoom_waiting_room")
        assert result is False
        assert engine.updates == []


def test_audit_includes_patient_id(app, monkeypatch):
    """The pid from openemr_postcalendar_events propagates into the audit row."""
    engine = _CaptureStatusEngine(current_status="-", pid=151)
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        mark_appointment_status(999, "@", source="zoom_waiting_room")
        audits = AuditLog.query.filter_by(event_type="appointment.status_arrived").all()
        assert len(audits) == 1
        assert audits[0].openemr_patient_id == "151"
        assert audits[0].openemr_appointment_id == "999"
