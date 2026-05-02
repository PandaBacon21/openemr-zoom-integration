from datetime import datetime, timedelta, timezone

from auth_utils import AUTH_HEADERS, INVALID_AUTH_HEADERS
from app.extensions import db
from app.models import AuditLog


def _add_audit_log(
    event_type: str,
    *,
    zoom_account_id: str = "acct-1",
    success: bool = True,
    occurred_at: datetime | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        zoom_account_id=zoom_account_id,
        openemr_appointment_id="999",
        zoom_meeting_id="123456789",
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
            occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        _add_audit_log(
            "meeting.created",
            zoom_account_id="acct-2",
            success=True,
            occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        _add_audit_log(
            "meeting.create_failed",
            zoom_account_id="acct-1",
            success=False,
            occurred_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )

    response = client.get(
        "/audit/logs",
        headers=AUTH_HEADERS,
        query_string={
            "zoom_account_id": "acct-1",
            "event_type": "meeting.created",
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
