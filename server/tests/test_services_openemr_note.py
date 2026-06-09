"""Tests for app.services.openemr.note helpers — SOAP and Clinical Notes upserts.

Both forms dedup by encounter via the `forms` registration table:
    forms.encounter + formdir + deleted=0

`form_clinical_notes.external_id` is populated with the latest Zoom note_id
for traceability but is no longer the dedup key.

Also covers MeetingRecord.clinical_note relationship ordering (most recent
note wins when multiple ClinicalNoteRecord rows exist for one meeting).
"""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.extensions import db
from app.models import AuditLog, ClinicalNoteRecord, MeetingRecord
from app.services.openemr.note import (
    _upsert_clinical_note_form,
    _upsert_soap_form,
    write_note_to_encounter,
)


class FakeResult:
    def __init__(self, row=None, lastrowid=None):
        self._row = row
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._row


class RecordingConn:
    """Records SQL calls. SELECTs pop from a queue of fake rows; INSERTs return a lastrowid."""

    def __init__(self, select_returns=None, insert_lastrowid=42):
        self.calls = []
        self._select_returns = list(select_returns or [])
        self._insert_lastrowid = insert_lastrowid

    def execute(self, query, params):
        sql = str(query).strip()
        verb = sql.split()[0].upper()
        self.calls.append({"verb": verb, "sql": sql, "params": params})

        if verb == "SELECT":
            row = self._select_returns.pop(0) if self._select_returns else None
            return FakeResult(row=row)
        if verb == "INSERT":
            return FakeResult(lastrowid=self._insert_lastrowid)
        return FakeResult()


# ---------------------------------------------------------------------------
# Clinical Notes upsert
# ---------------------------------------------------------------------------


def test_upsert_clinical_note_updates_when_form_exists_for_encounter():
    """When a Clinical Notes form is already registered on the encounter, UPDATE
    it in place rather than inserting a duplicate — even when the new note_id
    differs from the one currently stored in external_id."""
    conn = RecordingConn(select_returns=[SimpleNamespace(form_id=99)])

    cn_id = _upsert_clinical_note_form(
        conn=conn,
        encounter_number=1234,
        pid=10,
        provider_id=20,
        provider_username="amiller",
        note_content="actual note content",
        note_title="Visit Note",
        note_id="zoom-note-NEW-123",
        now="2026-05-12 10:00:00",
        today="2026-05-12",
    )

    assert cn_id == 99
    assert [c["verb"] for c in conn.calls] == ["SELECT", "UPDATE"]

    # Dedup SELECT goes through forms (not form_clinical_notes.external_id)
    select_call = conn.calls[0]
    assert "FROM forms" in select_call["sql"]
    assert "formdir = 'clinical_notes'" in select_call["sql"]
    assert "deleted = 0" in select_call["sql"]
    assert select_call["params"] == {"encounter": 1234}

    # UPDATE refreshes description AND external_id with the latest note_id
    update_call = conn.calls[1]
    assert "UPDATE form_clinical_notes" in update_call["sql"]
    assert "external_id = :external_id" in update_call["sql"]
    assert update_call["params"]["external_id"] == "zoom-note-NEW-123"
    assert update_call["params"]["id"] == 99
    assert "Visit Note" in update_call["params"]["description"]
    assert "actual note content" in update_call["params"]["description"]


def test_upsert_clinical_note_inserts_when_no_form_on_encounter():
    """No Clinical Notes form on the encounter → INSERT form_clinical_notes,
    self-link form_id, and register in forms."""
    conn = RecordingConn(select_returns=[None], insert_lastrowid=77)

    cn_id = _upsert_clinical_note_form(
        conn=conn,
        encounter_number=1234,
        pid=10,
        provider_id=20,
        provider_username="amiller",
        note_content="brand new content",
        note_title="Initial Note",
        note_id="zoom-note-ABC-999",
        now="2026-05-12 10:00:00",
        today="2026-05-12",
    )

    assert cn_id == 77
    assert [c["verb"] for c in conn.calls] == ["SELECT", "INSERT", "UPDATE", "INSERT"]

    cn_insert = conn.calls[1]
    assert "INSERT INTO form_clinical_notes" in cn_insert["sql"]
    assert cn_insert["params"]["external_id"] == "zoom-note-ABC-999"
    assert cn_insert["params"]["pid"] == 10
    # form_clinical_notes.encounter is TEXT in OpenEMR — stored as a string
    assert cn_insert["params"]["encounter"] == "1234"

    self_ref_update = conn.calls[2]
    assert "UPDATE form_clinical_notes" in self_ref_update["sql"]
    assert "SET form_id = :id" in self_ref_update["sql"]
    assert self_ref_update["params"]["id"] == 77

    forms_insert = conn.calls[3]
    assert "INSERT INTO forms" in forms_insert["sql"]
    assert "'Clinical Notes'" in forms_insert["sql"]
    assert "'clinical_notes'" in forms_insert["sql"]
    assert forms_insert["params"]["form_id"] == 77
    assert forms_insert["params"]["encounter"] == 1234


def test_upsert_clinical_note_dedup_query_does_not_reference_external_id():
    """Regression guard: the dedup SELECT must not match on external_id, since
    a new Zoom note_id for the same meeting must still update the existing row."""
    conn = RecordingConn(select_returns=[SimpleNamespace(form_id=1)])

    _upsert_clinical_note_form(
        conn=conn,
        encounter_number=1,
        pid=1,
        provider_id=1,
        provider_username="u",
        note_content="c",
        note_title="t",
        note_id="any-note-id",
        now="2026-05-12 10:00:00",
        today="2026-05-12",
    )

    select_sql = conn.calls[0]["sql"]
    assert "external_id" not in select_sql.lower().split("where")[1].split("limit")[0]


# ---------------------------------------------------------------------------
# SOAP upsert
# ---------------------------------------------------------------------------


def test_upsert_soap_updates_when_form_exists_for_encounter():
    conn = RecordingConn(select_returns=[SimpleNamespace(form_id=55)])
    soap = {
        "subjective": "Patient reports headache.",
        "objective":  "BP 120/80.",
        "assessment": "Tension headache.",
        "plan":       "Tylenol PRN.",
    }

    soap_id = _upsert_soap_form(
        conn=conn,
        encounter_number=1234,
        pid=10,
        provider_id=20,
        provider_username="amiller",
        soap=soap,
        now="2026-05-12 10:00:00",
    )

    assert soap_id == 55
    assert [c["verb"] for c in conn.calls] == ["SELECT", "UPDATE"]

    select_call = conn.calls[0]
    assert "FROM forms" in select_call["sql"]
    assert "formdir = 'soap'" in select_call["sql"]
    assert "deleted = 0" in select_call["sql"]
    assert select_call["params"] == {"encounter": 1234}

    update_call = conn.calls[1]
    assert "UPDATE form_soap" in update_call["sql"]
    assert update_call["params"]["subjective"] == "Patient reports headache."
    assert update_call["params"]["objective"] == "BP 120/80."
    assert update_call["params"]["assessment"] == "Tension headache."
    assert update_call["params"]["plan"] == "Tylenol PRN."
    assert update_call["params"]["id"] == 55


def test_upsert_soap_inserts_when_no_form_on_encounter():
    conn = RecordingConn(select_returns=[None], insert_lastrowid=88)
    soap = {"subjective": "S", "objective": "O", "assessment": "A", "plan": "P"}

    soap_id = _upsert_soap_form(
        conn=conn,
        encounter_number=1234,
        pid=10,
        provider_id=20,
        provider_username="amiller",
        soap=soap,
        now="2026-05-12 10:00:00",
    )

    assert soap_id == 88
    assert [c["verb"] for c in conn.calls] == ["SELECT", "INSERT", "INSERT"]

    soap_insert = conn.calls[1]
    assert "INSERT INTO form_soap" in soap_insert["sql"]
    assert soap_insert["params"]["subjective"] == "S"
    assert soap_insert["params"]["pid"] == 10

    forms_insert = conn.calls[2]
    assert "INSERT INTO forms" in forms_insert["sql"]
    assert "'SOAP'" in forms_insert["sql"]
    assert "'soap'" in forms_insert["sql"]
    assert forms_insert["params"]["form_id"] == 88
    assert forms_insert["params"]["encounter"] == 1234


# ---------------------------------------------------------------------------
# MeetingRecord.clinical_note ordering
# ---------------------------------------------------------------------------


def test_meeting_record_clinical_note_returns_most_recent(app):
    """When multiple ClinicalNoteRecord rows exist for one MeetingRecord
    (e.g. a failed/empty note followed by a real one), the .clinical_note
    relationship returns the most recently received note."""
    with app.app_context():
        meeting = MeetingRecord(
            zoom_meeting_id="zm-abc-123",
            zoom_account_id="acct-1",
            openemr_appointment_id="500",
            openemr_user_id="20",
            status="started",
        )
        db.session.add(meeting)
        db.session.commit()

        older = ClinicalNoteRecord(
            zoom_meeting_id=meeting.zoom_meeting_id,
            zoom_note_id="note-OLD-failed",
            zoom_note_title="Failed note",
            note_content="",
            is_written_to_openemr=False,
        )
        older.received_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.session.add(older)
        db.session.commit()

        newer = ClinicalNoteRecord(
            zoom_meeting_id=meeting.zoom_meeting_id,
            zoom_note_id="note-NEW-real",
            zoom_note_title="Real note",
            note_content="actual content",
            is_written_to_openemr=False,
        )
        newer.received_at = datetime.now(timezone.utc)
        db.session.add(newer)
        db.session.commit()

        # Force a fresh load of the relationship
        db.session.expire(meeting)
        resolved = MeetingRecord.query.filter_by(zoom_meeting_id="zm-abc-123").one()

        assert resolved.clinical_note is not None
        assert resolved.clinical_note.zoom_note_id == "note-NEW-real"


# ---------------------------------------------------------------------------
# write_note_to_encounter eSign-locked guard
# ---------------------------------------------------------------------------


class _FakeBeginEngine:
    """Engine stub whose .begin() returns a connection that swallows every
    SQL call. Used by the unlocked-path test where we patch the upsert
    helpers out — write_note_to_encounter just needs the context manager
    to exist."""

    class _Conn:
        def execute(self, *a, **kw):
            return FakeResult()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def begin(self):
        return self._Conn()


def _patch_lock_target(monkeypatch, value):
    monkeypatch.setattr(
        "app.services.openemr.note.encounter_lock_target",
        lambda enc: value,
    )


def _last_audit(event_type: str):
    return (
        AuditLog.query
        .filter_by(event_type=event_type)
        .order_by(AuditLog.id.desc())
        .first()
    )


def _call_write_note(monkeypatch, **overrides):
    """Run write_note_to_encounter with sensible defaults so each test only
    declares the field it cares about."""
    kwargs = {
        "encounter_number": 30001,
        "pid": 100,
        "provider_id": 14,
        "provider_username": "amiller",
        "note_content": "S: cough\nO: T 38.2\nA: viral URI\nP: rest",
        "note_title": "Visit note",
        "note_id": "zoom-note-xyz",
        "note_writeback_mode": "both",
    }
    kwargs.update(overrides)
    return write_note_to_encounter(**kwargs)


def test_write_note_skipped_when_encounter_esigned(app, monkeypatch):
    """Encounter-level eSign cascades to every form. The guard must refuse
    the write, emit an audit row tagged lock_target='encounter', and never
    touch the engine."""
    _patch_lock_target(monkeypatch, "encounter")
    # If the function tries to reach the engine the test fails loudly.
    monkeypatch.setattr(
        "app.services.openemr.note.get_openemr_db_engine",
        lambda: (_ for _ in ()).throw(AssertionError("engine should not be used")),
    )
    with app.app_context():
        result = _call_write_note(monkeypatch)
        assert result is False
        audit = _last_audit("note.write_skipped_locked")
        assert audit is not None
        assert audit.success is False
        assert audit.openemr_encounter_number == "30001"
        assert audit.zoom_note_id == "zoom-note-xyz"
        detail = json.loads(audit.detail)
        assert detail["lock_target"] == "encounter"
        assert detail["note_writeback_mode"] == "both"


def test_write_note_skipped_when_soap_form_locked(app, monkeypatch):
    """Form-level eSign on the SOAP form only locks that form, but the
    Zoom note is finalized — Clinical Notes writeback must also be refused."""
    _patch_lock_target(monkeypatch, "soap")
    monkeypatch.setattr(
        "app.services.openemr.note.get_openemr_db_engine",
        lambda: (_ for _ in ()).throw(AssertionError("engine should not be used")),
    )
    with app.app_context():
        result = _call_write_note(monkeypatch, note_writeback_mode="clinical_note_only")
        assert result is False
        audit = _last_audit("note.write_skipped_locked")
        detail = json.loads(audit.detail)
        assert detail["lock_target"] == "soap"
        assert detail["note_writeback_mode"] == "clinical_note_only"


def test_write_note_skipped_when_clinical_notes_form_locked(app, monkeypatch):
    """Mirror of the SOAP case — Clinical Notes lock blocks SOAP writeback too."""
    _patch_lock_target(monkeypatch, "clinical_notes")
    monkeypatch.setattr(
        "app.services.openemr.note.get_openemr_db_engine",
        lambda: (_ for _ in ()).throw(AssertionError("engine should not be used")),
    )
    with app.app_context():
        result = _call_write_note(monkeypatch, note_writeback_mode="soap_only")
        assert result is False
        audit = _last_audit("note.write_skipped_locked")
        detail = json.loads(audit.detail)
        assert detail["lock_target"] == "clinical_notes"


def test_write_note_proceeds_when_no_locks(app, monkeypatch):
    """No lock row → both upserts fire and the function returns True. The
    upserts themselves are patched out — their internals have dedicated
    tests above; this test only verifies the guard lets them through."""
    _patch_lock_target(monkeypatch, None)
    monkeypatch.setattr(
        "app.services.openemr.note.get_openemr_db_engine",
        lambda: _FakeBeginEngine(),
    )
    soap_calls = []
    cn_calls = []
    monkeypatch.setattr(
        "app.services.openemr.note._upsert_soap_form",
        lambda **kw: soap_calls.append(kw) or 1,
    )
    monkeypatch.setattr(
        "app.services.openemr.note._upsert_clinical_note_form",
        lambda **kw: cn_calls.append(kw) or 1,
    )
    with app.app_context():
        result = _call_write_note(monkeypatch)
        assert result is True
        assert len(soap_calls) == 1
        assert len(cn_calls) == 1
        # No skipped-locked audit was emitted.
        assert _last_audit("note.write_skipped_locked") is None
