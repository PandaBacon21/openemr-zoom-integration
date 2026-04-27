from app.extensions import db
from app.models import ZoomAccount


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


def test_get_users_returns_500_when_api_key_not_configured(client, app):
    app.config["API_KEY"] = None

    response = client.get("/zoom/users")

    assert response.status_code == 500
    assert response.get_json() == {"error": "API_KEY not configured on server"}


def test_get_users_returns_401_for_invalid_api_key(client, app):
    app.config["API_KEY"] = "expected-key"

    response = client.get("/zoom/users", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid or missing API key"}


def test_get_users_requires_zoom_account_id(client, app):
    app.config["API_KEY"] = "expected-key"

    response = client.get("/zoom/users", headers={"X-API-Key": "expected-key"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "zoom_account_id query parameter is required"}


def test_get_users_returns_404_for_unknown_account(client, app):
    app.config["API_KEY"] = "expected-key"

    response = client.get(
        "/zoom/users",
        headers={"X-API-Key": "expected-key"},
        query_string={"zoom_account_id": "missing-account"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "No active registration found for account missing-account"}


def test_get_users_returns_404_for_inactive_account(client, app):
    app.config["API_KEY"] = "expected-key"

    with app.app_context():
        _create_account("acct-1", is_active=False)

    response = client.get(
        "/zoom/users",
        headers={"X-API-Key": "expected-key"},
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "No active registration found for account acct-1"}


def test_get_users_success_returns_user_list(client, app, monkeypatch):
    app.config["API_KEY"] = "expected-key"

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
        headers={"X-API-Key": "expected-key"},
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
    app.config["API_KEY"] = "expected-key"

    with app.app_context():
        _create_account("acct-1", is_active=True)

    def fake_get_zoom_users(account, search=None):
        raise RuntimeError("zoom unavailable")

    monkeypatch.setattr("app.blueprints.zoom.zoom_routes.get_zoom_users", fake_get_zoom_users)

    response = client.get(
        "/zoom/users",
        headers={"X-API-Key": "expected-key"},
        query_string={"zoom_account_id": "acct-1"},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "zoom unavailable"}
