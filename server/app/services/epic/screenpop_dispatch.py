"""Process-local screen-pop subscriber registry for Epic-ZCC CTI.

ReceiveCommunication3 dispatches navigation events to the OpenEMR user who
owns the call. Subscriptions are scoped by Zoomly account as well as OpenEMR
user so a staff user mapped on multiple ZCC accounts only receives events
from the account backing that browser stream.
"""

from queue import Queue
from threading import Lock


_subscribers: dict[tuple[str, str], set[Queue]] = {}
_lock = Lock()


def _key(zoom_account_id: str, openemr_user_id: str) -> tuple[str, str]:
    return str(zoom_account_id), str(openemr_user_id)


def subscribe(zoom_account_id: str, openemr_user_id: str) -> Queue:
    """Register one browser/tab subscriber for an account-scoped OpenEMR user."""
    key = _key(zoom_account_id, openemr_user_id)
    q: Queue = Queue()
    with _lock:
        _subscribers.setdefault(key, set()).add(q)
    return q


def unsubscribe(zoom_account_id: str, openemr_user_id: str, q: Queue) -> None:
    """Remove a subscriber queue for an account-scoped OpenEMR user."""
    key = _key(zoom_account_id, openemr_user_id)
    with _lock:
        queues = _subscribers.get(key)
        if not queues:
            return
        queues.discard(q)
        if not queues:
            _subscribers.pop(key, None)


def dispatch(zoom_account_id: str, openemr_user_id: str, event_dict: dict) -> int:
    """Push an event to every active queue for the account-scoped OpenEMR user.

    Returns the number of queues that received the event. Each subscriber gets
    a shallow copy so one consumer cannot mutate another consumer's payload.
    """
    key = _key(zoom_account_id, openemr_user_id)
    with _lock:
        queues = list(_subscribers.get(key, set()))

    for q in queues:
        q.put(dict(event_dict))
    return len(queues)
