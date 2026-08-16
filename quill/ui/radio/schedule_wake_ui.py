"""Wiring the two automatic halves of "be awake when the recording is due".

The decisions are all in :mod:`quill.core.radio.schedule_wake` (pure, tested
against a clock you pass in) and the OS call is in
:mod:`quill.platform.windows.recording_wake_task`. This is the thin layer that
knows about the running app: where the schedule lives, when to re-ask, and
which preference governs each half.

It is a module of host-taking functions rather than a mixin because
``main_frame_radio`` is at its GATE-11 ceiling, and because both halves are the
same shape as the rest of the radio glue -- ``refresh(host)``, called whenever
something might have changed.

**Two preferences, deliberately separate.** Holding standby off is a small,
local, permission-free thing; registering a task that wakes a sleeping computer
is a change to the machine. Somebody may reasonably want the first and not the
second, and a single switch would make that impossible to say.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _entries(host: Any) -> list[Any]:
    """The scheduled entries, or an empty list before the scheduler exists."""
    scheduler = getattr(host, "_radio_scheduler", None)
    entries = getattr(scheduler, "entries", None)
    return list(entries) if entries else []


def recording_is_imminent(host: Any, now: datetime | None = None) -> bool:
    """Whether a scheduled recording is close enough to hold standby off for.

    Consulted by the sleep inhibitor on every tick, so it is guarded end to
    end: a schedule that cannot be read is simply "nothing imminent" rather
    than an exception on a timer callback.
    """
    if not bool(getattr(host._radio_history, "keep_awake_before_recording", True)):
        return False
    try:
        from quill.core.radio.schedule_wake import is_imminent

        return is_imminent(_entries(host), now or datetime.now())
    except Exception:  # noqa: BLE001 - never let a timer tick raise
        return False


def refresh_wake_task(host: Any) -> None:
    """Re-register the OS wake for the next recording, or remove it.

    Called when the schedule changes and after a recording finishes, which is
    when "the next occurrence" becomes a different moment. Windows-only and
    best effort: a machine whose policy forbids scheduled tasks silently keeps
    the other two defences.
    """
    try:
        from quill.core.radio.schedule_wake import next_wake_moment
        from quill.platform.windows import recording_wake_task as task

        if not task.is_windows():
            return
        wanted = bool(getattr(host._radio_history, "wake_for_scheduled_recording", True))
        moment = next_wake_moment(_entries(host), datetime.now()) if wanted else None
        if moment is None:
            # No schedule, or the preference is off: leave nothing behind. A
            # stale task would wake the machine for a recording that is not
            # coming, which is worse than not waking at all.
            task.unregister()
            return
        task.register(moment)
    except Exception:  # noqa: BLE001 - a wake we cannot register is not fatal
        return


def describe_next(host: Any) -> str:
    """One spoken sentence about the next scheduled recording."""
    try:
        from quill.core.radio.schedule_wake import describe

        return describe(_entries(host), datetime.now())
    except Exception:  # noqa: BLE001
        return "No recordings are scheduled."
