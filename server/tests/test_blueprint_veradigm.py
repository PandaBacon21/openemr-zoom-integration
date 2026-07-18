import hashlib
import hmac

from auth_utils import AUTH_HEADERS, make_auth_headers

from app.extensions import db
from app.models import UserMapping, ZoomAccount

OPENEMR_SECRET = "test-openemr-flask-secret"
SESSION_SECRET = "test-secret-key-0123456789"


# --- fixtures / helpers ----------------------------------------------------

def _configure_secrets(app):
    app.config["OPENEMR_FLASK_SECRET"] = OPENEMR_SECRET
    app.config["SECRET_KEY"] = SESSION_SECRET


def _create_account(account_id: str = "acct-1") -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path="/tmp/private.pem",
        kid=f"zoomly-{account_id}",
        is_active=True,
    )
    db.session.add(account)
    db.session.commit()
    return account


def _create_provider_mapping(account: ZoomAccount, provider_id: str = "10") -> UserMapping:
    mapping = UserMapping(
        zoom_account_id=account.account_id,
        openemr_user_id=provider_id,
        openemr_provider_name="Dr Jane Doe",
        zoom_user_id="u-1",
        zoom_user_email="jane@example.com",
        is_provider=True,
        is_active=True,
    )
    db.session.add(mapping)
    db.session.commit()
    return mapping


def _launch_sig(u: str, ts: str) -> str:
    return hmac.new(
        OPENEMR_SECRET.encode(), f"{u}:{ts}".encode(), hashlib.sha256
    ).hexdigest()


def _openemr_sig(body: bytes) -> str:
    return hmac.new(OPENEMR_SECRET.encode(), body.strip(), hashlib.sha256).hexdigest()


# --- guard -----------------------------------------------------------------

def test_appointments_requires_auth(client):
    resp = client.get("/veradigm/appointments")
    assert resp.status_code == 401


# --- nav-bootstrap ---------------------------------------------------------

def test_nav_bootstrap_requires_signature(app, client):
    _configure_secrets(app)
    resp = client.post("/veradigm/nav-bootstrap", json={"openemr_user_id": "10"})
    assert resp.status_code == 401


def test_nav_bootstrap_reports_provider(app, client):
    _configure_secrets(app)
    with app.app_context():
        account = _create_account()
        _create_provider_mapping(account, "10")

    body = b'{"openemr_user_id": "10"}'
    resp = client.post(
        "/veradigm/nav-bootstrap",
        data=body,
        headers={"Content-Type": "application/json", "X-Zoomly-Signature": _openemr_sig(body)},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_provider"] is True
    assert data["provider_id"] == "10"
    assert data["account_id"] == "acct-1"


def test_nav_bootstrap_non_provider(app, client):
    _configure_secrets(app)
    body = b'{"openemr_user_id": "999"}'
    resp = client.post(
        "/veradigm/nav-bootstrap",
        data=body,
        headers={"Content-Type": "application/json", "X-Zoomly-Signature": _openemr_sig(body)},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_provider"] is False
    assert data["provider_id"] is None


# --- launch ----------------------------------------------------------------

def test_launch_invalid_signature_redirects_to_ehr_login(app, client):
    _configure_secrets(app)
    resp = client.get("/veradigm/launch?u=10&ts=9999999999&sig=bad", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "https://openemr.public"


def test_launch_valid_sets_cookie_and_redirects(app, client):
    _configure_secrets(app)
    with app.app_context():
        account = _create_account()
        _create_provider_mapping(account, "10")

    import time
    ts = str(int(time.time()))
    resp = client.get(
        f"/veradigm/launch?u=10&ts={ts}&sig={_launch_sig('10', ts)}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/healthcare/veradigm/appointments"
    set_cookie = resp.headers.get("Set-Cookie", "")
    assert "veradigm_session=" in set_cookie


# --- appointments (dual context) -------------------------------------------

def test_appointments_admin_requires_account_id(app, client):
    _configure_secrets(app)
    resp = client.get("/veradigm/appointments", headers=AUTH_HEADERS)
    assert resp.status_code == 400


def test_appointments_admin_success(app, client, monkeypatch):
    _configure_secrets(app)
    with app.app_context():
        _create_account()

    sentinel = {"today": "2026-07-16", "appointments": []}
    monkeypatch.setattr(
        "app.blueprints.veradigm.veradigm_routes.build_appointments_response",
        lambda *a, **k: sentinel,
    )
    resp = client.get(
        "/veradigm/appointments?zoom_account_id=acct-1",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.get_json() == sentinel


def test_appointments_ehr_context_uses_cookie(app, client, monkeypatch):
    _configure_secrets(app)
    with app.app_context():
        account = _create_account()
        _create_provider_mapping(account, "10")
        from app.blueprints.veradigm.veradigm_auth import mint_session_token
        token = mint_session_token(provider_id="10", account_id="acct-1")

    captured = {}

    def _fake_build(account_id, mappings, *a, **k):
        captured["account_id"] = account_id
        captured["provider_ids"] = [m.openemr_user_id for m in mappings]
        return {"today": "2026-07-16", "appointments": []}

    monkeypatch.setattr(
        "app.blueprints.veradigm.veradigm_routes.build_appointments_response", _fake_build
    )
    client.set_cookie("veradigm_session", token)
    resp = client.get("/veradigm/appointments")
    assert resp.status_code == 200
    assert captured["account_id"] == "acct-1"
    assert captured["provider_ids"] == ["10"]  # forced to the launching provider


def test_ehr_context_wins_over_admin_cookie(app, client, monkeypatch):
    """Regression: a browser logged into the admin app carries the admin_token
    cookie on the EHR page too. Without an Authorization bearer header, the
    veradigm_session cookie must still resolve to EHR context (not admin, which
    would 400 on the missing zoom_account_id)."""
    _configure_secrets(app)
    with app.app_context():
        account = _create_account()
        _create_provider_mapping(account, "10")
        from app.blueprints.veradigm.veradigm_auth import mint_session_token
        token = mint_session_token(provider_id="10", account_id="acct-1")

    monkeypatch.setattr(
        "app.blueprints.veradigm.veradigm_routes.build_appointments_response",
        lambda account_id, mappings, *a, **k: {"today": "2026-07-16", "appointments": []},
    )
    # Simulate the admin session cookie also being present in the browser.
    admin_token = make_auth_headers()["Authorization"].split(" ", 1)[1]
    client.set_cookie("admin_token", admin_token)
    client.set_cookie("veradigm_session", token)

    resp = client.get("/veradigm/appointments")  # no Authorization header
    assert resp.status_code == 200


# --- meeting mint-or-reuse -------------------------------------------------

def test_create_meeting_admin_success(app, client, monkeypatch):
    _configure_secrets(app)
    with app.app_context():
        _create_account()

    monkeypatch.setattr(
        "app.blueprints.veradigm.veradigm_routes.get_or_create_veradigm_meeting",
        lambda account, eid: {"meeting_id": "123", "start_url": "s", "join_url": "j", "reused": False},
    )
    resp = client.post(
        "/veradigm/appointments/555/meeting?zoom_account_id=acct-1",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.get_json()["meeting_id"] == "123"


def test_create_meeting_maps_error_status(app, client, monkeypatch):
    _configure_secrets(app)
    with app.app_context():
        _create_account()

    monkeypatch.setattr(
        "app.blueprints.veradigm.veradigm_routes.get_or_create_veradigm_meeting",
        lambda account, eid: {"error": "not_veradigm_appointment"},
    )
    resp = client.post(
        "/veradigm/appointments/555/meeting?zoom_account_id=acct-1",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "not_veradigm_appointment"
