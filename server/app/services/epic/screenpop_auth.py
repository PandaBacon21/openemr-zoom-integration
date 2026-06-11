"""HMAC helpers for OpenEMR-facing Epic-ZCC screen-pop streams."""

import hashlib
import hmac
import time


class ScreenpopTokenError(Exception):
    """Raised when an SSE stream token cannot be accepted."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def make_screenpop_token(
    secret: str,
    zoom_account_id: str,
    openemr_user_id: str,
    expires_at: int,
) -> str:
    """Return the hex HMAC token for one account-scoped OpenEMR subscriber."""
    payload = _token_payload(zoom_account_id, openemr_user_id, expires_at)
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_screenpop_token(
    secret: str,
    zoom_account_id: str,
    openemr_user_id: str,
    expires_at_raw: str | None,
    token: str | None,
) -> int:
    """Validate a stream token and return its integer expiry timestamp."""
    if not expires_at_raw:
        raise ScreenpopTokenError("missing_expires", "expires is required")
    if not token:
        raise ScreenpopTokenError("missing_token", "token is required")

    try:
        expires_at = int(expires_at_raw)
    except ValueError as e:
        raise ScreenpopTokenError("invalid_expires", "expires must be an integer") from e

    if expires_at <= int(time.time()):
        raise ScreenpopTokenError("expired_token", "token is expired")

    expected = make_screenpop_token(
        secret,
        zoom_account_id,
        openemr_user_id,
        expires_at,
    )
    if not hmac.compare_digest(expected, token):
        raise ScreenpopTokenError("invalid_token", "token is invalid")

    return expires_at


def verify_bridge_signature(raw_body: bytes, received_signature: str, secret: str) -> bool:
    """Verify an OpenEMR PHP -> Flask HMAC signature over the raw request body."""
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body.strip(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_signature)


def _token_payload(
    zoom_account_id: str,
    openemr_user_id: str,
    expires_at: int,
) -> bytes:
    return f"{zoom_account_id}\0{openemr_user_id}\0{expires_at}".encode("utf-8")
