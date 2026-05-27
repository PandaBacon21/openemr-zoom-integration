"""Tests for find_encounter_for_appointment + upsert_patient_tracker."""

from datetime import date, time, timedelta
from types import SimpleNamespace

from app.services.openemr.encounter.encounter import (
    find_encounter_for_appointment,
    ensure_encounter_for_appointment,
)
from app.services.openemr.appointments.appointment import upsert_patient_tracker


def _fake_engine(rows_by_query: list):
    """
    Mimics SQLAlchemy engine where each call to execute(...) returns one
    of the queued results. Each entry in `rows_by_query` is either:
      - dict-like with `.fetchone()` returning a SimpleNamespace or None
      - None (no row)
    """
    iterator = iter(rows_by_query)

    class FakeResult:
        def __init__(self, row):
            self._row = row

        def fetchone(self):
            return self._row

    class FakeConn:
        def execute(self, query, params=None):
            try:
                return FakeResult(next(iterator))
            except StopIteration:
                return FakeResult(None)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

        def connect(self):
            return FakeConn()

    return FakeEngine()


# -- find_encounter_for_appointment -----------------------------------------

def test_find_encounter_resolves_via_patient_tracker_first(monkeypatch):
    """patient_tracker.encounter > 0 → returns ('tracker' source)."""
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.get_openemr_db_engine",
        lambda: _fake_engine([SimpleNamespace(encounter=555001)]),
    )
    encounter, source = find_encounter_for_appointment(eid=999, pid=100, provider_id=10)
    assert encounter == 555001
    assert source == "tracker"


def test_find_encounter_falls_through_to_external_id_when_tracker_empty(monkeypatch):
    """Tracker query returns None (no row or encounter=0) → external_id lookup wins."""
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.get_openemr_db_engine",
        lambda: _fake_engine([
            None,                                       # tracker miss
            SimpleNamespace(encounter=555002),          # external_id hit
        ]),
    )
    encounter, source = find_encounter_for_appointment(eid=999, pid=100, provider_id=10)
    assert encounter == 555002
    assert source == "external_id"


def test_find_encounter_falls_through_to_manual_fallback(monkeypatch):
    """Tracker miss + external_id miss → manual_fallback path wins; stamps external_id."""
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.get_openemr_db_engine",
        lambda: _fake_engine([
            None,                                       # tracker miss
            None,                                       # external_id miss
            SimpleNamespace(encounter=555003),          # manual_fallback hit
            # The 4th execute is the UPDATE that stamps external_id — its
            # result isn't read, fake just returns None.
        ]),
    )
    encounter, source = find_encounter_for_appointment(eid=999, pid=100, provider_id=10)
    assert encounter == 555003
    assert source == "manual_fallback"


def test_find_encounter_returns_none_when_no_path_hits(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.get_openemr_db_engine",
        lambda: _fake_engine([None, None, None]),
    )
    encounter, source = find_encounter_for_appointment(eid=999, pid=100, provider_id=10)
    assert encounter is None
    assert source is None


# -- upsert_patient_tracker -------------------------------------------------

class _UpsertCaptureEngine:
    """Captures all execute() calls so tests can inspect them."""
    def __init__(self, existing_row=None):
        self.existing_row = existing_row
        self.calls = []

    def begin(self):
        outer = self

        class FakeResult:
            def __init__(self, row):
                self._row = row

            def fetchone(self):
                return self._row

        class FakeConn:
            def execute(self, query, params=None):
                query_str = str(query).strip().lower()
                outer.calls.append({"query": query_str[:30], "params": params})
                if query_str.startswith("select"):
                    return FakeResult(outer.existing_row)
                return FakeResult(None)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return FakeConn()


def test_upsert_patient_tracker_inserts_when_missing(monkeypatch):
    engine = _UpsertCaptureEngine(existing_row=None)
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )

    upsert_patient_tracker(
        eid=999, pid=100,
        apptdate=date(2026, 5, 22), appttime=time(8, 0),
        encounter=555001, original_user="zoomly_test",
    )

    # 2 queries: 1 SELECT (existence check) + 1 INSERT
    assert len(engine.calls) == 2
    assert engine.calls[0]["query"].startswith("select")
    assert engine.calls[1]["query"].startswith("insert")
    insert_params = engine.calls[1]["params"]
    assert insert_params["eid"] == 999
    assert insert_params["pid"] == 100
    assert insert_params["enc"] == 555001
    assert insert_params["user"] == "zoomly_test"


def test_upsert_patient_tracker_updates_when_row_exists_with_new_encounter(monkeypatch):
    """Existing tracker row with encounter=0; called with encounter=555001 → UPDATE."""
    engine = _UpsertCaptureEngine(existing_row=SimpleNamespace(id=42, encounter=0))
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )

    upsert_patient_tracker(
        eid=999, pid=100,
        apptdate=date(2026, 5, 22), appttime=time(8, 0),
        encounter=555001, original_user="zoomly_test",
    )

    assert len(engine.calls) == 2
    assert engine.calls[1]["query"].startswith("update")
    update_params = engine.calls[1]["params"]
    assert update_params["enc"] == 555001
    assert update_params["id"] == 42


def test_upsert_patient_tracker_noop_when_existing_encounter_matches(monkeypatch):
    """Same encounter already linked → no UPDATE issued."""
    engine = _UpsertCaptureEngine(existing_row=SimpleNamespace(id=42, encounter=555001))
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )

    upsert_patient_tracker(
        eid=999, pid=100,
        apptdate=date(2026, 5, 22), appttime=time(8, 0),
        encounter=555001, original_user="zoomly_test",
    )

    # Only the SELECT runs — no UPDATE/INSERT issued
    assert len(engine.calls) == 1
    assert engine.calls[0]["query"].startswith("select")


# -- ensure_encounter_for_appointment ---------------------------------------

def test_ensure_returns_existing_encounter_without_creating(monkeypatch):
    """Find returns existing → ensure returns the same, source preserved, no create."""
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.find_encounter_for_appointment",
        lambda eid, pid, provider_id: (555001, "tracker"),
    )
    create_calls = []
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.create_encounter",
        lambda **kwargs: create_calls.append(kwargs) or None,
    )
    encounter, source = ensure_encounter_for_appointment(
        eid=999, pid=100, provider_id=10, facility_id=1, pc_catid=27,
    )
    assert encounter == 555001
    assert source == "tracker"
    assert create_calls == []


def test_ensure_creates_when_find_returns_none(monkeypatch):
    """Find returns None → ensure calls create, returns ('created')."""
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.find_encounter_for_appointment",
        lambda eid, pid, provider_id: (None, None),
    )
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.create_encounter",
        lambda **kwargs: 555002,
    )
    encounter, source = ensure_encounter_for_appointment(
        eid=999, pid=100, provider_id=10, facility_id=1, pc_catid=27,
    )
    assert encounter == 555002
    assert source == "created"


def test_ensure_returns_none_when_create_fails(monkeypatch):
    """Find returns None and create returns None → (None, None)."""
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.find_encounter_for_appointment",
        lambda eid, pid, provider_id: (None, None),
    )
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.create_encounter",
        lambda **kwargs: None,
    )
    encounter, source = ensure_encounter_for_appointment(
        eid=999, pid=100, provider_id=10, facility_id=1, pc_catid=27,
    )
    assert encounter is None
    assert source is None


def test_ensure_preserves_manual_fallback_source(monkeypatch):
    """Find via manual_fallback path → ensure surfaces 'manual_fallback' so caller can audit encounter.claimed."""
    monkeypatch.setattr(
        "app.services.openemr.encounter.encounter.find_encounter_for_appointment",
        lambda eid, pid, provider_id: (555003, "manual_fallback"),
    )
    encounter, source = ensure_encounter_for_appointment(
        eid=999, pid=100, provider_id=10, facility_id=1, pc_catid=27,
    )
    assert encounter == 555003
    assert source == "manual_fallback"


def test_upsert_patient_tracker_skips_update_when_caller_passes_zero(monkeypatch):
    """encounter=0 caller (e.g. generate_future_appointment first call) shouldn't blank
    an existing non-zero encounter on the tracker row."""
    engine = _UpsertCaptureEngine(existing_row=SimpleNamespace(id=42, encounter=555001))
    monkeypatch.setattr(
        "app.services.openemr.appointments.appointment.get_openemr_db_engine",
        lambda: engine,
    )

    upsert_patient_tracker(
        eid=999, pid=100,
        apptdate=date(2026, 5, 22), appttime=time(8, 0),
        encounter=0, original_user="zoomly_test",
    )

    # Only the SELECT — no INSERT or UPDATE
    assert len(engine.calls) == 1
