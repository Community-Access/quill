"""Stop after silence: dictation that has heard nothing for a while stops.

Dictation Settings' *Stop dictation after silence* (off unless chosen). Every
state change the controller reports is activity -- speech starting, a phrase
being written, dictation starting -- so the clock is reset from the feedback
port's ``state_changed`` rather than from anywhere inside the recogniser. While
dictation is writing, a check runs every fifteen seconds; once it stops, the
check stops with it, so nothing ticks while dictation is off.

With the wake phrase on, stopping goes back to waiting for it, exactly as
saying "stop dictation" would; the silence limit applies only to writing.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import wx

from quill.core.windows_dictation.controller import DictationState
from quill.core.windows_dictation.options import silence_expired

__all__ = ["check_silence", "note_activity"]

_CHECK_MS = 15_000

_last_heard = time.monotonic()
_timer: Any = None


def note_activity(state: DictationState, controller: Callable[[], Any]) -> None:
    """Reset the clock, and make sure a check is waiting while dictation writes."""
    global _last_heard
    _last_heard = time.monotonic()
    if state is DictationState.LISTENING and _timer is None:
        _schedule(controller)


def _schedule(controller: Callable[[], Any]) -> None:
    global _timer
    try:
        _timer = wx.CallLater(_CHECK_MS, _tick, controller)
    except Exception:  # noqa: BLE001 - no event loop (tests): nothing to watch
        _timer = None


def _tick(controller: Callable[[], Any]) -> None:
    global _timer
    _timer = None
    current = controller()
    if current is None or not current.active:
        return
    if check_silence(current, time.monotonic()):
        return
    _schedule(controller)


def check_silence(controller: Any, now: float) -> bool:
    """Stop *controller* if its silence limit has passed. Returns whether it did."""
    minutes = int(getattr(controller.preferences, "silence_minutes", 0) or 0)
    if controller.state is not DictationState.LISTENING:
        return False
    if not silence_expired(_last_heard, now, minutes):
        return False
    unit = "minute" if minutes == 1 else "minutes"
    controller.stop(f"Dictation off after {minutes} {unit} of silence.")
    return True
