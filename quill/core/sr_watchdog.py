"""Screen-reader liveness watchdog with a two-strikes rule (wx-free core).

QUILL's screen-reader detection was a one-shot startup probe: if the reader
died mid-session, nothing in QUILL knew. For a blind user that is the
environment collapsing — and the rule for any collapse is **flush unsaved
work first, then act** (the emergency-backup lesson, assessment item 10).

Two strikes are mandatory: JAWS and NVDA restart routinely (updates, crashes,
profile switches), and a single missed check during a restart must not fire
the emergency path. Only two consecutive misses count as death; any sighting
resets the count. Recovery (the reader comes back) is also reported so the UI
can re-probe its announcement backend.

This module is the pure state machine over an injected probe; the UI owns the
timer, the flush, and the announcements.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["CHECK_INTERVAL_SECONDS", "MISSES_BEFORE_DEATH", "SrWatchdog", "WatchdogEvent"]

#: How often the UI timer should call :meth:`SrWatchdog.check`.
CHECK_INTERVAL_SECONDS = 30

#: Consecutive missed checks before the reader is considered gone. Two, so a
#: routine JAWS/NVDA restart (one missed check) never fires the emergency path.
MISSES_BEFORE_DEATH = 2


@dataclass(frozen=True, slots=True)
class WatchdogEvent:
    """The outcome of one check.

    ``kind`` is ``"none"`` (steady state), ``"died"`` (two consecutive misses
    just confirmed the reader is gone — flush now), or ``"recovered"`` (a
    reader is back after a confirmed death). ``reader_name`` names the last
    known reader for died events and the returning reader for recoveries.
    """

    kind: str
    reader_name: str = ""


class SrWatchdog:
    """Two-strikes liveness tracking over an injected detection probe.

    *probe* returns the running screen reader's name, or "" when none is
    detected. The watchdog arms only after it has seen a reader at least once:
    a user running without a screen reader (SAPI self-voice, sighted testing)
    must never trigger emergency behaviour.
    """

    def __init__(self, probe: Callable[[], str]) -> None:
        self._probe = probe
        self._last_seen_name = ""
        self._misses = 0
        self._dead = False

    @property
    def armed(self) -> bool:
        """True once a screen reader has been observed this session."""
        return bool(self._last_seen_name)

    def check(self) -> WatchdogEvent:
        """Run one liveness check; never raises (a probe error counts as a miss)."""
        try:
            name = (self._probe() or "").strip()
        except Exception:  # noqa: BLE001 - a probe failure must not become a crash
            name = ""
        if name and name.lower() != "none":
            recovered = self._dead
            self._dead = False
            self._misses = 0
            self._last_seen_name = name
            return WatchdogEvent(kind="recovered" if recovered else "none", reader_name=name)
        if not self.armed or self._dead:
            return WatchdogEvent(kind="none")
        self._misses += 1
        if self._misses < MISSES_BEFORE_DEATH:
            return WatchdogEvent(kind="none")
        self._dead = True
        return WatchdogEvent(kind="died", reader_name=self._last_seen_name)
