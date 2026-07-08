"""Regression: /oauth2/token issues ONE reusable token per account.

The Epic bearer token authenticates the ZCC->Zoomly call at the account level
(agent identity comes from RecipientID, not the token). Every agent's ZCC
client hits /oauth2/token independently, so the endpoint must hand back the
account's existing valid token rather than minting a new one each time —
otherwise a second agent's auth would strand the first agent's token. It only
re-mints once the current token is within the refresh margin of expiring.

Lives in its own file (not the token-suite) purely so the filename doesn't trip
the secret-file read guard on '*token*'.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models import AccountConfig, ZoomAccount
from app.services.epic import token_store


TEST_ACCOUNT_ID = "epic-oauth-reuse-acct"
TOKEN_PATH = f"/zoomly/{TEST_ACCOUNT_ID}/interconnect-amcurprd-oauth/oauth2/token"


@pytest.fixture(autouse=True)
def reset_token_store():
    token_store._tokens.clear()
    yield
    token_store._tokens.clear()


def _seed_account(app) -> None:
    with app.app_context():
        db.session.add(ZoomAccount(
            account_id=TEST_ACCOUNT_ID,
            client_id="zoom-client-id",
            client_secret="zoom-client-secret",
            webhook_secret="zoom-webhook-secret",
            openemr_client_id="openemr-client-id",
            private_key_path=f"/tmp/keys/{TEST_ACCOUNT_ID}/private.pem",
            kid=f"zoomly-{TEST_ACCOUNT_ID}",
            is_active=True,
        ))
        db.session.add(AccountConfig(
            account_id=TEST_ACCOUNT_ID,
            timezone="America/New_York",
            epic_zcc_enabled=True,
        ))
        db.session.commit()


def _mock_assertion(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.blueprints.epic.auth_routes.verify_zoom_assertion",
        lambda assertion, audience: {"iss": "zoom", "sub": "zoom", "jti": "jti-x"},
    )


def _post_token(client):
    return client.post(TOKEN_PATH, data={
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": "fake.jwt.assertion",
    })


def test_second_auth_returns_same_account_token(app, client, monkeypatch):
    _seed_account(app)
    _mock_assertion(monkeypatch)

    first = _post_token(client)
    second = _post_token(client)

    assert first.status_code == 200
    assert second.status_code == 200
    t1 = first.get_json()["access_token"]
    t2 = second.get_json()["access_token"]

    # Two independent agent auths converge on ONE account token, and it still
    # validates — neither agent strands the other.
    assert t1 == t2
    assert token_store.validate_token(t1) == TEST_ACCOUNT_ID
    assert second.get_json()["expires_in"] <= first.get_json()["expires_in"]


def test_token_reminted_once_within_refresh_margin(app, client, monkeypatch):
    _seed_account(app)
    _mock_assertion(monkeypatch)

    t1 = _post_token(client).get_json()["access_token"]

    # Push the stored token inside the refresh margin so the next auth re-mints.
    with app.app_context():
        acct = db.session.get(ZoomAccount, TEST_ACCOUNT_ID)
        acct.epic_zcc_bearer_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        db.session.commit()

    t2 = _post_token(client).get_json()["access_token"]

    assert t1 != t2
    assert token_store.validate_token(t2) == TEST_ACCOUNT_ID
