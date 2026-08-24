"""Speaking, or not, during quiet hours -- the one call every unprompted
announcement makes.

:mod:`quill.core.quiet_hours` decides; this is where the decision is spent.
It is deliberately **not** a gate around ``_announce``: quiet hours must never
silence the answer to a keypress, and the only way to be sure of that is for
each unprompted site to opt in by naming what it is.

    speak_background(self, "Three new episodes of The Daily.", kind=Kind.NEW_EPISODE)

The window is cached for a few seconds rather than re-read per announcement: a
forty-episode download batch would otherwise open the same small JSON file
forty times, and a listener who changes the setting is not waiting on the
second hand.
"""

from __future__ import annotations

import time as _clock
from datetime import datetime
from typing import Any

from quill.core.quiet_hours import (
    Kind,
    QuietHours,
    load_quiet_hours,
    save_quiet_hours,
    silences,
    toggle_sentence,
)

#: How long a loaded window is trusted before it is read again.
_CACHE_SECONDS = 5.0

_cached: QuietHours | None = None
_cached_at = 0.0


def current(*, force: bool = False) -> QuietHours:
    """The listener's quiet window, cached briefly."""
    global _cached, _cached_at
    now = _clock.monotonic()
    if force or _cached is None or (now - _cached_at) > _CACHE_SECONDS:
        from quill.core.paths import app_data_dir

        _cached = load_quiet_hours(app_data_dir())
        _cached_at = now
    return _cached


def invalidate() -> None:
    """Forget the cached window (after a settings change, and in tests)."""
    global _cached, _cached_at
    _cached = None
    _cached_at = 0.0


def held_back(kind: str, *, now: datetime | None = None) -> bool:
    """Whether an announcement of *kind* should stay silent right now."""
    moment = (now or datetime.now()).time()
    return silences(current(), kind, moment)


def speak_background(host: Any, message: str, *, kind: str = Kind.BACKGROUND) -> bool:
    """Announce *message* unless quiet hours hold this kind back.

    Returns whether it was spoken, so a caller that also earcons or writes a
    status line can stay in step with the speech rather than half-happening.
    """
    if not message:
        return False
    if held_back(kind):
        return False
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(message)
        return True
    return False


def should_tick(*, now: datetime | None = None) -> bool:
    """Whether a check heartbeat should make its sound right now."""
    return not held_back(Kind.TICK, now=now)


class QuietHoursMixin:
    """The frame's side: one toggle command, one honest sentence."""

    def _register_quiet_hours_commands(self) -> None:
        commands: Any = self.commands  # type: ignore[attr-defined]
        commands.try_register(
            "app.quiet_hours",
            "Quiet Hours...",
            self.open_quiet_hours,
            feature_id="core.app",
        )
        commands.try_register(
            "app.quiet_hours_toggle",
            "Quiet Hours On/Off",
            self.toggle_quiet_hours,
            feature_id="core.app",
        )

    def open_quiet_hours(self) -> None:
        """The window: when, and what still gets through."""
        from quill.ui.quiet_hours_dialog import show_quiet_hours

        show_quiet_hours(self)

    def toggle_quiet_hours(self) -> None:
        """Turn the quiet window on or off, and say which it now is."""
        from quill.core.paths import app_data_dir

        hours = current(force=True)
        hours.enabled = not hours.enabled
        save_quiet_hours(app_data_dir(), hours)
        invalidate()
        announce = getattr(self, "_announce", None)
        if callable(announce):
            announce(toggle_sentence(hours))
