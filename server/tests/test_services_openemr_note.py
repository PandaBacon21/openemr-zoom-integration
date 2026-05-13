"""Tests for app.services.openemr.note helpers — SOAP and Clinical Notes upserts.

Both forms dedup by encounter via the `forms` registration table:
    forms.encounter + formdir + deleted=0

`form_clinical_notes.external_id` is populated with the latest Zoom note_id
for traceability but is no longer the dedup key.
"""

from types import SimpleNamespace

from app.services.openemr.note import (
    _upsert_clinical_note_form,
    _upsert_soap_form,
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
