import hashlib
import hmac
from types import SimpleNamespace

from auth_utils import AUTH_HEADERS, INVALID_AUTH_HEADERS
from app.extensions import db
from app.models import AccountConfig, ClinicalNoteRecord, MeetingRecord, ZoomAccount


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
    db.session.add(AccountConfig(account_id=account_id, timezone="America/Denver"))
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


def test_fetch_zoom_note_uses_account_writeback_mode(client, app, monkeypatch):
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account, _record = _create_meeting_with_note("acct-fetch-mode")
        account.config.note_writeback_mode = "soap_only"
        db.session.commit()

    captured = {}
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_zoom_clinical_note",
        lambda account, note_id: {
            "note_title": "Zoom Clinical Note",
            "note_content": "Subjective\nDoing well",
        },
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_provider_username",
        lambda provider_id: "provider-user",
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.write_note_to_encounter",
        lambda **kwargs: captured.update(kwargs) or True,
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555010/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "encounter_number": 555010,
        "note_id": "note-acct-fetch-mode",
        "note_title": "Zoom Clinical Note",
    }
    assert captured["note_writeback_mode"] == "soap_only"
    assert captured["provider_username"] == "provider-user"


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


# ---------------------------------------------------------------------------
# fetch_zoom_note — audit/log coverage (manual fetch parity)
# ---------------------------------------------------------------------------

def _fake_raising_engine(exc: Exception):
    class FakeConn:
        def execute(self, query, params):
            raise exc

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    return FakeEngine()


def _patch_manual_fetch_audit(monkeypatch, calls):
    """
    fetch_zoom_note writes audits from two modules:
      - zoom_routes (direct write_audit_log calls)
      - zoom_route_helper (_audit_manual_fetch_failed helper)
    Patch both so all audit calls land in one list for assertion.
    """
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.write_audit_log",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_route_helper.write_audit_log",
        lambda **kwargs: calls.append(kwargs),
    )


def _create_meeting_without_note(account_id: str):
    account = _create_account(account_id)
    record = MeetingRecord(
        zoom_account_id=account.account_id,
        zoom_meeting_id=f"meeting-{account_id}",
        openemr_appointment_id="999",
        openemr_provider_id="10",
    )
    db.session.add(record)
    db.session.commit()
    return account, record


def test_fetch_zoom_note_audits_request_at_entry_even_on_failure(client, app, monkeypatch):
    """G-M1: every button press must leave a note.manual_fetch_requested row."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(None),
    )

    body = b""
    response = client.post(
        "/zoom/encounter/777/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 404
    entry = next(c for c in calls if c["event_type"] == "note.manual_fetch_requested")
    assert entry["success"] is True
    assert entry["openemr_encounter_number"] == "777"


def test_fetch_zoom_note_audits_db_error_on_lookup(client, app, monkeypatch):
    """G-M2: DB error during encounter lookup → reason=db_error."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_raising_engine(RuntimeError("connection refused")),
    )

    body = b""
    response = client.post(
        "/zoom/encounter/600/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 500
    failed = next(c for c in calls if c["event_type"] == "note.manual_fetch_failed")
    assert failed["success"] is False
    assert failed["openemr_encounter_number"] == "600"
    assert failed["detail"] == {"reason": "db_error"}
    assert "connection refused" in failed["error_message"]


def test_fetch_zoom_note_audits_not_zoom_encounter(client, app, monkeypatch):
    """G-M3: no row in form_encounter → reason=not_zoom_encounter."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(None),
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555100/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 404
    failed = next(c for c in calls if c["event_type"] == "note.manual_fetch_failed")
    assert failed["openemr_encounter_number"] == "555100"
    assert failed["detail"] == {"reason": "not_zoom_encounter"}


def test_fetch_zoom_note_audits_malformed_external_id(client, app, monkeypatch):
    """G-M4: external_id that won't parse to int → reason=malformed_external_id."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_abc")
        ),
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555101/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 500
    failed = next(c for c in calls if c["event_type"] == "note.manual_fetch_failed")
    assert failed["detail"] == {"reason": "malformed_external_id"}
    assert failed["openemr_provider_id"] == "10"
    assert failed["openemr_patient_id"] == "1"


def test_fetch_zoom_note_audits_no_meeting_record(client, app, monkeypatch):
    """G-M5: encounter row OK but no MeetingRecord in DB."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=7, provider_id=42, external_id="zoom_eid_888")
        ),
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555102/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 404
    failed = next(c for c in calls if c["event_type"] == "note.manual_fetch_failed")
    assert failed["detail"] == {"reason": "no_meeting_record"}
    assert failed["openemr_appointment_id"] == "888"
    assert failed["openemr_provider_id"] == "42"
    assert failed["openemr_patient_id"] == "7"


def test_fetch_zoom_note_audits_no_note_id(client, app, monkeypatch):
    """G-M6: MeetingRecord exists but no ClinicalNoteRecord."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_without_note("acct-no-note")

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555103/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 404
    failed = next(c for c in calls if c["event_type"] == "note.manual_fetch_failed")
    assert failed["detail"] == {"reason": "no_note_id"}
    assert failed["zoom_account_id"] == "acct-no-note"
    assert failed["zoom_meeting_id"] == "meeting-acct-no-note"


def test_fetch_zoom_note_audits_account_inactive(client, app, monkeypatch):
    """G-M7: account exists in MeetingRecord but is_active=False."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account, _ = _create_meeting_with_note("acct-inactive")
        account.is_active = False
        db.session.commit()

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555104/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 404
    failed = next(c for c in calls if c["event_type"] == "note.manual_fetch_failed")
    assert failed["detail"] == {"reason": "account_inactive"}
    assert failed["zoom_account_id"] == "acct-inactive"
    assert failed["zoom_note_id"] == "note-acct-inactive"


def test_fetch_zoom_note_audits_zoom_api_exception(client, app, monkeypatch):
    """G-M8: Zoom API raises → note.fetch_error with trigger=manual_fetch."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-api-err")

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )

    def boom(_account, _note_id):
        raise RuntimeError("zoom unavailable")

    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.get_zoom_clinical_note", boom)

    body = b""
    response = client.post(
        "/zoom/encounter/555105/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 502
    fetch_err = next(c for c in calls if c["event_type"] == "note.fetch_error")
    assert fetch_err["success"] is False
    assert fetch_err["zoom_account_id"] == "acct-api-err"
    assert fetch_err["zoom_note_id"] == "note-acct-api-err"
    assert fetch_err["detail"] == {"trigger": "manual_fetch"}
    assert "zoom unavailable" in fetch_err["error_message"]


def test_fetch_zoom_note_audits_content_empty_when_note_none(client, app, monkeypatch):
    """G-M9: get_zoom_clinical_note returns None → note.content_empty audit; placeholder writeback preserved."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-note-none")

    calls = []
    write_args = {}
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_zoom_clinical_note",
        lambda *_: None,
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_provider_username",
        lambda *_: "provider",
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.write_note_to_encounter",
        lambda **kwargs: write_args.update(kwargs) or True,
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555106/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    empty = next(c for c in calls if c["event_type"] == "note.content_empty")
    assert empty["detail"] == {"trigger": "manual_fetch", "note_none": True, "content_length": 0}
    # Preserve current placeholder behavior
    assert write_args["note_content"] == "Note Content Missing"
    assert write_args["note_title"] == "Note Title Missing"


def test_fetch_zoom_note_audits_content_empty_string(client, app, monkeypatch):
    """G-M9: note_content == '' triggers note.content_empty; writeback still called with empty body."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-empty")

    calls = []
    write_args = {}
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_zoom_clinical_note",
        lambda *_: {"note_title": "Title", "note_content": ""},
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_provider_username",
        lambda *_: "p",
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.write_note_to_encounter",
        lambda **kwargs: write_args.update(kwargs) or True,
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555107/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    empty = next(c for c in calls if c["event_type"] == "note.content_empty")
    assert empty["detail"] == {"trigger": "manual_fetch", "note_none": False, "content_length": 0}
    assert write_args["note_content"] == ""

    written = next(c for c in calls if c["event_type"] == "note.written")
    assert written["detail"] == {"trigger": "manual_fetch", "content_blank": True}


def test_fetch_zoom_note_audits_content_empty_whitespace(client, app, monkeypatch):
    """G-M9: note_content == '\\n   \\n' counts as blank — the exact case Josh flagged."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-ws")

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_zoom_clinical_note",
        lambda *_: {"note_title": "Title", "note_content": "\n   \n"},
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_provider_username",
        lambda *_: "p",
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.write_note_to_encounter",
        lambda **kwargs: True,
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555108/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    empty = next(c for c in calls if c["event_type"] == "note.content_empty")
    assert empty["detail"]["note_none"] is False
    assert empty["detail"]["content_length"] == 5


def test_fetch_zoom_note_audits_written_on_success(client, app, monkeypatch):
    """G-M10: happy path emits note.written with trigger=manual_fetch and content_blank=False."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-ok")

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_zoom_clinical_note",
        lambda *_: {"note_title": "Title", "note_content": "Subjective\nDoing well"},
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_provider_username",
        lambda *_: "p",
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.write_note_to_encounter",
        lambda **kwargs: True,
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555110/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    written = next(c for c in calls if c["event_type"] == "note.written")
    assert written["success"] is True
    assert written["zoom_account_id"] == "acct-ok"
    assert written["zoom_note_id"] == "note-acct-ok"
    assert written["openemr_appointment_id"] == "999"
    assert written["openemr_encounter_number"] == "555110"
    assert written["detail"] == {"trigger": "manual_fetch", "content_blank": False}
    # And the entry audit fired
    assert any(c["event_type"] == "note.manual_fetch_requested" for c in calls)


def test_fetch_zoom_note_audits_write_failed(client, app, monkeypatch):
    """G-M10: write_note_to_encounter returns False → note.write_failed with trigger=manual_fetch."""
    app.config["OPENEMR_FLASK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _create_meeting_with_note("acct-write-fail")

    calls = []
    _patch_manual_fetch_audit(monkeypatch, calls)
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_openemr_db_engine",
        lambda: _fake_encounter_engine(
            SimpleNamespace(pid=1, provider_id=10, external_id="zoom_eid_999")
        ),
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_zoom_clinical_note",
        lambda *_: {"note_title": "Title", "note_content": "Subjective\nSomething"},
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.get_provider_username",
        lambda *_: "p",
    )
    monkeypatch.setattr(
        "app.blueprints.zoom.zoom_routes.write_note_to_encounter",
        lambda **_: False,
    )

    body = b""
    response = client.post(
        "/zoom/encounter/555109/fetch_zoom_note",
        data=body,
        headers={"X-Zoomly-Signature": _openemr_signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 500
    failed = next(c for c in calls if c["event_type"] == "note.write_failed")
    assert failed["success"] is False
    assert failed["zoom_account_id"] == "acct-write-fail"
    assert failed["detail"] == {"trigger": "manual_fetch", "content_blank": False}
    assert failed["error_message"] == "OpenEMR note write failed"
