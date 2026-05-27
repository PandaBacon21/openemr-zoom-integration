"""Tests for the POST /config/demo/hydrate endpoint (Sprint 13 / S13-06)."""

import json

from auth_utils import AUTH_HEADERS, INVALID_AUTH_HEADERS
from app.extensions import db
from app.models import AccountConfig, AuditLog, ZoomAccount


def _create_account(app, account_id: str = "acct-hydrate", *, is_active: bool = True) -> ZoomAccount:
    with app.app_context():
        account = ZoomAccount(
            account_id=account_id,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{account_id}/private.pem",
            kid=f"zoomly-{account_id}",
            is_active=is_active,
        )
        db.session.add(account)
        db.session.add(AccountConfig(account_id=account_id, timezone="America/Denver"))
        db.session.commit()
        return account


def test_hydrate_requires_auth(client):
    response = client.post("/config/demo/hydrate", json={"zoom_account_id": "acct-hydrate"})
    assert response.status_code == 401


def test_hydrate_rejects_invalid_jwt(client):
    response = client.post(
        "/config/demo/hydrate",
        json={"zoom_account_id": "acct-hydrate"},
        headers=INVALID_AUTH_HEADERS,
    )
    assert response.status_code == 401


def test_hydrate_returns_400_when_account_id_missing(client):
    response = client.post("/config/demo/hydrate", json={}, headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert "zoom_account_id" in response.get_json()["error"]


def test_hydrate_returns_400_when_body_missing(client):
    # No JSON body at all
    response = client.post("/config/demo/hydrate", headers=AUTH_HEADERS)
    assert response.status_code == 400


def test_hydrate_returns_404_when_account_not_found(client, app):
    response = client.post(
        "/config/demo/hydrate",
        json={"zoom_account_id": "does-not-exist"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert "No active registration found" in response.get_json()["error"]

    # Failure audited
    with app.app_context():
        audits = AuditLog.query.filter_by(event_type="demo.hydrate_request_failed").all()
    assert len(audits) == 1
    assert json.loads(audits[0].detail)["stage"] == "account_lookup"


def test_hydrate_returns_404_when_account_inactive(client, app):
    _create_account(app, "acct-inactive", is_active=False)
    response = client.post(
        "/config/demo/hydrate",
        json={"zoom_account_id": "acct-inactive"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404


def test_hydrate_returns_summary_on_success(client, app, monkeypatch):
    _create_account(app, "acct-hydrate")

    fake_future = {
        "providers_processed": 2,
        "providers_skipped": [],
        "appointments_created": 8,
        "meetings_created": 8,
        "meetings_backfilled": 0,
        "errors": [],
    }
    fake_past = {
        "past_encounters_created": 2,
        "past_encounters_skipped_today": False,
        "past_encounter_skips": [],
        "past_encounter_errors": [],
    }
    monkeypatch.setattr(
        "app.blueprints.config.demo_routes.hydrate_future_meetings",
        lambda account: fake_future,
    )
    monkeypatch.setattr(
        "app.blueprints.config.demo_routes.seed_past_locked_encounters",
        lambda account: fake_past,
    )

    response = client.post(
        "/config/demo/hydrate",
        json={"zoom_account_id": "acct-hydrate"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.get_json() == {**fake_future, **fake_past}


def test_hydrate_passes_account_to_orchestrator(client, app, monkeypatch):
    _create_account(app, "acct-hydrate")
    captured = {}

    def fake_hydrate(account):
        captured["account_id"] = account.account_id
        return {
            "providers_processed": 0, "providers_skipped": [],
            "appointments_created": 0, "meetings_created": 0,
            "meetings_backfilled": 0, "errors": [],
        }
    monkeypatch.setattr("app.blueprints.config.demo_routes.hydrate_future_meetings", fake_hydrate)
    monkeypatch.setattr(
        "app.blueprints.config.demo_routes.seed_past_locked_encounters",
        lambda account: {
            "past_encounters_created": 0, "past_encounters_skipped_today": False,
            "past_encounter_skips": [], "past_encounter_errors": [],
        },
    )

    client.post(
        "/config/demo/hydrate",
        json={"zoom_account_id": "acct-hydrate"},
        headers=AUTH_HEADERS,
    )
    assert captured["account_id"] == "acct-hydrate"


def test_hydrate_returns_500_and_audits_when_orchestrator_raises(client, app, monkeypatch):
    _create_account(app, "acct-hydrate")

    def boom(account):
        raise RuntimeError("OpenEMR DB down")
    monkeypatch.setattr("app.blueprints.config.demo_routes.hydrate_future_meetings", boom)

    response = client.post(
        "/config/demo/hydrate",
        json={"zoom_account_id": "acct-hydrate"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 500
    assert "OpenEMR DB down" in response.get_json()["error"]

    with app.app_context():
        audits = AuditLog.query.filter_by(event_type="demo.hydrate_request_failed").all()
    assert len(audits) == 1
    assert json.loads(audits[0].detail)["stage"] == "orchestrator"
    assert audits[0].error_message == "OpenEMR DB down"
