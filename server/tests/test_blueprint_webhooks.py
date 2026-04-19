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


def _body(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body.strip(), hashlib.sha256).hexdigest()


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


def test_openemr_webhook_accepts_matching_payload(client, app, monkeypatch):
    app.config["OPENEMR_WEBHOOK_SECRET"] = "test-webhook-secret"

    monkeypatch.setattr(
        "app.blueprints.webhooks.filter_appointment_event",
        lambda payload: [SimpleNamespace(zoom_account=SimpleNamespace(account_id="acct-1"))],
    )

    body = _body(OPENEMR_APPOINTMENT_PAYLOAD)
    response = client.post(
        "/webhooks/openemr",
        data=body,
        content_type="application/json",
        headers={"X-Zoomly-Signature": _signature(body, "test-webhook-secret")},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "accepted",
        "eid": 999,
        "matched_accounts": ["acct-1"],
    }


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
