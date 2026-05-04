import hashlib
import hmac
from types import SimpleNamespace

from auth_utils import AUTH_HEADERS, INVALID_AUTH_HEADERS
from app.extensions import db
from app.models import ClinicalNoteRecord, MeetingRecord, ZoomAccount


def _create_account(account_id: str, *, is_active: bool = True) -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path="/tmp/private.pem",
        kid=f"zoomly-{account_id}",
        is_active=is_active,
    )
    db.session.add(account)
    db.session.commit()
    return account


def _openemr_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body.strip(), hashlib.sha256).hexdigest()


def _fake_encounter_engine(row):
    class FakeResult:
        def fetchone(self):
            return row

    class FakeConn:
        def execute(self, query, params):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    return FakeEngine()


def _create_meeting_with_note(account_id: str, *, completed: bool = False):
    account = _create_account(account_id)
    record = MeetingRecord(
        zoom_account_id=account.account_id,
        zoom_meeting_id=f"meeting-{account_id}",
        openemr_appointment_id="999",
        openemr_provider_id="10",
    )
    db.session.add(record)
    db.session.add(
        ClinicalNoteRecord(
            zoom_meeting_id=record.zoom_meeting_id,
            zoom_note_id=f"note-{account_id}",
            zoom_note_title="Clinical Note",
            is_completed_in_zoom=completed,
        )
    )
    db.session.commit()
    return account, record


def test_get_users_returns_500_when_jwt_secret_not_configured(client, app):
    app.config["CONFIG_JWT_SECRET"] = None

    response = client.get("/zoom/users", headers=AUTH_HEADERS)

    assert response.status_code == 500
    assert response.get_json() == {"error": "JWT secret not configured"}


def test_get_users_returns_401_for_invalid_jwt(client):
    response = client.get("/zoom/users", headers=INVALID_AUTH_HEADERS)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid token"}


def test_get_users_requires_zoom_account_id(client):
    response = client.get("/zoom/users", headers=AUTH_HEADERS)

    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_get_users_returns_404_for_unknown_account(client):
    response = client.get(
        "/zoom/users",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "missing-account"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "No active registration found for account missing-account"}


def test_get_users_returns_404_for_inactive_account(client, app):
    with app.app_context():
        _create_account("acct-1", is_active=False)

    response = client.get(
        "/zoom/users",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "No active registration found for account acct-1"}


def test_get_users_success_returns_user_list(client, app, monkeypatch):
    with app.app_context():
        _create_account("acct-1", is_active=True)

    captured = {}

    def fake_get_zoom_users(account, search=None):
        captured["account_id"] = account.account_id
        captured["search"] = search
        return [
            {
                "zoom_user_id": "u-1",
                "email": "dr.jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "full_name": "Jane Doe",
                "display_name": "Dr Jane Doe",
                "type": 2,
                "status": "active",
            }
        ]

    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.get_zoom_users", fake_get_zoom_users)

    response = client.get(
        "/zoom/users",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1", "search": "jane"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "count": 1,
        "users": [
            {
                "zoom_user_id": "u-1",
                "email": "dr.jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "full_name": "Jane Doe",
                "display_name": "Dr Jane Doe",
                "type": 2,
                "status": "active",
            }
        ],
    }
    assert captured == {"account_id": "acct-1", "search": "jane"}


def test_get_users_maps_service_error_to_500(client, app, monkeypatch):
    with app.app_context():
        _create_account("acct-1", is_active=True)

    def fake_get_zoom_users(account, search=None):
        raise RuntimeError("zoom unavailable")

    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.get_zoom_users", fake_get_zoom_users)

    response = client.get(
        "/zoom/users",
        headers=AUTH_HEADERS,
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "zoom unavailable"}


def test_complete_zoom_note_audits_success_with_encounter_context(client, app, monkeypatch):
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-complete")

    calls = []
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.mark_zoom_note_completed", lambda account, note_id: True)
    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.write_audit_log", lambda **kwargs: calls.append(kwargs))

    body = b""
    response = client.post(
        "/zoom/encounter/555001/complete_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "completed", "note_id": "note-acct-complete"}
    audit_call = next(call for call in calls if call["event_type"] == "zoom.completion_success")
    assert audit_call["success"] is True
    assert audit_call["zoom_account_id"] == "acct-complete"
    assert audit_call["zoom_note_id"] == "note-acct-complete"
    assert audit_call["openemr_appointment_id"] == "999"
    assert audit_call["openemr_encounter_number"] == "555001"
    assert audit_call["openemr_provider_id"] == 10
    assert audit_call["openemr_patient_id"] == 1
    assert "detail" not in audit_call


def test_complete_zoom_note_audits_skip_with_encounter_context(client, app, monkeypatch):
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-complete-skip", completed=True)

    calls = []
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=3, provider_id=30, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.mark_zoom_note_completed",
        lambda account, note_id: (_ for _ in ()).throw(AssertionError("should not complete again")),
    )
    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.write_audit_log", lambda **kwargs: calls.append(kwargs))

    body = b""
    response = client.post(
        "/zoom/encounter/555003/complete_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "already_completed"}
    audit_call = next(call for call in calls if call["event_type"] == "zoom.completion_skipped")
    assert audit_call["success"] is True
    assert audit_call["zoom_account_id"] == "acct-complete-skip"
    assert audit_call["zoom_note_id"] == "note-acct-complete-skip"
    assert audit_call["openemr_appointment_id"] == "999"
    assert audit_call["openemr_encounter_number"] == "555003"
    assert audit_call["openemr_provider_id"] == 30
    assert audit_call["openemr_patient_id"] == 3


def test_complete_zoom_note_audits_false_completion_result_as_error(client, app, monkeypatch):
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-complete-fail")

    calls = []
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=2, provider_id=20, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.mark_zoom_note_completed", lambda account, note_id: False)
    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.write_audit_log", lambda **kwargs: calls.append(kwargs))

    body = b""
    response = client.post(
        "/zoom/encounter/555002/complete_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "error", "reason": "zoom api error"}
    audit_call = next(call for call in calls if call["event_type"] == "zoom.completion_error")
    assert audit_call["success"] is False
    assert audit_call["zoom_account_id"] == "acct-complete-fail"
    assert audit_call["zoom_note_id"] == "note-acct-complete-fail"
    assert audit_call["openemr_appointment_id"] == "999"
    assert audit_call["openemr_encounter_number"] == "555002"
    assert audit_call["openemr_provider_id"] == 20
    assert audit_call["openemr_patient_id"] == 2
    assert audit_call["error_message"] == "Zoom note completion failed"
