"""Short-lived cache mapping outbound calls to OpenEMR patient IDs.

Populated by the initiate-call route after ZCC accepts the request.
Keyed by (zoom_account_id, zcc_user_id): the agent's ZCC user ID is the
only value guaranteed to appear on both sides — as `mapping.zcc_user_id`
at call initiation and as `recipient_id` in the ReceiveCommunication3
screen-pop event. ZCC does not echo EpicCallID or PhoneSystemCallID back
in ReceiveCommunication3 (confirmed: PhoneSystemCallID is null in ZCC's
InitiateCall response for our configuration).

One entry per agent per account. Last-write wins for concurrent calls,
which is acceptable — agents in a clinical CTI context handle one call
at a time.
"""

import time
from threading import Lock

from .constants import EPIC_OUTBOUND_CALL_CACHE_TTL_SECONDS


# (zoom_account_id, zcc_user_id) -> (openemr_patient_id, expires_at)
_cache: dict[tuple[str, str], tuple[str, float]] = {}
_lock = Lock()


def _sweep_expired(now: float) -> None:
    if len(_cache) < 1000:
        return
    for key in [k for k, (_, exp) in _cache.items() if exp <= now]:
        _cache.pop(key, None)


def store_outbound_call(
    zoom_account_id: str,
    zcc_user_id: str,
    openemr_patient_id: str,
) -> None:
    """Cache the patient ID for an outbound call so ReceiveCommunication3 can pop it."""
    if not zcc_user_id or not openemr_patient_id:
        return
    now = time.time()
    with _lock:
        _sweep_expired(now)
        _cache[(zoom_account_id, zcc_user_id)] = (
            openemr_patient_id,
            now + EPIC_OUTBOUND_CALL_CACHE_TTL_SECONDS,
        )


def get_outbound_call(zoom_account_id: str, zcc_user_id: str) -> str | None:
    """Return the OpenEMR patient ID for an agent's most recent outbound call."""
    if not zcc_user_id:
        return None
    now = time.time()
    with _lock:
        record = _cache.get((zoom_account_id, zcc_user_id))
        if not record:
            return None
        patient_id, expires_at = record
        if expires_at <= now:
            _cache.pop((zoom_account_id, zcc_user_id), None)
            return None
    return patient_id
