"""Kind to a modest computer: the keep-up watchdog, and models unloaded when idle.

Two of the safeguards in dict.md section 1 (the third, the two-second check,
is :mod:`~quill.core.windows_dictation.speed_check`). The baseline computer is
Windows 10, 4 GB of memory, an older dual-core processor, with a screen reader
running -- and the screen reader has to stay instantly responsive.

* **The keep-up watchdog.** When the microphone's audio waits longer than the
  engine can clear it -- the computer is busy, or on battery saver, or the
  chosen model is simply too big for it -- a downloaded model gives way to
  Moonshine tiny for the rest of the session, and dictation says so once
  rather than falling further and further behind. The saved choice is not
  changed; the next session tries the chosen model again. Only downloaded
  models are watched: the built-in engines are the fast ones already, and
  OpenAI's speed is the network's, not this computer's.
* **Nothing loaded when dictation is off.** Speech models load on the first
  start and stay loaded while dictation is in use, so starting again is
  instant; :data:`IDLE_MINUTES` after the last session ends they are unloaded,
  which gives their memory back (several hundred megabytes for the larger
  models) to a 4 GB computer.

wx-free.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

__all__ = ["BEHIND_SECONDS", "IDLE_MINUTES", "IdleUnloader", "KeepUpWatchdog"]

#: Audio waiting this long means the engine is not keeping up.
BEHIND_SECONDS = 4.0
#: Phrases that took longer to recognise than this many times their length,
#: this many times running, mean the same thing on a phrase engine.
_SLOW_RATIO = 1.5
_SLOW_RUN = 2
#: Minutes after the last session before the models are unloaded.
IDLE_MINUTES = 5


class KeepUpWatchdog:
    """Says when an engine has fallen behind the person speaking."""

    def __init__(self, *, behind_seconds: float = BEHIND_SECONDS) -> None:
        self._behind = behind_seconds
        self._slow = 0

    def note_phrase(self, decode_seconds: float, audio_seconds: float) -> None:
        if audio_seconds <= 0:
            return
        if decode_seconds > audio_seconds * _SLOW_RATIO:
            self._slow += 1
        else:
            self._slow = 0

    def falling_behind(self, backlog_seconds: float) -> bool:
        return backlog_seconds >= self._behind or self._slow >= _SLOW_RUN


class IdleUnloader:
    """Runs *unload* once nothing has used the models for a while.

    :meth:`busy` when a session starts (cancels a pending unload), :meth:`idle`
    when one ends (schedules it). The timer is a daemon thread that does
    nothing but wait, so it costs nothing while it waits and never keeps the
    program open.
    """

    def __init__(self, unload: Callable[[], None], *, minutes: float = IDLE_MINUTES) -> None:
        self._unload = unload
        self._seconds = minutes * 60
        self._lock = threading.Lock()
        self._sessions = 0
        self._timer: threading.Timer | None = None

    def busy(self) -> None:
        with self._lock:
            self._sessions += 1
            self._cancel()

    def idle(self) -> None:
        with self._lock:
            self._sessions = max(0, self._sessions - 1)
            if self._sessions:
                return
            self._cancel()
            timer = threading.Timer(self._seconds, self._fire)
            timer.daemon = True
            timer.name = "dictation-idle-unload"
            self._timer = timer
            timer.start()

    def _cancel(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
            if self._sessions:
                return
        try:
            self._unload()
        except Exception:  # noqa: BLE001 - unloading is a courtesy
            pass
