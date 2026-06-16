"""Verify Zoom-signed JWT assertions arriving at our Epic-spoof token endpoint.

Zoom POSTs a signed JWT as the `client_assertion` parameter on
`/oauth2/token`. We verify it against Zoom's JWKS (fetched from the `jku`
header, cached per JWKS URL) and validate the standard JWT claims before
minting an opaque access token.
"""

import logging
import time
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import jwt
import requests
from jwt import PyJWKClient

from .constants import (
    EPIC_INBOUND_JWT_ALGS,
    EPIC_JKU_HOST_ALLOWLIST,
    EPIC_JTI_REPLAY_TTL_SECONDS,
    EPIC_JWKS_CACHE_TTL_SECONDS,
    EPIC_ZOOM_FALLBACK_JWKS_URL,
)

logger = logging.getLogger(__name__)


class InvalidAssertionError(Exception):
    """Raised when a Zoom JWT assertion fails any verification step.

    The `reason` carries a short stable code for audit logging and OAuth2
    error response mapping. The message is a human-readable diagnostic.
    """

    def __init__(self, reason: str, message: str = ""):
        super().__init__(message or reason)
        self.reason = reason


# Per-URL JWKS cache. Module-level so all requests share the same cache.
# Safe under Gunicorn's 1-gevent-worker setup; greenlets cooperate, no GIL races.
_jwks_cache: dict[str, tuple[float, Any]] = {}
_jwks_cache_lock = Lock()

# Replay protection: jti → expires_at. Lazy sweep on insert keeps memory bounded
# (the inbound JWT's own `exp` is typically 5min, matching the replay window).
_jti_seen: dict[str, float] = {}
_jti_lock = Lock()


def _jku_host_allowed(jku: str) -> bool:
    """JKU is untrusted input — verify the host is a Zoom domain before fetching."""
    try:
        host = urlparse(jku).hostname or ""
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in EPIC_JKU_HOST_ALLOWLIST)


def _fetch_jwks(jku: str) -> Any:
    """Fetch JWKS from `jku`, caching per URL with TTL.

    Returns a PyJWKClient for signing-key lookup by kid. Cache hit returns
    the existing client; miss fetches and replaces.
    """
    now = time.time()
    with _jwks_cache_lock:
        cached = _jwks_cache.get(jku)
        if cached and cached[0] > now:
            return cached[1]

    try:
        # PyJWKClient handles the HTTP fetch + JWK parsing internally.
        # We wrap it so the cache stays per-URL rather than global.
        client = PyJWKClient(jku, cache_keys=False, lifespan=EPIC_JWKS_CACHE_TTL_SECONDS, timeout=10)
        client.get_jwk_set()  # eager fetch so failure surfaces here, not at verify
    except (requests.RequestException, jwt.PyJWKClientError) as e:
        logger.warning(f"epic.inbound_jwt | JWKS fetch failed for jku={jku}: {e}")
        raise InvalidAssertionError("jwks_fetch_failed", str(e))

    with _jwks_cache_lock:
        _jwks_cache[jku] = (now + EPIC_JWKS_CACHE_TTL_SECONDS, client)
    return client


def _claim_jti(jti: str, exp: int) -> None:
    """Reject if jti already seen within the replay window; otherwise record it."""
    now = time.time()
    expires_at = min(float(exp), now + EPIC_JTI_REPLAY_TTL_SECONDS)
    with _jti_lock:
        # Lazy sweep — drop any entries that have already passed their expiry.
        if len(_jti_seen) > 1000:
            for stale in [k for k, v in _jti_seen.items() if v <= now]:
                _jti_seen.pop(stale, None)
        if jti in _jti_seen and _jti_seen[jti] > now:
            raise InvalidAssertionError("replay", f"jti {jti} already seen")
        _jti_seen[jti] = expires_at


def verify_zoom_assertion(token: str, expected_audience: str) -> dict:
    """Verify a Zoom-signed client_assertion JWT and return its claims.

    Steps:
      1. Parse header without verification to extract `kid`, `alg`, `jku`.
      2. Reject unsupported algs and untrusted JKU hosts (defense against
         attacker-controlled JKU pointing at their own JWKS).
      3. Fetch + cache JWKS at `jku`.
      4. Decode + verify signature using the kid-matched key.
      5. Validate `iss == sub`, `aud == expected_audience`, `exp` in the future.
      6. Check `jti` against the in-process replay set.

    Raises InvalidAssertionError(reason=...) on any failure; the `reason`
    code is used both for the OAuth2 error response and for audit detail.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as e:
        raise InvalidAssertionError("bad_request", f"malformed JWT header: {e}")
    logger.info(header)
    
    kid = header.get("kid")
    alg = header.get("alg")
    jku = header.get("jku")

    logger.info(f"epic.inbound_jwt | assertion header | kid={kid!r} alg={alg!r} jku={jku!r}")

    if not kid:
        raise InvalidAssertionError("kid_missing", "JWT header lacks kid")
    if alg not in EPIC_INBOUND_JWT_ALGS:
        raise InvalidAssertionError("alg_unsupported", f"alg={alg!r} not in {EPIC_INBOUND_JWT_ALGS}")
    if not jku:
        jku = EPIC_ZOOM_FALLBACK_JWKS_URL
    if not _jku_host_allowed(jku):
        raise InvalidAssertionError("jku_untrusted", f"jku host not in allowlist: {jku}")

    jwks_client = _fetch_jwks(jku)

    try:
        signing_key = jwks_client.get_signing_key(kid).key
    except jwt.PyJWKClientError as e:
        raise InvalidAssertionError("bad_signature", f"kid {kid} not in JWKS: {e}")

    try:
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=list(EPIC_INBOUND_JWT_ALGS),
            audience=expected_audience,
            options={"require": ["iss", "sub", "aud", "exp", "jti"]},
        )
    except jwt.ExpiredSignatureError:
        raise InvalidAssertionError("expired", "JWT exp is in the past")
    except jwt.InvalidAudienceError:
        raise InvalidAssertionError("aud_mismatch", f"aud != {expected_audience}")
    except jwt.InvalidSignatureError as e:
        raise InvalidAssertionError("bad_signature", str(e))
    except jwt.MissingRequiredClaimError as e:
        raise InvalidAssertionError("bad_request", f"missing required claim: {e}")
    except jwt.InvalidTokenError as e:
        raise InvalidAssertionError("bad_signature", str(e))

    if claims["iss"] != claims["sub"]:
        raise InvalidAssertionError("iss_sub_mismatch", f"iss={claims['iss']!r} != sub={claims['sub']!r}")

    _claim_jti(claims["jti"], claims["exp"])

    return claims
