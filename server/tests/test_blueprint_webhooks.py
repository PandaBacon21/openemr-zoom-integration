import hashlib
import hmac
import json
from types import SimpleNamespace


OPENEMR_APPOINTMENT_PAYLOAD = {
    "event": "appointment.set",
    "eid": 999,
    "pid": 1,
    "provider_id": 10,
    "category_id": 27,
    "appointment_date": "20260420",
    "appointment_time": "10:00",
    "appt_status": "^",
    "facility_id": 1,
    "comments": "Test appointment",
    "fired_at": "2026-04-19T14:00:00+00:00",
}

OPENEMR_APPOINTMENT_DELETE_PAYLOAD = {
    "event": "appointment.deleted",
    "eid": 999,
    "fired_at": "2026-04-19T14:05:00+00:00",
}


def _body(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body.strip(), hashlib.sha256).hexdigest()


def _create_zoom_account(account_id: str):
    from app.extensions import db
    from app.models import ZoomAccount

    account = ZoomAccount(
        account_id=account_id,
        client_id=f"client-{account_id}",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id=f"openemr-{account_id}",
        private_key_path=f"/tmp/{account_id}/private.pem",
        kid=f"zoomly-{account_id}",
        timezone="America/Denver",
        is_active=True,
    )
    db.session.add(account)
    db.session.commit()
    return account


def _create_meeting_record(account_id: str, *, meeting_id: str = "existing-123", eid: str = "999"):
    from app.extensions import db
    from app.models import MeetingRecord

    account = _create_zoom_account(account_id)
    record = MeetingRecord(
        zoom_account_id=account.id,
        zoom_meeting_id=meeting_id,
        zoom_start_url=f"https://zoom.example/start/{meeting_id}",
        zoom_join_url=f"https://zoom.example/join/{meeting_id}",
        openemr_appointment_id=eid,
        openemr_provider_id="10",
        openemr_appt_status="^",
        status="created",
    )
    db.session.add(record)
    db.session.commit()
    return account, record


def test_verify_signature_helper():
    from app.blueprints.webhooks import _verify_signature

    secret = "test-webhook-secret"
    body = b'{"eid":999}'
    sig = _signature(body, secret)

    assert _verify_signature(body, sig, secret) is True
    assert _verify_signature(body, "bad-signature", secret) is False


def test_openemr_webhook_returns_500_when_secret_missing(client, app):
    app.config["OPENEMR_WEBHOOK_SECRET"] = None
    response = client.post("/webhooks/openemr", data=b"{}", content_type="application/json")
    assert response.status_code == 500
    assert response.get_json() == {"error": "server misconfiguration"}


def test_openemr_webhook_returns_400_when_signature_missing(client, app):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    response = client.post("/webhooks/openemr", data=b"{}", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json() == {"error": "missing signature"}


def test_openemr_webhook_returns_401_when_signature_invalid(client, app):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    response = client.post(
        "/webhooks/openemr",
        data=b"{}",
        content_type="application/json",
        headers={"X-Zoomly-Signature": "invalid"},
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "invalid signature"}


def test_openemr_webhook_returns_400_on_invalid_json(client, app):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    bad_body = b'{"event":'
    response = client.post(
        "/webhooks/openemr",
        data=bad_body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(bad_body, "test-webhook-secret")},
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid JSON"}


def test_openemr_webhook_returns_400_when_eid_missing(client, app):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    payload = dict(OPENEMR_APPOINTMENT_PAYLOAD)
    payload.pop("eid")
    body = _body(payload)

    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "missing required field: eid"}


def test_openemr_webhook_creates_records_for_matching_payload(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account = _create_zoom_account("acct-1")
        account_stub = SimpleNamespace(account_id=account.account_id, id=account.id)

    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda payload: [
            SimpleNamespace(
                zoom_account=account_stub,
                provider_mapping=SimpleNamespace(id=10, openemr_provider_id=10),
                payload=payload,
            )
        ],
    )
    monkeypatch.setattr(
        "app.blueprints.webhooks.create_zoom_meeting",
        lambda match: {
            "meeting_id": "123456789",
            "start_url": "https://zoom.example/start/123456789",
            "join_url": "https://zoom.example/join/123456789",
        },
    )

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["eid"] == 999
    assert len(payload["created"]) == 1
    assert payload["updated"] == []
    assert payload["created"][0]["account_id"] == "acct-1"
    assert payload["created"][0]["zoom_meeting_id"] == "123456789"
    assert payload["created"][0]["zoom_join_url"] == "https://zoom.example/join/123456789"

    with app.app_context():
        from app.models import MeetingPatient, MeetingRecord

        meeting = MeetingRecord.query.filter_by(zoom_meeting_id="123456789").first()
        assert meeting is not None
        assert meeting.openemr_appointment_id == "999"
        assert meeting.openemr_provider_id == "10"
        assert meeting.openemr_appt_status == "^"
        assert meeting.status == "created"

        patient = MeetingPatient.query.filter_by(meeting_record_id=meeting.id).first()
        assert patient is not None
        assert patient.openemr_patient_id == "1"


def test_openemr_webhook_returns_partial_when_one_match_fails(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account_1 = _create_zoom_account("acct-1")
        account_2 = _create_zoom_account("acct-2")
        account_1_stub = SimpleNamespace(account_id=account_1.account_id, id=account_1.id)
        account_2_stub = SimpleNamespace(account_id=account_2.account_id, id=account_2.id)

    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda payload: [
            SimpleNamespace(
                zoom_account=account_1_stub,
                provider_mapping=SimpleNamespace(id=10, openemr_provider_id=10),
                payload=payload,
            ),
            SimpleNamespace(
                zoom_account=account_2_stub,
                provider_mapping=SimpleNamespace(id=11, openemr_provider_id=11),
                payload=payload,
            ),
        ],
    )

    def fake_create_zoom_meeting(match):
        if match.zoom_account.account_id == "acct-2":
            raise RuntimeError("zoom failure")
        return {
            "meeting_id": "m-success",
            "start_url": "https://zoom.example/start/m-success",
            "join_url": "https://zoom.example/join/m-success",
        }

    monkeypatch.setattr("app.blueprints.webhooks.create_zoom_meeting", fake_create_zoom_meeting)

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 207
    payload = response.get_json()
    assert payload["status"] == "partial"
    assert payload["eid"] == 999
    assert len(payload["created"]) == 1
    assert payload["updated"] == []
    assert payload["created"][0]["account_id"] == "acct-1"
    assert len(payload["errors"]) == 1
    assert payload["errors"][0]["account_id"] == "acct-2"


def test_openemr_webhook_returns_500_when_all_matches_fail(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account = _create_zoom_account("acct-err")
        account_stub = SimpleNamespace(account_id=account.account_id, id=account.id)

    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda payload: [
            SimpleNamespace(
                zoom_account=account_stub,
                provider_mapping=SimpleNamespace(id=10, openemr_provider_id=10),
                payload=payload,
            )
        ],
    )
    monkeypatch.setattr(
        "app.blueprints.webhooks.create_zoom_meeting",
        lambda match: (_ for _ in ()).throw(RuntimeError("zoom failure")),
    )

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["eid"] == 999
    assert len(payload["errors"]) == 1
    assert payload["errors"][0]["account_id"] == "acct-err"


def test_openemr_webhook_drops_by_category_payload(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    payload = dict(OPENEMR_APPOINTMENT_PAYLOAD)
    payload["category_id"] = 99

    monkeypatch.setattr("app.blueprints.webhooks.filter_appointment_event", lambda payload: [])

    body = _body(payload)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "dropped", "eid": 999}


def test_openemr_webhook_drops_by_provider_payload(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    payload = dict(OPENEMR_APPOINTMENT_PAYLOAD)
    payload["provider_id"] = 99

    monkeypatch.setattr("app.blueprints.webhooks.filter_appointment_event", lambda payload: [])

    body = _body(payload)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "dropped", "eid": 999}


def test_openemr_webhook_writes_received_and_dropped_audit_events(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    calls = []

    monkeypatch.setattr("app.blueprints.webhooks.filter_appointment_event", lambda payload: [])
    monkeypatch.setattr("app.blueprints.webhooks.write_audit_log", lambda **kwargs: calls.append(kwargs))

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "dropped", "eid": 999}
    assert len(calls) == 2
    assert calls[0]["event_type"] == "appointment.received.appointment.set"
    assert calls[0]["success"] is True
    assert calls[0]["openemr_appointment_id"] == 999
    assert calls[0]["detail"] == {"event": "appointment.set", "appointment_type": 27}
    assert calls[1]["event_type"] == "appointment.dropped"
    assert calls[1]["success"] is True
    assert calls[1]["openemr_appointment_id"] == 999
    assert calls[1]["detail"] == {
        "reason": "no matching provider/type",
        "appointment_type": 27,
    }


def test_openemr_webhook_writes_received_audit_event_for_deleted_payload(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    calls = []
    monkeypatch.setattr("app.blueprints.webhooks.write_audit_log", lambda **kwargs: calls.append(kwargs))

    body = _body(OPENEMR_APPOINTMENT_DELETE_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "no_record", "eid": 999}
    assert len(calls) == 1
    assert calls[0]["event_type"] == "appointment.received.appointment.deleted"
    assert calls[0]["success"] is True
    assert calls[0]["openemr_appointment_id"] == 999
    assert calls[0]["detail"] == {"event": "appointment.deleted", "appointment_type": None}


def test_openemr_webhook_create_writes_openemr_urls_and_audits_success(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account = _create_zoom_account("acct-writeback")
        account_stub = SimpleNamespace(account_id=account.account_id, id=account.id)

    calls = []
    captured = {}
    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda payload: [
            SimpleNamespace(
                zoom_account=account_stub,
                provider_mapping=SimpleNamespace(id=10, openemr_provider_id=10),
                payload=payload,
            )
        ],
    )
    monkeypatch.setattr(
        "app.blueprints.webhooks.create_zoom_meeting",
        lambda match: {
            "meeting_id": "123456789",
            "start_url": "https://zoom.example/start/123456789",
            "join_url": "https://zoom.example/join/123456789",
        },
    )
    monkeypatch.setattr(
        "app.services.openemr.write_zoom_urls_to_appointment",
        lambda eid, start_url, join_url: captured.update(
            {"eid": eid, "start_url": start_url, "join_url": join_url}
        )
        or True,
    )
    monkeypatch.setattr("app.blueprints.webhooks.write_audit_log", lambda **kwargs: calls.append(kwargs))

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert captured == {
        "eid": 999,
        "start_url": "https://zoom.example/start/123456789",
        "join_url": "https://zoom.example/join/123456789",
    }
    event_types = [call["event_type"] for call in calls]
    assert "appointment.received.appointment.set" in event_types
    assert "meeting.created" in event_types
    assert "openemr.url_writeback_success" in event_types


def test_openemr_webhook_create_audits_writeback_failure(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account = _create_zoom_account("acct-writeback-fail")
        account_stub = SimpleNamespace(account_id=account.account_id, id=account.id)

    calls = []
    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda payload: [
            SimpleNamespace(
                zoom_account=account_stub,
                provider_mapping=SimpleNamespace(id=10, openemr_provider_id=10),
                payload=payload,
            )
        ],
    )
    monkeypatch.setattr(
        "app.blueprints.webhooks.create_zoom_meeting",
        lambda match: {
            "meeting_id": "writeback-fail-1",
            "start_url": "https://zoom.example/start/writeback-fail-1",
            "join_url": "https://zoom.example/join/writeback-fail-1",
        },
    )
    monkeypatch.setattr(
        "app.services.openemr.write_zoom_urls_to_appointment",
        lambda eid, start_url, join_url: False,
    )
    monkeypatch.setattr("app.blueprints.webhooks.write_audit_log", lambda **kwargs: calls.append(kwargs))

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    event_types = [call["event_type"] for call in calls]
    assert "openemr.url_writeback_failed" in event_types


def test_openemr_webhook_updates_existing_meeting_when_zoom_meeting_exists(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account, record = _create_meeting_record("acct-update", meeting_id="meet-old", eid="999")
        record_id = record.id
        account_stub = SimpleNamespace(account_id=account.account_id, id=account.id)

    payload = dict(OPENEMR_APPOINTMENT_PAYLOAD)
    payload["appt_status"] = "@"

    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda p: [
            SimpleNamespace(
                zoom_account=account_stub,
                provider_mapping=SimpleNamespace(id=10, openemr_provider_id=10),
                payload=p,
            )
        ],
    )
    monkeypatch.setattr("app.blueprints.webhooks.get_zoom_meeting", lambda account, meeting_id: {"id": meeting_id})
    monkeypatch.setattr("app.blueprints.webhooks.create_zoom_meeting", lambda match: (_ for _ in ()).throw(AssertionError("should not create")))
    monkeypatch.setattr("app.services.zoom.update_zoom_meeting", lambda account, meeting_id, match: None)

    body = _body(payload)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    body_json = response.get_json()
    assert body_json["status"] == "ok"
    assert body_json["created"] == []
    assert len(body_json["updated"]) == 1
    assert body_json["updated"][0]["action"] == "updated"
    assert body_json["updated"][0]["zoom_meeting_id"] == "meet-old"
    assert body_json["updated"][0]["meeting_record_id"] == record_id

    with app.app_context():
        from app.models import MeetingRecord

        refreshed = MeetingRecord.query.get(record_id)
        assert refreshed is not None
        assert refreshed.zoom_meeting_id == "meet-old"
        assert refreshed.openemr_appt_status == "@"


def test_openemr_webhook_recreates_existing_meeting_when_zoom_meeting_missing(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account, record = _create_meeting_record("acct-recreate", meeting_id="meet-old", eid="999")
        record_id = record.id
        account_stub = SimpleNamespace(account_id=account.account_id, id=account.id)

    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda p: [
            SimpleNamespace(
                zoom_account=account_stub,
                provider_mapping=SimpleNamespace(id=10, openemr_provider_id=10),
                payload=p,
            )
        ],
    )
    monkeypatch.setattr("app.blueprints.webhooks.get_zoom_meeting", lambda account, meeting_id: None)
    monkeypatch.setattr(
        "app.blueprints.webhooks.create_zoom_meeting",
        lambda match: {
            "meeting_id": "meet-new",
            "start_url": "https://zoom.example/start/meet-new",
            "join_url": "https://zoom.example/join/meet-new",
        },
    )

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    body_json = response.get_json()
    assert body_json["status"] == "ok"
    assert body_json["created"] == []
    assert len(body_json["updated"]) == 1
    assert body_json["updated"][0]["action"] == "recreated"
    assert body_json["updated"][0]["zoom_meeting_id"] == "meet-new"

    with app.app_context():
        from app.models import MeetingRecord

        refreshed = MeetingRecord.query.get(record_id)
        assert refreshed is not None
        assert refreshed.zoom_meeting_id == "meet-new"


def test_openemr_webhook_delete_returns_no_record_when_meeting_not_found(client, app):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    body = _body(OPENEMR_APPOINTMENT_DELETE_PAYLOAD)

    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "no_record", "eid": 999}


def test_openemr_webhook_delete_removes_zoom_and_db_record(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        account, record = _create_meeting_record("acct-delete", meeting_id="meet-del", eid="999")
        record_id = record.id

    monkeypatch.setattr("app.blueprints.webhooks.delete_zoom_meeting", lambda account, meeting_id: True)

    body = _body(OPENEMR_APPOINTMENT_DELETE_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "deleted",
        "eid": 999,
        "deleted_meetings": ["meet-del"],
    }

    with app.app_context():
        from app.models import MeetingRecord

        refreshed = MeetingRecord.query.get(record_id)
        assert refreshed is None


def test_openemr_webhook_delete_returns_error_when_zoom_delete_fails(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"
    with app.app_context():
        _, record = _create_meeting_record("acct-delete-error", meeting_id="meet-del-err", eid="999")
        record_id = record.id

    monkeypatch.setattr(
        "app.blueprints.webhooks.delete_zoom_meeting",
        lambda account, meeting_id: (_ for _ in ()).throw(RuntimeError("zoom delete failed")),
    )

    body = _body(OPENEMR_APPOINTMENT_DELETE_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 500
    body_json = response.get_json()
    assert body_json["status"] == "error"
    assert body_json["eid"] == 999
    assert body_json["errors"][0]["meeting_id"] == "meet-del-err"

    with app.app_context():
        from app.models import MeetingRecord

        refreshed = MeetingRecord.query.get(record_id)
        assert refreshed is not None
        assert refreshed.status == "error"
