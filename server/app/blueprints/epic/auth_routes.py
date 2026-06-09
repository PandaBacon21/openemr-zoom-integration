"""Epic-style OAuth2 token endpoint for the ZCC CTI middleware.

Zoom Contact Center POSTs `grant_type=client_credentials` with a signed JWT
assertion. We verify the assertion against Zoom's JWKS (via `jku`), mint an
opaque access token bound to the path-resolved Zoomly account, and respond
with the OAuth2-shaped JSON Zoom expects.
"""

import logging
from flask import current_app, g, jsonify, request

from app.blueprints.epic import epic_bp
from app.services.audit import write_audit_log
from app.services.epic.constants import EPIC_DEFAULT_SCOPES
from app.services.epic.inbound_jwt import InvalidAssertionError, verify_zoom_assertion
from app.services.epic.token_store import issue_token


logger = logging.getLogger(__name__)


# Reasons that should never leak to Zoom as `invalid_grant` because they
# describe a client-id / configuration problem rather than a bad assertion.
_INVALID_CLIENT_REASONS = {"iss_sub_mismatch"}


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
    # zoom_account_id arrives as a path-arg kwarg; the account itself is
    # already resolved + attached to g by the blueprint's before_request.
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

    access_token, expires_in = issue_token(account.account_id)

    write_audit_log(
        event_type="epic_zcc.token_issued",
        success=True,
        zoom_account_id=account.account_id,
        detail={
            "iss": claims.get("iss"),
            "jti": claims.get("jti"),
            "expires_in": expires_in,
        },
    )

    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "scope": EPIC_DEFAULT_SCOPES,
    }), 200
