"""
Auth for the Veradigm external appointment surface.

Two contexts share the /veradigm data endpoints:
  - EHR launch: the OpenEMR nav icon opens a ZoomBridge-HMAC-signed /veradigm/launch
    URL (proof the user is logged into the EHR). We verify the signature, then mint a
    short-lived `veradigm_session` cookie scoped to that provider + account.
  - Admin: the per-account config tab uses the existing admin JWT.

Data endpoints accept the cookie OR the admin JWT; neither -> 401.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone, timedelta

import jwt
from flask import current_app, request

from app.blueprints.auth.auth_helpers import verify_jwt_cookie_or_header

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "veradigm_session"
SESSION_TTL_SECONDS = 3600          # cookie lifetime after an EHR launch
LAUNCH_MAX_AGE_SECONDS = 300        # signed launch URL freshness window


def _openemr_secret() -> str:
    return current_app.config.get("OPENEMR_FLASK_SECRET", "") or ""


def _session_secret() -> str:
    return current_app.config.get("SECRET_KEY", "") or ""


def launch_signature(openemr_user_id: str, ts: str) -> str:
    """HMAC-SHA256 over the canonical launch string, matching the PHP nav helper."""
    canonical = f"{openemr_user_id}:{ts}".encode("utf-8")
    return hmac.new(_openemr_secret().encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def verify_launch_signature(openemr_user_id: str, ts: str, sig: str) -> bool:
    """Verify the signed launch URL params and their freshness."""
    if not (openemr_user_id and ts and sig):
        return False
    secret = _openemr_secret()
    if not secret:
        logger.error("veradigm | OPENEMR_FLASK_SECRET not configured")
        return False
    if not hmac.compare_digest(launch_signature(openemr_user_id, ts), sig):
        return False
    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return False
    age = datetime.now(timezone.utc).timestamp() - ts_int
    return -60 <= age <= LAUNCH_MAX_AGE_SECONDS  # small negative tolerance for clock skew


def mint_session_token(provider_id: str, account_id: str) -> str:
    """Mint the short-lived veradigm_session JWT (HS256, SECRET_KEY)."""
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "ctx": "veradigm",
            "provider_id": str(provider_id),
            "account_id": str(account_id),
            "iat": now,
            "exp": now + timedelta(seconds=SESSION_TTL_SECONDS),
        },
        _session_secret(),
        algorithm="HS256",
    )


def decode_session_token(token: str) -> dict | None:
    """Decode/validate the veradigm_session cookie; None if invalid/expired."""
    secret = _session_secret()
    if not secret or not token:
        return None
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
    if claims.get("ctx") != "veradigm":
        return None
    return claims


def resolve_context() -> dict | None:
    """
    Resolve the caller's context for a /veradigm data endpoint.

    The admin app and the external EHR page share this Flask origin, so a browser
    that is logged into the admin console carries the `admin_token` cookie on the
    EHR page too. To disambiguate:

      - The admin config tab authenticates with an ``Authorization: Bearer`` header
        (added by the admin axios client). Presence of that header => admin.
      - The external EHR page sends NO bearer header — only the `veradigm_session`
        cookie set by /veradigm/launch. So when there is no bearer header, a valid
        session cookie means EHR context (even if an admin_token cookie is also
        present).

    Returns:
      {"context": "admin"}                                   — valid admin JWT
      {"context": "ehr", "provider_id": .., "account_id": ..} — valid session cookie
      None                                                    — neither
    """
    has_bearer = request.headers.get("Authorization", "").startswith("Bearer ")

    # EHR page: no admin bearer header, but a valid session cookie.
    if not has_bearer:
        claims = decode_session_token(request.cookies.get(SESSION_COOKIE_NAME, ""))
        if claims:
            return {
                "context": "ehr",
                "provider_id": claims["provider_id"],
                "account_id": claims["account_id"],
            }

    # Admin: valid admin JWT (bearer header or admin_token cookie).
    if verify_jwt_cookie_or_header() is None:
        return {"context": "admin"}

    return None
