from datetime import datetime, timedelta, timezone

from auth_utils import AUTH_HEADERS, INVALID_AUTH_HEADERS
from app.extensions import db
from app.models import AuditLog


def _add_audit_log(
    event_type: str,
    *,
    zoom_account_id: str = "acct-1",
    success: bool = True,
    openemr_encounter_number: str | None = None,
    openemr_user_id: str | None = None,
    openemr_patient_id: str | None = None,
    zoom_note_id: str | None = None,
    occurred_at: datetime | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        zoom_account_id=zoom_account_id,
        openemr_appointment_id="999",
        openemr_encounter_number=openemr_encounter_number,
        openemr_user_id=openemr_user_id,
        openemr_patient_id=openemr_patient_id,
        zoom_meeting_id="123456789",
        zoom_note_id=zoom_note_id,
        success=success,
        detail='{"source": "test"}',
        occurred_at=occurred_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def test_get_audit_logs_returns_401_for_invalid_jwt(client):
    response = client.get("/audit/logs", headers=INVALID_AUTH_HEADERS)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid token"}


def test_get_audit_logs_returns_paginated_results(client, app):
    with app.app_context():
        older = _add_audit_log(
            "meeting.created",
            occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        newer = _add_audit_log(
            "note.written",
            occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        older_id = older.id
        newer_id = newer.id

    response = client.get(
        "/audit/logs",
        headers=AUTH_HEADERS,
        query_string={"page": 1, "per_page": 1},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["per_page"] == 1
    assert body["pages"] == 2
    assert [log["id"] for log in body["logs"]] == [newer_id]
    assert body["logs"][0]["event_type"] == "note.written"
    assert older_id != newer_id


def test_get_audit_logs_filters_by_account_success_and_date(client, app):
    with app.app_context():
        _add_audit_log(
            "meeting.created",
            zoom_account_id="acct-1",
            success=True,
            openemr_encounter_number="enc-1",
            openemr_user_id="provider-1",
            openemr_patient_id="patient-1",
            zoom_note_id="note-1",
            occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        _add_audit_log(
            "meeting.created",
            zoom_account_id="acct-2",
            success=True,
            openemr_encounter_number="enc-1",
            openemr_user_id="provider-1",
            openemr_patient_id="patient-1",
            zoom_note_id="note-1",
            occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        _add_audit_log(
            "meeting.create_failed",
            zoom_account_id="acct-1",
            success=False,
            openemr_encounter_number="enc-2",
            openemr_user_id="provider-2",
            openemr_patient_id="patient-2",
            zoom_note_id="note-2",
            occurred_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )

    response = client.get(
        "/audit/logs",
        headers=AUTH_HEADERS,
        query_string={
            "zoom_account_id": "acct-1",
            "event_type": "meeting.created",
            "openemr_encounter_number": "enc-1",
            "openemr_user_id": "provider-1",
            "openemr_patient_id": "patient-1",
            "zoom_note_id": "note-1",
            "success": "true",
            "date_from": datetime(2026, 1, 2, tzinfo=timezone.utc).isoformat(),
            "date_to": (
                datetime(2026, 1, 2, tzinfo=timezone.utc) + timedelta(hours=1)
            ).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 1
    assert body["logs"][0]["zoom_account_id"] == "acct-1"
    assert body["logs"][0]["event_type"] == "meeting.created"
    assert body["logs"][0]["openemr_encounter_number"] == "enc-1"
    assert body["logs"][0]["openemr_user_id"] == "provider-1"
    assert body["logs"][0]["openemr_patient_id"] == "patient-1"
    assert body["logs"][0]["zoom_note_id"] == "note-1"
    assert body["logs"][0]["success"] is True


def test_get_audit_logs_rejects_bad_dates_and_pagination(client):
    date_response = client.get(
        "/audit/logs",
        headers=AUTH_HEADERS,
        query_string={"date_from": "not-a-date"},
    )
    page_response = client.get(
        "/audit/logs",
        headers=AUTH_HEADERS,
        query_string={"page": "abc"},
    )

    assert date_response.status_code == 400
    assert date_response.get_json() == {"error": "Invalid date_from format: not-a-date"}
    assert page_response.status_code == 400
    assert page_response.get_json() == {"error": "Invalid pagination parameters"}


def test_get_audit_logs_exclude_event_types_hides_success_rows(client, app):
    """`exclude_event_types` should hide success rows for the listed events
    but keep their failures visible."""
    with app.app_context():
        _add_audit_log("jwks.fetched", success=True)
        _add_audit_log("openemr.token_verify_success", success=True)
        _add_audit_log("openemr.token_verify_failed", success=False)
        _add_audit_log("meeting.created", success=True)
        _add_audit_log("jwks.fetched", success=False)  # failure of noisy type

    response = client.get(
        "/audit/logs",
        headers=AUTH_HEADERS,
        query_string={
            "exclude_event_types": "jwks.fetched,openemr.token_verify_success",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    returned_events = {
        (log["event_type"], log["success"]) for log in body["logs"]
    }
    # Successful noisy events suppressed
    assert ("jwks.fetched", True) not in returned_events
    assert ("openemr.token_verify_success", True) not in returned_events
    # Failures of noisy types still surfaced
    assert ("jwks.fetched", False) in returned_events
    # Unrelated success events untouched
    assert ("meeting.created", True) in returned_events
    assert ("openemr.token_verify_failed", False) in returned_events
    assert body["total"] == 3


def test_get_audit_logs_exclude_event_types_skipped_when_event_type_set(client, app):
    """Explicit `event_type` filter wins over `exclude_event_types`."""
    with app.app_context():
        _add_audit_log("jwks.fetched", success=True)
        _add_audit_log("jwks.fetched", success=True)

    response = client.get(
        "/audit/logs",
        headers=AUTH_HEADERS,
        query_string={
            "event_type": "jwks.fetched",
            "exclude_event_types": "jwks.fetched",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 2
    assert all(log["event_type"] == "jwks.fetched" for log in body["logs"])
