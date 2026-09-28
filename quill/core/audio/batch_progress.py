"""How far a conversion batch has got, in words a listener can use.

The batch runner reports two things from its worker threads: a file finished,
and how far a running file has got. This turns both into one overall fraction
and one sentence -- "Converting Book.m4b: 42 percent, about 3 minutes left" --
and decides when the sentence is worth sending, so a machine converting seven
files at once does not post fourteen updates a second to the window.

Pure of ``wx`` and thread-safe; the Converter marshals :meth:`update`'s answer
to the UI thread itself.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

#: The fewest seconds between two status updates while files are running.
UPDATE_EVERY_SECONDS = 1.0

#: No time estimate before this much work and this much time: an early guess
#: swings wildly, and a wrong number spoken aloud is worse than none.
_ESTIMATE_AFTER_FRACTION = 0.03
_ESTIMATE_AFTER_SECONDS = 5.0


class BatchProgress:
    """Overall progress of ``total`` files, each weighted equally."""

    def __init__(self, total: int, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._total = max(1, total)
        self._clock = clock
        self._started = clock()
        self._last_sent = float("-inf")
        self._done = 0
        self._running: dict[Path, float] = {}
        self._lock = threading.Lock()

    def file_progress(self, source: Path, fraction: float) -> tuple[str, float] | None:
        """Record one running file's fraction; the update to show, or None if too soon."""
        with self._lock:
            self._running[source] = max(0.0, min(1.0, fraction))
            now = self._clock()
            if now - self._last_sent < UPDATE_EVERY_SECONDS:
                return None
            self._last_sent = now
            return self._describe(now, source), self._overall()

    def file_done(self, source: Path) -> tuple[str, float]:
        """Record a finished file; always returns the update to show."""
        with self._lock:
            self._running.pop(source, None)
            self._done += 1
            now = self._clock()
            self._last_sent = now
            return self._describe(now, source), self._overall()

    def overall(self) -> float:
        with self._lock:
            return self._overall()

    def _overall(self) -> float:
        return min(1.0, (self._done + sum(self._running.values())) / self._total)

    def _describe(self, now: float, source: Path) -> str:
        overall = self._overall()
        percent = int(overall * 100)
        if self._total == 1:
            text = f"Converting {source.name}: {percent} percent"
        else:
            text = f"Converted {self._done} of {self._total}, {percent} percent overall"
        left = self._seconds_left(now, overall)
        if left is not None:
            text += f", {_say_duration(left)} left"
        return text

    def _seconds_left(self, now: float, overall: float) -> float | None:
        elapsed = now - self._started
        if overall < _ESTIMATE_AFTER_FRACTION or elapsed < _ESTIMATE_AFTER_SECONDS:
            return None
        if overall >= 1.0:
            return None
        return elapsed * (1.0 - overall) / overall


def _say_duration(seconds: float) -> str:
    """ "about 3 minutes", "about 1 hour 10 minutes", "less than a minute"."""
    if seconds < 60:
        return "less than a minute"
    minutes = int(round(seconds / 60))
    if minutes < 60:
        return f"about {minutes} minute{'s' if minutes != 1 else ''}"
    hours, rest = divmod(minutes, 60)
    text = f"about {hours} hour{'s' if hours != 1 else ''}"
    if rest:
        text += f" {rest} minute{'s' if rest != 1 else ''}"
    return text
