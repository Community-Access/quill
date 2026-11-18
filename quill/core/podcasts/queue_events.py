"""Tell the app when an episode joins the Play Queue.

Episodes reach the queue from eighteen places (a menu, Auto-Queue, a lineup,
a watched folder, the AI, a notification...). Download Queued Episodes has to
hear about every one, so the queue operations themselves call :func:`queued`
and the app listens once, rather than each caller remembering to ask. Before
2026-11-18 a queued episode was only fetched at the show's next feed refresh,
so a streaming listener's queue could reach an episode before it had arrived
(Chris Nova).

One listener per process: the one Cast library. wx-free, strict-typed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

_log = logging.getLogger(__name__)
_listener: Callable[[str, str], None] | None = None


def set_listener(listener: Callable[[str, str], None] | None) -> None:
    """Called with ``(show_id, episode_guid)`` each time an episode is queued."""
    global _listener
    _listener = listener


def queued(show_id: str, episode_guid: str) -> None:
    """An episode joined the queue. Never raises: queueing must not fail on it."""
    listener = _listener
    if listener is None:
        return
    try:
        listener(show_id, episode_guid)
    except Exception:  # noqa: BLE001 - a listener problem is logged, not raised
        _log.exception("The queued-episode listener failed")
