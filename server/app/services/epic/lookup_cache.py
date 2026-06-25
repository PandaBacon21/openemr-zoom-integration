"""Short-lived cache of PatientLookUp results keyed by caller phone number.

PatientLookUp arrives first carrying search criteria; ReceiveCommunication3
arrives shortly after carrying the patient chosen by ZCC. This cache bridges
the two so ReceiveCommunication3 can drive the screen pop without re-querying
OpenEMR.

The key is (zoom_account_id, phone_digits) where phone_digits is the
normalized 10-digit US number from PatientLookUp's Address.PhoneNumbers — the
same value ZCC echoes back in ReceiveCommunication3's CallerPhoneNumber.

PatientLookUp's UserID/UserIDType are per-account Epic background service
credentials (not per-agent), so they cannot serve as a per-call cache key.

Process-local + in-memory like token_store. Gunicorn 1-gevent-worker means
all requests for an account hit the same process; a restart drops every
entry, which forces ZCC to redo the lookup — same outcome as natural TTL.
"""

import time
from threading import Lock

from .constants import EPIC_LOOKUP_CACHE_TTL_SECONDS


# (zoom_account_id, phone_digits) -> (cached_at, expires_at, payload)
_cache: dict[tuple[str, str], tuple[float, float, dict]] = {}
_lock = Lock()


def _sweep_expired(now: float) -> None:
    if len(_cache) < 1000:
        return
    for key in [k for k, (_, exp, _) in _cache.items() if exp <= now]:
        _cache.pop(key, None)


def cache_lookup(
    zoom_account_id: str,
    phone_digits: str,
    rows: list[dict],
    queried_fields: list[str],
) -> None:
    """Store the lookup result for later retrieval by ReceiveCommunication3.

    `phone_digits` is the normalized 10-digit caller number from
    PatientLookUp's Address.PhoneNumbers. ReceiveCommunication3 uses the same
    number (CallerPhoneNumber) to read the cache, then picks the matching row.
    `queried_fields` is kept alongside for downstream audit only.

    No-op when phone_digits is falsy — the lookup still runs and returns
    matches to ZCC, but the screen-pop path won't be reachable without a key.
    """
    if not phone_digits:
        return
    now = time.time()
    with _lock:
        _sweep_expired(now)
        _cache[(zoom_account_id, phone_digits)] = (
            now,
            now + EPIC_LOOKUP_CACHE_TTL_SECONDS,
            {"rows": rows, "queried_fields": queried_fields},
        )


def get_cached_lookup(zoom_account_id: str, phone_digits: str) -> dict | None:
    """Return the cached lookup for a caller phone, or None if missing/expired."""
    if not phone_digits:
        return None
    now = time.time()
    with _lock:
        record = _cache.get((zoom_account_id, phone_digits))
        if not record:
            return None
        _, expires_at, payload = record
        if expires_at <= now:
            _cache.pop((zoom_account_id, phone_digits), None)
            return None
    return payload


def invalidate_for_account(zoom_account_id: str) -> int:
    """Drop every cached lookup for an account (used when CTI is disabled)."""
    with _lock:
        to_drop = [k for k in _cache if k[0] == zoom_account_id]
        for k in to_drop:
            _cache.pop(k, None)
    return len(to_drop)
