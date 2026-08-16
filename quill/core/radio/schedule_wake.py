"""Making sure the computer is awake when a scheduled recording is due.

A scheduled recording cannot fire on a sleeping machine. The scheduler is a
thread inside a running app, so when Windows drops into standby it simply stops
being asked, and the recording starts whenever the machine next wakes -- which
looks, from the outside, exactly like the app losing track of time. A listener
who scheduled 11:00 and got 11:03 has no way to tell those apart.

Quill Radio already inhibits standby *while* something plays or records
(:mod:`quill.platform.keep_awake`), which is the easy half. This module is the
other half: the stretch *before* a recording, when nothing is playing and there
is nothing to keep the machine up.

Three defences, weakest to strongest, and they are meant to be used together:

1. **Say so.** The schedule dialog states the requirement in one line. A
   listener who knows their machine sleeps can then plan around it.
2. **Hold standby off as the moment approaches** -- :func:`is_imminent`. Cheap,
   needs no permissions, and covers the common case of a machine that is awake
   now and would otherwise doze in the next few minutes.
3. **Ask the OS to wake for it** -- :func:`next_wake_moment` feeds a Windows
   scheduled task with ``WakeToRun``. The only one that survives a machine that
   is *already* asleep, and the only one that needs the OS's cooperation.

Everything here is pure: it answers *when* and *whether*, never *how*. The
Windows end lives in :mod:`quill.platform.windows.recording_wake_task` and the
UI glue in :mod:`quill.ui.radio.schedule_wake_ui`, so this stays wx-free,
platform-free and testable with a clock you pass in.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

#: How long before a recording to start refusing standby. Five minutes is the
#: shape of the problem rather than a round number: Windows' shortest idle
#: sleep timer is a couple of minutes, and the transition itself plus the
#: scheduler's twenty-second poll want headroom on top.
IMMINENT_MINUTES = 5

#: How far ahead of the recording to wake the machine. It has to cover the
#: wake itself, the sign-in screen, and -- if Quill Radio is not running -- an
#: app launch, before the scheduler's first poll can fire the entry. A minute
#: is not enough for a cold machine; two is.
WAKE_LEAD_MINUTES = 2


def _next_moments(entries: list[Any], now: datetime) -> list[datetime]:
    """Every enabled entry's next occurrence, as absolute datetimes.

    Disabled entries are skipped -- an entry switched off is not a reason to
    keep somebody's computer awake -- and anything whose time cannot be parsed
    contributes nothing rather than raising: this runs on a UI timer, and a
    single malformed entry must not cost the whole feature.
    """
    from quill.core.radio.recording_schedule import next_occurrence

    moments: list[datetime] = []
    for entry in entries or []:
        if not getattr(entry, "enabled", True):
            continue
        try:
            moment = next_occurrence(entry, now)
        except Exception:  # noqa: BLE001 - one bad entry is not a failed schedule
            continue
        if moment is not None:
            moments.append(moment)
    return moments


def _as_absolute(moment: datetime, now: datetime) -> datetime:
    """Put *moment* in the same awareness as *now* so they can be compared."""
    if moment.tzinfo is not None and now.tzinfo is None:
        return moment.astimezone().replace(tzinfo=None)
    if moment.tzinfo is None and now.tzinfo is not None:
        return moment.astimezone(now.tzinfo)
    return moment


def seconds_until_next(entries: list[Any], now: datetime) -> float | None:
    """Seconds until the soonest upcoming recording, or ``None`` if there is none.

    Never negative: an occurrence already under way returns 0.0, because the
    honest answer to "how long until I need the machine awake" is "now".
    """
    soonest: float | None = None
    for moment in _next_moments(entries, now):
        delta = (_as_absolute(moment, now) - now).total_seconds()
        seconds = max(0.0, delta)
        if soonest is None or seconds < soonest:
            soonest = seconds
    return soonest


def is_imminent(
    entries: list[Any], now: datetime, *, within_minutes: int = IMMINENT_MINUTES
) -> bool:
    """Whether a scheduled recording is close enough to hold standby off for.

    The question the sleep inhibitor asks on every tick. ``False`` when nothing
    is scheduled, so an empty schedule never costs anybody a sleeping computer.
    """
    seconds = seconds_until_next(entries, now)
    return seconds is not None and seconds <= max(0, within_minutes) * 60


def next_wake_moment(
    entries: list[Any], now: datetime, *, lead_minutes: int = WAKE_LEAD_MINUTES
) -> datetime | None:
    """When to ask the OS to wake the machine, or ``None`` if nothing is due.

    The soonest occurrence, minus a lead. Clamped to at least a minute from
    now: registering a wake for a moment that has already passed either fires
    instantly or is refused outright, and neither is what "wake me at 10:58"
    was supposed to mean.
    """
    moments = [_as_absolute(m, now) for m in _next_moments(entries, now)]
    if not moments:
        return None
    target = min(moments) - timedelta(minutes=max(0, lead_minutes))
    floor = now + timedelta(minutes=1)
    return max(target, floor)


def describe(entries: list[Any], now: datetime) -> str:
    """One spoken sentence about the next recording, for a status line.

    Words, never a timecode -- "in 2 hours, 5 minutes", not "2:05" -- because
    this is read aloud and a bare pair of numbers is ambiguous.
    """
    seconds = seconds_until_next(entries, now)
    if seconds is None:
        return "No recordings are scheduled."
    minutes = int(seconds // 60)
    if minutes <= 0:
        return "A scheduled recording is due now."
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'' if hours == 1 else 's'}")
    if minutes or not hours:
        parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
    return f"Next scheduled recording in {', '.join(parts)}."
