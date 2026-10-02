"""Truthful outcomes for the writes a listener never sees: settings and history.

qc.md F-01. A settings or history file is written dozens of times a session,
from menu handlers, worker threads and close paths, and every one of those
call sites used to either crash on a full disk or swallow the error. Neither
tells the listener anything true: the first loses the action, the second makes
a failed save sound exactly like a successful one.

So the shared writers go through :func:`guarded_write`. It does the write,
tells whoever is listening how it went (:func:`subscribe`), and re-raises a
failure -- so every caller behaves exactly as it did, and the *app* decides
what to say, once, with a Retry and an Open Folder (``quill.ui.persistence_reporting``).

The outcome carries the path and a stable reason code, never the content
being written. wx-free, strict-typed; listeners are called on the writing
thread and must marshal to the UI themselves.
"""

from __future__ import annotations

import errno
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

#: Reason codes, stable for logs; the sentences are for people.
DISK_FULL = "disk_full"
DENIED = "denied"
READ_ONLY = "read_only"
MISSING_FOLDER = "missing_folder"
OTHER = "other"

REASON_SENTENCES: dict[str, str] = {
    DISK_FULL: "The disk is full.",
    DENIED: "Windows did not allow writing there -- the file may be open in "
    "another program, or the folder may be protected.",
    READ_ONLY: "The folder is read only.",
    MISSING_FOLDER: "The folder it lives in is missing.",
    OTHER: "The file could not be written.",
}


def reason_for(error: OSError) -> str:
    """The stable reason code for *error*."""
    code = getattr(error, "errno", None)
    if code == errno.ENOSPC:
        return DISK_FULL
    if code in (errno.EACCES, errno.EPERM) or isinstance(error, PermissionError):
        return DENIED
    if code == errno.EROFS:
        return READ_ONLY
    if code == errno.ENOENT or isinstance(error, FileNotFoundError):
        return MISSING_FOLDER
    return OTHER


@dataclass(frozen=True, slots=True)
class WriteOutcome:
    """How one guarded write went."""

    #: What was being saved, as the listener would name it: "QUILL settings".
    what: str
    path: Path
    ok: bool
    reason: str = ""
    #: Writes the same thing again through the same guard. ``None`` on success.
    retry: Callable[[], None] | None = None

    @property
    def reason_sentence(self) -> str:
        return REASON_SENTENCES.get(self.reason, REASON_SENTENCES[OTHER]) if not self.ok else ""


_listeners: list[Callable[[WriteOutcome], None]] = []
_lock = threading.Lock()


def subscribe(listener: Callable[[WriteOutcome], None]) -> Callable[[], None]:
    """Hear every guarded write's outcome. Returns the unsubscribe."""
    with _lock:
        _listeners.append(listener)

    def unsubscribe() -> None:
        with _lock:
            if listener in _listeners:
                _listeners.remove(listener)

    return unsubscribe


def _notify(outcome: WriteOutcome) -> None:
    with _lock:
        listeners = list(_listeners)
    for listener in listeners:
        try:
            listener(outcome)
        except Exception:  # noqa: BLE001 - a listener must never break a save
            logger.exception("persistence outcome listener failed")


def guarded_write(what: str, path: Path, write: Callable[[], None]) -> None:
    """Run *write*; report the outcome; re-raise ``OSError`` unchanged."""
    try:
        write()
    except OSError as error:
        reason = reason_for(error)
        logger.warning("QUILL-PERSIST-WRITE %s: %s (%s)", what, reason, type(error).__name__)
        _notify(
            WriteOutcome(
                what, path, ok=False, reason=reason, retry=lambda: guarded_write(what, path, write)
            )
        )
        raise
    _notify(WriteOutcome(what, path, ok=True))


__all__ = [
    "DENIED",
    "DISK_FULL",
    "MISSING_FOLDER",
    "OTHER",
    "READ_ONLY",
    "REASON_SENTENCES",
    "WriteOutcome",
    "guarded_write",
    "reason_for",
    "subscribe",
]
