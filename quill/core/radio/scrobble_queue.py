"""Songs waiting to be scrobbled, kept on disk until a service takes them.

A scrobble that fails because the internet dropped, or because last.fm was
busy, is not lost: it waits here, one list per service, and is tried again
later. Three limits keep the list honest:

* **A cap per service** (:data:`MAX_PER_SERVICE`). A computer offline for a
  month keeps the newest songs, not every song since.
* **An age limit** (:data:`MAX_AGE_SECONDS`). last.fm ignores a scrobble more
  than two weeks old, so there is no point keeping one.
* **A growing wait between tries** (:func:`retry_delay`), from one minute up
  to an hour, so a service that is down is not hammered.

What each service said decides what happens to a batch (:class:`Outcome`):
taken, try again later, sign in again, or give up on that batch because the
service will never accept it as written.

The thread rule: the queue is changed from a worker (after a submission) and
from the UI thread (when a song is heard), so every change takes the lock.
Writes are atomic (``write_json_atomic``). The idea of queueing and retrying
comes from BlindRadio by serrebidev (MIT); no code was copied. wx-free,
strict-typed.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from quill.core.radio.scrobble_tracker import Listen
from quill.core.storage import write_json_atomic

_log = logging.getLogger(__name__)

_FILE_NAME = "radio_scrobble_queue.json"

MAX_PER_SERVICE = 500
MAX_AGE_SECONDS = 14 * 24 * 60 * 60
#: Songs sent in one request. last.fm takes at most 50.
BATCH_SIZE = 50

FIRST_RETRY_SECONDS = 60.0
MAX_RETRY_SECONDS = 60.0 * 60.0

#: What a submission can come back as.
SENT = "sent"
RETRY = "retry"
SIGN_IN = "sign_in"
REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class Outcome:
    """What a service said about one batch."""

    kind: str
    #: Plain words for the log, or for the listener when they must act.
    detail: str = ""


def retry_delay(failures: int) -> float:
    """Seconds to wait after *failures* failed tries in a row (pure)."""
    if failures <= 0:
        return 0.0
    return float(min(MAX_RETRY_SECONDS, FIRST_RETRY_SECONDS * (2 ** (failures - 1))))


class ScrobbleQueue:
    """One waiting list per service, saved under *data_dir*."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._path = data_dir / _FILE_NAME if data_dir is not None else None
        self._lock = threading.Lock()
        self._pending: dict[str, list[Listen]] = {}
        self._failures: dict[str, int] = {}
        self._next_try: dict[str, float] = {}
        #: Services waiting on the listener to sign in again.
        self._blocked: set[str] = set()
        self._load()

    # -- persistence ------------------------------------------------------

    def _load(self) -> None:
        if self._path is None or not self._path.is_file():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _log.debug("Scrobble queue unreadable; starting empty", exc_info=True)
            return
        services = raw.get("services") if isinstance(raw, dict) else None
        if not isinstance(services, dict):
            return
        for name, items in services.items():
            if not isinstance(items, list):
                continue
            listens = [found for item in items if (found := Listen.from_dict(item)) is not None]
            if listens:
                self._pending[str(name)] = listens[-MAX_PER_SERVICE:]

    def _save_locked(self) -> None:
        if self._path is None:
            return
        payload = {
            "version": 1,
            "services": {
                name: [listen.to_dict() for listen in items]
                for name, items in self._pending.items()
                if items
            },
        }
        try:
            write_json_atomic(self._path, payload)
        except OSError:
            _log.debug("Could not save the scrobble queue", exc_info=True)

    # -- the queue --------------------------------------------------------

    def add(self, service: str, listen: Listen) -> None:
        with self._lock:
            items = self._pending.setdefault(service, [])
            if listen in items:
                return
            items.append(listen)
            del items[:-MAX_PER_SERVICE]
            self._save_locked()

    def pending(self, service: str) -> list[Listen]:
        with self._lock:
            return list(self._pending.get(service, []))

    def unblock(self, service: str) -> None:
        """The listener signed in again: try that service's songs at once."""
        with self._lock:
            self._blocked.discard(service)
            self._failures.pop(service, None)
            self._next_try.pop(service, None)

    def is_blocked(self, service: str) -> bool:
        with self._lock:
            return service in self._blocked

    def has_due(self, service: str, *, now: float) -> bool:
        """Whether *service* has songs waiting that may be tried now. No disk."""
        with self._lock:
            if service in self._blocked or now < self._next_try.get(service, 0.0):
                return False
            return bool(self._pending.get(service))

    def due_batch(self, service: str, *, now: float) -> list[Listen]:
        """The oldest songs ready to send now, or [] when it is not time yet.

        Songs past :data:`MAX_AGE_SECONDS` are dropped here, unsent.
        """
        with self._lock:
            if service in self._blocked or now < self._next_try.get(service, 0.0):
                return []
            items = self._pending.get(service, [])
            fresh = [item for item in items if now - item.listened_at <= MAX_AGE_SECONDS]
            if len(fresh) != len(items):
                self._pending[service] = fresh
                self._save_locked()
            return list(fresh[:BATCH_SIZE])

    def settle(self, service: str, batch: list[Listen], outcome: Outcome, *, now: float) -> None:
        """Apply what the service said about *batch*."""
        with self._lock:
            items = self._pending.get(service, [])
            if outcome.kind in (SENT, REJECTED):
                self._pending[service] = [item for item in items if item not in batch]
                self._failures.pop(service, None)
                self._next_try.pop(service, None)
                self._save_locked()
                return
            if outcome.kind == SIGN_IN:
                self._blocked.add(service)
                return
            failures = self._failures.get(service, 0) + 1
            self._failures[service] = failures
            self._next_try[service] = now + retry_delay(failures)


__all__ = [
    "BATCH_SIZE",
    "MAX_AGE_SECONDS",
    "MAX_PER_SERVICE",
    "REJECTED",
    "RETRY",
    "SENT",
    "SIGN_IN",
    "Outcome",
    "ScrobbleQueue",
    "retry_delay",
]
