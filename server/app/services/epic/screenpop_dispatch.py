"""Process-local screen-pop subscriber registry for Epic-ZCC CTI.

ReceiveCommunication3 dispatches navigation events to the OpenEMR user who
owns the call. S11-08 will expose these queues as Server-Sent Events; S11-07
only needs the registry and dispatch semantics.
"""

from queue import Queue
from threading import Lock


_subscribers: dict[str, set[Queue]] = {}
_lock = Lock()


def subscribe(openemr_user_id: str) -> Queue:
    """Register one browser/tab subscriber for an OpenEMR user."""
    key = str(openemr_user_id)
    q: Queue = Queue()
    with _lock:
        _subscribers.setdefault(key, set()).add(q)
    return q


def unsubscribe(openemr_user_id: str, q: Queue) -> None:
    """Remove a subscriber queue for an OpenEMR user."""
    key = str(openemr_user_id)
    with _lock:
        queues = _subscribers.get(key)
        if not queues:
            return
        queues.discard(q)
        if not queues:
            _subscribers.pop(key, None)


def dispatch(openemr_user_id: str, event_dict: dict) -> int:
    """Push an event to every active queue for the OpenEMR user.

    Returns the number of queues that received the event. Each subscriber gets
    a shallow copy so one consumer cannot mutate another consumer's payload.
    """
    key = str(openemr_user_id)
    with _lock:
        queues = list(_subscribers.get(key, set()))

    for q in queues:
        q.put(dict(event_dict))
    return len(queues)
