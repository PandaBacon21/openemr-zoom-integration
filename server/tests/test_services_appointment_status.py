"""Tests for the forward-only mark_appointment_status state machine."""

import json
from types import SimpleNamespace

from app.extensions import db
from app.models import AccountConfig, AuditLog, ZoomAccount
from app.services.openemr.appointments.appointment import mark_appointment_status


class _CaptureStatusEngine:
    """
    Mimics SQLAlchemy engine for mark_appointment_status. Handles three
    SELECTs (appointment row, tracker row) plus the two UPDATEs and two
    INSERTs that may follow, and records each so tests can assert against
    them.

    Args:
        current_status: pc_apptstatus on the simulated appointment row
        pid:            pc_pid on the simulated appointment row
        eid_exists:     when False, the appointment SELECT returns None
        tracker_row:    None means no patient_tracker row exists (helper
                        will INSERT one); a SimpleNamespace with
                        id/lastseq/laststatus simulates an existing tracker
    """
    def __init__(
        self,
        current_status: str,
        pid: int = 100,
        eid_exists: bool = True,
        tracker_row=None,
    ):
        self.current_status = current_status
        self.pid = pid
        self.eid_exists = eid_exists
        self.tracker_row = tracker_row
        self.updates: list[dict] = []           # appointment UPDATEs (pc_apptstatus)
        self.tracker_updates: list[dict] = []   # patient_tracker UPDATEs (lastseq)
        self.tracker_inserts: list[dict] = []   # new patient_tracker rows
        self.element_inserts: list[dict] = []   # patient_tracker_element rows

    def begin(self):
        outer = self

        class FakeResult:
            def __init__(self, row=None, lastrowid=None):
                self._row = row
                self.lastrowid = lastrowid

            def fetchone(self):
                return self._row

        class FakeConn:
            def execute(self, query, params=None):
                q = str(query).strip().lower()
                if q.startswith("select"):
                    if "patient_tracker" in q:
                        return FakeResult(outer.tracker_row)
                    if not outer.eid_exists:
                        return FakeResult(None)
                    return FakeResult(SimpleNamespace(
                        pc_apptstatus=outer.current_status,
                        pc_pid=outer.pid,
                        pc_eventDate="2026-05-22",
                        pc_startTime="09:00:00",
                    ))
                if q.startswith("update"):
                    if "patient_tracker" in q:
                        outer.tracker_updates.append(dict(params))
                    else:
                        outer.updates.append(dict(params))
                    return FakeResult(None)
                if q.startswith("insert"):
                    if "patient_tracker_element" in q:
                        outer.element_inserts.append(dict(params))
                        return FakeResult(None)
                    if "patient_tracker" in q:
                        outer.tracker_inserts.append(dict(params))
                        return FakeResult(None, lastrowid=42)
                    return FakeResult(None)
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


def test_creates_tracker_row_when_none_exists(app, monkeypatch):
    """
    When no patient_tracker row exists for this appointment, the helper
    must INSERT one + INSERT a first element at seq=1. This is the path
    for hydrated demo appointments where the user never touched the
    calendar dialog before the Zoom webhook fired.
    """
    engine = _CaptureStatusEngine(current_status="-", tracker_row=None)
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        result = mark_appointment_status(999, "@", source="zoom_waiting_room")
        assert result is True
        # pc_apptstatus UPDATE
        assert len(engine.updates) == 1
        # New tracker row + first element
        assert len(engine.tracker_inserts) == 1
        assert len(engine.element_inserts) == 1
        assert engine.element_inserts[0]["status"] == "@"
        assert engine.element_inserts[0]["user"] == "zoom_waiting_room"
        # No tracker UPDATE — we created fresh
        assert engine.tracker_updates == []


def test_appends_tracker_element_when_status_changes(app, monkeypatch):
    """
    When patient_tracker already exists (e.g., user manually toggled to
    Arrived via the calendar UI), the helper must UPDATE lastseq and
    INSERT a new element row at seq=lastseq+1 so the Flow Board picks
    up the new status. This is the exact scenario that caused the
    original bug: manual Arrived + Zoom-driven In Exam Room.
    """
    engine = _CaptureStatusEngine(
        current_status="@",
        tracker_row=SimpleNamespace(id=7, lastseq=1, laststatus="@"),
    )
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )
    with app.app_context():
        result = mark_appointment_status(999, "<", source="zoom_meeting_started")
        assert result is True
        assert len(engine.updates) == 1
        # No new tracker INSERT — row already existed
        assert engine.tracker_inserts == []
        # lastseq bumped to 2
        assert len(engine.tracker_updates) == 1
        assert engine.tracker_updates[0] == {"seq": 2, "id": 7}
        # New element at seq=2 with target status
        assert len(engine.element_inserts) == 1
        elem = engine.element_inserts[0]
        assert elem["status"] == "<"
        assert elem["seq"] == "2"
        assert elem["tid"] == 7
        assert elem["user"] == "zoom_meeting_started"


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
