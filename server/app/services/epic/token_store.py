"""Process-local opaque access token store for the Epic-spoof token endpoint.

After Zoom successfully exchanges a signed JWT assertion at /oauth2/token,
we mint an opaque token and store it here with a TTL. Subsequent calls from
Zoom (PatientLookUp, ReceiveCommunication3, Practitioner search) carry the
token in the Authorization header and we resolve it back to a zoom_account_id.

Why process-local + in-memory:
  - Gunicorn runs 1 gevent worker on staging/prod, so all requests for an
    account hit the same process — no need to coordinate across workers.
  - Tokens are short-lived (60min). Restarts force Zoom to re-mint a token
    on the next call, which is the same flow as natural token expiry.
"""

import secrets
import time
from threading import Lock

from .constants import EPIC_TOKEN_TTL_SECONDS


_tokens: dict[str, tuple[str, float]] = {}
_lock = Lock()


def _sweep_expired(now: float) -> None:
    """Lazy sweep called from issue/validate. Bounds memory under steady state."""
    if len(_tokens) < 1000:
        return
    for token in [t for t, (_, exp) in _tokens.items() if exp <= now]:
        _tokens.pop(token, None)


def issue_token(zoom_account_id: str) -> tuple[str, int]:
    """Mint an opaque token bound to a Zoomly account.

    Returns (token, expires_in_seconds) suitable for the OAuth2 token response.
    """
    now = time.time()
    token = secrets.token_urlsafe(32)
    expires_at = now + EPIC_TOKEN_TTL_SECONDS

    with _lock:
        _sweep_expired(now)
        _tokens[token] = (zoom_account_id, expires_at)

    return token, EPIC_TOKEN_TTL_SECONDS


def validate_token(token: str) -> str | None:
    """Resolve a bearer token to its zoom_account_id, or None if invalid/expired."""
    now = time.time()
    with _lock:
        record = _tokens.get(token)
        if not record:
            return None
        account_id, expires_at = record
        if expires_at <= now:
            _tokens.pop(token, None)
            return None
    return account_id


def revoke_all_for_account(zoom_account_id: str) -> int:
    """Drop every token for an account (used when CTI is disabled or the account is deleted).

    Returns the number of tokens revoked.
    """
    with _lock:
        to_drop = [t for t, (acc, _) in _tokens.items() if acc == zoom_account_id]
        for t in to_drop:
            _tokens.pop(t, None)
    return len(to_drop)
