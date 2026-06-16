from auth_utils import AUTH_HEADERS, INVALID_AUTH_HEADERS
from app.extensions import db
from app.models import AccountConfig, ZoomAccount


def _create_account(app, account_id: str, *, epic_zcc_client_id=None, epic_kid=None) -> ZoomAccount:
    with app.app_context():
        account = ZoomAccount(
            account_id=account_id,
            nickname="Test Account",
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{account_id}/private.pem",
            kid=f"zoomly-{account_id}",
            tenant_id=f"t{account_id[-9:]}",
            epic_zcc_client_id=epic_zcc_client_id,
            epic_kid=epic_kid,
            is_active=True,
        )
        db.session.add(account)
        db.session.add(AccountConfig(account_id=account_id, timezone="America/New_York"))
        db.session.commit()
        return account


# ── GET ──────────────────────────────────────────────────────────────────────

def test_get_epic_zcc_requires_auth(client):
    response = client.get("/config/account/acct-1/epic-zcc")
    assert response.status_code == 401


def test_get_epic_zcc_returns_404_for_unknown_account(client):
    response = client.get("/config/account/missing/epic-zcc", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert "No active registration" in response.get_json()["error"]


def test_get_epic_zcc_returns_all_fields(client, app):
    _create_account(app, "acct-1")
    app.config["APP_PUBLIC_URL"] = "https://bridge.example.com"

    response = client.get("/config/account/acct-1/epic-zcc", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.get_json()
    assert body["zoom_account_id"] == "acct-1"
    assert body["epic_zcc_enabled"] is False
    assert body["epic_zcc_connection_name"] is None
    assert body["epic_zcc_backend_url"] is None
    assert body["epic_zcc_background_user_id"] is None
    assert body["epic_zcc_background_user_id_type"] is None
    assert body["epic_zcc_phone_system_id"] is None
    assert body["epic_zcc_phone_system_id_type"] is None
    assert body["epic_zcc_recipient_id_type"] == "Phone"
    assert body["epic_zcc_client_id"] is None
    assert body["epic_kid"] is None
    assert body["instance_url"] == (
        "https://bridge.example.com/zoomly/acct-1/interconnect-amcurprd-oauth"
    )
    assert body["jwks_url"] is None


def test_get_epic_zcc_computes_jwks_url_when_kid_set(client, app):
    _create_account(app, "acct-2", epic_zcc_client_id="uuid-123", epic_kid="ABCD1234")
    app.config["APP_PUBLIC_URL"] = "https://bridge.example.com"

    response = client.get("/config/account/acct-2/epic-zcc", headers=AUTH_HEADERS)

    body = response.get_json()
    assert body["epic_zcc_client_id"] == "uuid-123"
    assert body["epic_kid"] == "ABCD1234"
    assert body["jwks_url"] == (
        "https://bridge.example.com/zoomly/acct-2/interconnect-amcurprd-oauth"
        "/oauth2/keys/1/ABCD1234"
    )


# ── PATCH ─────────────────────────────────────────────────────────────────────

def test_patch_epic_zcc_requires_auth(client):
    response = client.patch("/config/account/acct-1/epic-zcc", json={"epic_zcc_enabled": True})
    assert response.status_code == 401


def test_patch_epic_zcc_requires_json_body(client):
    response = client.patch("/config/account/acct-1/epic-zcc", headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Request body must be JSON"}


def test_patch_epic_zcc_rejects_empty_or_unknown_fields(client):
    response = client.patch(
        "/config/account/acct-1/epic-zcc",
        headers=AUTH_HEADERS,
        json={"unknown_field": "value"},
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "No valid fields provided"}


def test_patch_epic_zcc_returns_404_for_unknown_account(client):
    response = client.patch(
        "/config/account/missing/epic-zcc",
        headers=AUTH_HEADERS,
        json={"epic_zcc_enabled": True},
    )
    assert response.status_code == 404
    assert "No active registration" in response.get_json()["error"]


def test_patch_epic_zcc_updates_config_fields(client, app):
    _create_account(app, "acct-1")

    response = client.patch(
        "/config/account/acct-1/epic-zcc",
        headers=AUTH_HEADERS,
        json={
            "epic_zcc_enabled": True,
            "epic_zcc_connection_name": "Zoomly Demo",
            "epic_zcc_backend_url": "us01cciapi.zoom.us",
            "epic_zcc_phone_system_id": "PS-001",
            "epic_zcc_phone_system_id_type": "Internal",
            "epic_zcc_background_user_id": "admin",
            "epic_zcc_background_user_id_type": "Login",
            "epic_zcc_recipient_id_type": "Phone",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["epic_zcc_enabled"] is True
    assert body["epic_zcc_connection_name"] == "Zoomly Demo"
    assert body["epic_zcc_backend_url"] == "us01cciapi.zoom.us"
    assert body["epic_zcc_phone_system_id"] == "PS-001"
    assert body["epic_zcc_phone_system_id_type"] == "Internal"
    assert body["epic_zcc_background_user_id"] == "admin"
    assert body["epic_zcc_background_user_id_type"] == "Login"
    assert body["epic_zcc_recipient_id_type"] == "Phone"

    # Confirm persisted to DB
    with app.app_context():
        cfg = AccountConfig.query.filter_by(account_id="acct-1").first()
        assert cfg.epic_zcc_enabled is True
        assert cfg.epic_zcc_connection_name == "Zoomly Demo"
        assert cfg.epic_zcc_backend_url == "us01cciapi.zoom.us"


def test_patch_epic_zcc_partial_update_leaves_other_fields_unchanged(client, app):
    _create_account(app, "acct-1")

    # Set an initial value
    client.patch(
        "/config/account/acct-1/epic-zcc",
        headers=AUTH_HEADERS,
        json={"epic_zcc_connection_name": "Original Name"},
    )

    # Patch only backend URL
    response = client.patch(
        "/config/account/acct-1/epic-zcc",
        headers=AUTH_HEADERS,
        json={"epic_zcc_backend_url": "dab-integration.zoomdab.us"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["epic_zcc_connection_name"] == "Original Name"
    assert body["epic_zcc_backend_url"] == "dab-integration.zoomdab.us"


# ── POST initialize ───────────────────────────────────────────────────────────

def test_initialize_epic_zcc_requires_auth(client):
    response = client.post("/config/account/acct-1/epic-zcc/initialize")
    assert response.status_code == 401


def test_initialize_epic_zcc_returns_404_for_unknown_account(client):
    response = client.post(
        "/config/account/missing/epic-zcc/initialize",
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404
    assert "No active registration" in response.get_json()["error"]


def test_initialize_epic_zcc_generates_and_persists_credentials(client, app):
    _create_account(app, "acct-1")

    response = client.post(
        "/config/account/acct-1/epic-zcc/initialize",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["zoom_account_id"] == "acct-1"
    assert body["epic_zcc_client_id"] is not None
    assert len(body["epic_zcc_client_id"]) == 36  # UUID format
    assert body["epic_kid"] is not None
    assert len(body["epic_kid"]) == 32  # secrets.token_hex(16).upper()
    assert body["epic_kid"] == body["epic_kid"].upper()

    # Confirm persisted to DB
    with app.app_context():
        account = ZoomAccount.query.filter_by(account_id="acct-1").first()
        assert account.epic_zcc_client_id == body["epic_zcc_client_id"]
        assert account.epic_kid == body["epic_kid"]


def test_initialize_epic_zcc_regenerates_new_values(client, app):
    _create_account(app, "acct-1", epic_zcc_client_id="old-uuid", epic_kid="OLDKID")

    response = client.post(
        "/config/account/acct-1/epic-zcc/initialize",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["epic_zcc_client_id"] != "old-uuid"
    assert body["epic_kid"] != "OLDKID"
