from auth_utils import AUTH_HEADERS, INVALID_AUTH_HEADERS


def test_login_returns_jwt_for_valid_password(client):
    response = client.post("/api/auth/login", json={"password": "test-admin-password"})

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body["token"], str)
    assert body["token"]


def test_login_rejects_invalid_password(client):
    response = client.post("/api/auth/login", json={"password": "wrong-password"})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid password"}


def test_login_returns_500_when_auth_not_configured(client, app):
    app.config["CONFIG_JWT_SECRET"] = None

    response = client.post("/api/auth/login", json={"password": "test-admin-password"})

    assert response.status_code == 500
    assert response.get_json() == {"error": "Auth not configured on server"}


def test_verify_accepts_valid_jwt(client):
    response = client.get("/api/auth/verify", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_verify_rejects_missing_jwt(client):
    response = client.get("/api/auth/verify")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Missing token"}


def test_verify_rejects_invalid_jwt(client):
    response = client.get("/api/auth/verify", headers=INVALID_AUTH_HEADERS)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid token"}
