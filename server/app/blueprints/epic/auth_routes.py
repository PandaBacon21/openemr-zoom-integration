"""Epic-style OAuth2 token endpoint for the ZCC CTI middleware.

Zoom Contact Center POSTs `grant_type=client_credentials` with a signed JWT
assertion. We verify the assertion against Zoom's JWKS (via `jku`), mint an
opaque access token bound to the path-resolved Zoomly account, and respond
with the OAuth2-shaped JSON Zoom expects.
"""

import logging
from datetime import datetime, timedelta, timezone

from flask import current_app, g, jsonify, request

from app.blueprints.epic import epic_bp
from app.extensions import db
from app.services.audit import write_audit_log
from app.services.epic.constants import EPIC_DEFAULT_SCOPES, EPIC_KEY_VERSION
from app.services.epic.inbound_jwt import InvalidAssertionError, verify_zoom_assertion
from app.services.epic.token_store import issue_token
from app.services.keys import build_single_key_jwks


logger = logging.getLogger(__name__)


# Reasons that should never leak to Zoom as `invalid_grant` because they
# describe a client-id / configuration problem rather than a bad assertion.
_INVALID_CLIENT_REASONS = {"iss_sub_mismatch"}

# Re-mint the account token only once it's within this margin of expiring;
# otherwise a token request returns the account's existing token so all agents
# share one. Small margin keeps the rotation-overlap window tiny.
_TOKEN_REFRESH_MARGIN = timedelta(seconds=60)


def _oauth_error(error: str, reason: str, account_id: str | None, message: str = ""):
    write_audit_log(
        event_type="epic_zcc.token_request_failed",
        success=False,
        zoom_account_id=account_id,
        detail={"reason": reason},
        error_message=message or reason,
    )
    body = {"error": error, "error_description": message or reason}
    return jsonify(body), 400


@epic_bp.route("/oauth2/token", methods=["POST"])
def token(zoom_account_id: str):
    # Flask passes zoom_account_id from the blueprint URL prefix; before_request
    # already resolved it onto g.zoom_account.
    _ = zoom_account_id
    account = g.zoom_account
    grant_type = request.form.get("grant_type")
    assertion_type = request.form.get("client_assertion_type")
    assertion = request.form.get("client_assertion")

    if grant_type != "client_credentials":
        return _oauth_error("unsupported_grant_type", "bad_request", account.account_id,
                            f"grant_type={grant_type!r}")
    if assertion_type != "urn:ietf:params:oauth:client-assertion-type:jwt-bearer":
        return _oauth_error("invalid_request", "bad_request", account.account_id,
                            f"client_assertion_type={assertion_type!r}")
    if not assertion:
        return _oauth_error("invalid_request", "bad_request", account.account_id,
                            "client_assertion missing")

    # Audience is the exact URL Zoom POSTed to, derived from our public base.
    # request.path includes the resolved account_id and Epic slug.
    public_base = current_app.config.get("APP_PUBLIC_URL", "").rstrip("/")
    expected_audience = f"{public_base}{request.path}"

    try:
        claims = verify_zoom_assertion(assertion, expected_audience)
    except InvalidAssertionError as e:
        oauth_err = "invalid_client" if e.reason in _INVALID_CLIENT_REASONS else "invalid_grant"
        return _oauth_error(oauth_err, e.reason, account.account_id, str(e))

    # The bearer token authenticates the ZCC->Zoomly call at the ACCOUNT level
    # (agent identity comes from RecipientID, not the token). So reuse the
    # account's current token instead of minting a fresh one per client — every
    # agent's ZCC client converges on one account token, which also survives a
    # restart via the persisted field + the guard's DB fallback. Only mint when
    # there's no token or it's within the refresh margin of expiring.
    now = datetime.now(timezone.utc)
    existing = account.epic_zcc_bearer_token
    existing_exp = account.epic_zcc_bearer_token_expires_at
    # Stored value can come back timezone-naive depending on the DB/driver;
    # treat a naive timestamp as UTC so the arithmetic never mixes tz-aware and
    # tz-naive datetimes.
    if existing_exp is not None and existing_exp.tzinfo is None:
        existing_exp = existing_exp.replace(tzinfo=timezone.utc)
    reused = bool(
        existing and existing_exp and (existing_exp - now) > _TOKEN_REFRESH_MARGIN
    )
    if reused:
        access_token = existing
        expires_in = int((existing_exp - now).total_seconds())
    else:
        access_token, expires_in = issue_token(account.account_id)
        account.epic_zcc_bearer_token = access_token
        account.epic_zcc_bearer_token_expires_at = now + timedelta(seconds=expires_in)
        db.session.commit()

    write_audit_log(
        event_type="epic_zcc.token_issued",
        success=True,
        zoom_account_id=account.account_id,
        detail={
            "iss": claims.get("iss"),
            "jti": claims.get("jti"),
            "expires_in": expires_in,
            "reused": reused,
        },
    )

    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "scope": EPIC_DEFAULT_SCOPES,
    }), 200


@epic_bp.route("/oauth2/keys/<version>/<kid>", methods=["GET"])
def jwks(zoom_account_id: str, version: str, kid: str):
    """Per-account single-key JWKS endpoint.

    Zoom fetches this URL (registered as "JWT key set URL" in their admin
    portal) to resolve the kid we use when signing outbound assertions to
    ZCC. The version segment is hardcoded to EPIC_KEY_VERSION for Sprint 11;
    a future key-rotation feature will bump it.

    We refuse to return a JWKS unless the path kid matches account.epic_kid
    exactly — that way the endpoint can't be used to enumerate other
    accounts' kids via guessing.
    """
    # Flask passes zoom_account_id from the blueprint URL prefix; before_request
    # already resolved it onto g.zoom_account.
    _ = zoom_account_id
    account = g.zoom_account

    if version != EPIC_KEY_VERSION:
        return jsonify({"error": "not_found"}), 404
    if not account.epic_kid or kid != account.epic_kid:
        return jsonify({"error": "not_found"}), 404

    jwks_doc = build_single_key_jwks(account)
    if not jwks_doc["keys"]:
        # epic_kid was set but the key file is missing — log + 404.
        # build_single_key_jwks already wrote the diagnostic to the app log.
        return jsonify({"error": "not_found"}), 404

    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
    )
    write_audit_log(
        event_type="epic_zcc.jwks_fetched",
        success=True,
        zoom_account_id=account.account_id,
        detail={"client_ip": client_ip, "kid": kid, "version": version},
    )
    return jsonify(jwks_doc), 200
