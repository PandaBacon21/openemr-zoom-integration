import base64
from datetime import date, time
from types import SimpleNamespace

import jwt

from app.extensions import db
from app.models import AccountConfig, ProviderMapping, ZoomAccount
from app.services.ehr_context import set_ehr_context_credentials


def _basic_auth(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"


def _create_ehr_account(app, *, account_id: str = "acct-1") -> ZoomAccount:
    with app.app_context():
        account = ZoomAccount(
            account_id=account_id,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{account_id}/private.pem",
            kid=f"zoomly-{account_id}",
            tenant_id="tenant1234",
            is_active=True,
        )
        set_ehr_context_credentials(account, "ehr-user", "ehr-pass")
        db.session.add(account)
        db.session.add(AccountConfig(account_id=account_id, timezone="America/Denver"))
        db.session.commit()
        return account


def test_get_token_requires_tenant_header(client):
    response = client.get(
        "/rest/auth/gettoken",
        headers={"Authorization": _basic_auth("ehr-user", "ehr-pass")},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Missing X-Tenant-ID header"}


def test_get_token_rejects_invalid_credentials(client, app):
    _create_ehr_account(app)

    response = client.get(
        "/rest/auth/gettoken",
        headers={
            "X-Tenant-ID": "tenant1234",
            "Authorization": _basic_auth("ehr-user", "wrong-pass"),
        },
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid credentials"}


def test_get_token_returns_bearer_jwt(client, app):
    _create_ehr_account(app)

    response = client.get(
        "/rest/auth/gettoken",
        headers={
            "X-Tenant-ID": "tenant1234",
            "Authorization": _basic_auth("ehr-user", "ehr-pass"),
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    decoded = jwt.decode(body["token"], app.config["SECRET_KEY"], algorithms=["HS256"])
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert decoded["sub"] == "tenant1234"
    assert decoded["tid"] == "tenant1234"


def test_get_appointments_returns_mapped_provider_appointments(client, app, monkeypatch):
    _create_ehr_account(app)
    with app.app_context():
        db.session.add(
            ProviderMapping(
                zoom_account_id="acct-1",
                openemr_fhir_id="pract-1",
                openemr_provider_npi="1234567890",
                openemr_provider_id="10",
                openemr_provider_name="Dr Jane Doe",
                zoom_user_id="zoom-user-1",
                zoom_user_email="jane@example.com",
                zoom_user_type=2,
                is_active=True,
            )
        )
        db.session.commit()

    token_response = client.get(
        "/rest/auth/gettoken",
        headers={
            "X-Tenant-ID": "tenant1234",
            "Authorization": _basic_auth("ehr-user", "ehr-pass"),
        },
    )
    bearer = token_response.get_json()["token"]

    captured = {}

    class FakeResult:
        def fetchall(self):
            return [
                SimpleNamespace(
                    pc_eid=391,
                    pc_pid=109,
                    pc_aid=10,
                    pc_eventDate=date(2026, 4, 27),
                    pc_startTime=time(10, 0, 0),
                    pc_endTime=time(10, 30, 0),
                    pc_title="Zoom Telehealth",
                    pc_duration=1800,
                    pc_catname="Telehealth Zoom",
                    fname="Aisha",
                    lname="Johnson",
                    DOB=date(1993, 1, 25),
                    sex="Female",
                )
            ]

    class FakeConn:
        def execute(self, query, params):
            captured["query"] = str(query)
            captured["params"] = params
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(
        "app.blueprints.ehr_context.ehr_context_routes.get_openemr_db_engine",
        lambda: FakeEngine(),
    )

    response = client.post(
        "/rest/openendpoint/service/getAppointments",
        headers={
            "X-Tenant-ID": "tenant1234",
            "Authorization": f"Bearer {bearer}",
        },
        json={"dateTime": "2026-04-27T16:00:00", "zoomUserId": "zoom-user-1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == 200
    assert body["response"] == [
        {
            "appointmentId": "391",
            "providerId": "10",
            "patientId": "109",
            "startTime": "2026-04-27T16:00:00",
            "endTime": "2026-04-27T16:30:00",
            "serviceType": "Zoom Telehealth",
            "name": "Aisha Johnson",
            "dob": "1993-01-25",
            "gender": "Female",
            "appointmentType": "Telehealth Zoom",
        }
    ]
    assert captured["params"]["provider_id"] == 10
