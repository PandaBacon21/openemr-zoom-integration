"""Short-lived cache of PatientLookUp results keyed by ZCC agent.

PatientLookUp arrives first carrying search criteria; ReceiveCommunication3
(S11-07) arrives shortly after carrying the patient chosen by ZCC's IVR.
This cache bridges the two so ReceiveCommunication3 can drive the screen
pop without re-querying OpenEMR.

The key is (zoom_account_id, agent_user_id) where agent_user_id is the
ZCC user id ZCC sends in PatientLookUp's <UserID> element — the same value
ZCC passes as RecipientID in ReceiveCommunication3.

Process-local + in-memory like token_store. Gunicorn 1-gevent-worker means
all requests for an account hit the same process; a restart drops every
entry, which forces ZCC to redo the lookup — same outcome as natural TTL.
"""

import time
from threading import Lock

from .constants import EPIC_LOOKUP_CACHE_TTL_SECONDS


# (zoom_account_id, agent_user_id) -> (cached_at, expires_at, payload)
_cache: dict[tuple[str, str], tuple[float, float, dict]] = {}
_lock = Lock()


def _sweep_expired(now: float) -> None:
    if len(_cache) < 1000:
        return
    for key in [k for k, (_, exp, _) in _cache.items() if exp <= now]:
        _cache.pop(key, None)


def cache_lookup(
    zoom_account_id: str,
    agent_user_id: str,
    rows: list[dict],
    queried_fields: list[str],
) -> None:
    """Store the lookup result for later retrieval by ReceiveCommunication3.

    `rows` should be the full list returned by patient_search; ReceiveCommunication3
    will pick the row whose PatientID matches what ZCC sends in the routing
    event. `queried_fields` is kept alongside for downstream audit only.

    No-op when agent_user_id is falsy — the lookup still runs and returns
    matches to ZCC, but the screen-pop path won't be reachable for an
    unidentified agent.
    """
    if not agent_user_id:
        return
    now = time.time()
    with _lock:
        _sweep_expired(now)
        _cache[(zoom_account_id, agent_user_id)] = (
            now,
            now + EPIC_LOOKUP_CACHE_TTL_SECONDS,
            {"rows": rows, "queried_fields": queried_fields},
        )


def get_cached_lookup(zoom_account_id: str, agent_user_id: str) -> dict | None:
    """Return the cached lookup for an agent, or None if missing/expired."""
    if not agent_user_id:
        return None
    now = time.time()
    with _lock:
        record = _cache.get((zoom_account_id, agent_user_id))
        if not record:
            return None
        _, expires_at, payload = record
        if expires_at <= now:
            _cache.pop((zoom_account_id, agent_user_id), None)
            return None
    return payload


def invalidate_for_account(zoom_account_id: str) -> int:
    """Drop every cached lookup for an account (used when CTI is disabled)."""
    with _lock:
        to_drop = [k for k in _cache if k[0] == zoom_account_id]
        for k in to_drop:
            _cache.pop(k, None)
    return len(to_drop)
