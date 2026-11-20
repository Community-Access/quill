"""Which scheduled recordings were missed while the app was closed (#4).

Extracted from ``recording_schedule`` under GATE-11 (extract, never rebaseline)
so the scheduler could gain its stale-snapshot check (plan.md, Windows Radio
recording review, 2026-11-20). The occurrence arithmetic it relies on -- each
entry's own zone, its wall-clock time, "naive means system-local" -- stays in
``recording_schedule`` and is imported rather than repeated.

wx-free, strict-typed.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from quill.core.radio.recording_schedule import (
    RecordingScheduleEntry,
    _entry_zone,
    _time_of_day,
    _to_absolute,
)

#: Cap the missed-occurrence look-back so a long-dormant install (or an empty
#: "last seen") never reports months of daily occurrences at once (#4).
_MAX_MISSED_LOOKBACK_DAYS = 62


def _occurrences_between(
    entry: RecordingScheduleEntry, since_abs: datetime, now_abs: datetime
) -> list[datetime]:
    """Absolute moments *entry* would have fired in ``(since_abs, now_abs]``.

    Interprets the entry's wall-clock time in its own zone (local when unset),
    the same frame :func:`is_due` uses. An occurrence on or before
    ``last_fired_date`` is treated as already handled and skipped.
    """
    zone = _entry_zone(entry)
    if entry.recurrence == "once":
        if entry.last_fired_date:
            return []
        try:
            target = datetime.fromisoformat(entry.run_at)
        except ValueError:
            return []
        if zone is not None and target.tzinfo is None:
            target = target.replace(tzinfo=zone)
        target_abs = _to_absolute(target)
        return [target_abs] if since_abs < target_abs <= now_abs else []
    time_of_day = _time_of_day(entry.run_at)
    if time_of_day is None:
        return []
    hour, minute = time_of_day
    # Walk each calendar date in the entry's zone across the window.
    start_local = since_abs.astimezone(zone) if zone is not None else since_abs.astimezone()
    end_local = now_abs.astimezone(zone) if zone is not None else now_abs.astimezone()
    day = start_local.date()
    last_day = end_local.date()
    if (last_day - day).days > _MAX_MISSED_LOOKBACK_DAYS:
        day = last_day - timedelta(days=_MAX_MISSED_LOOKBACK_DAYS)
    occurrences: list[datetime] = []
    while day <= last_day:
        if entry.recurrence == "weekly" and day.weekday() != entry.weekday:
            day += timedelta(days=1)
            continue
        if entry.last_fired_date and day.isoformat() <= entry.last_fired_date:
            day += timedelta(days=1)
            continue
        occ = datetime(day.year, day.month, day.day, hour, minute, tzinfo=start_local.tzinfo)
        occ_abs = _to_absolute(occ)
        if since_abs < occ_abs <= now_abs:
            occurrences.append(occ_abs)
        day += timedelta(days=1)
    return occurrences


def missed_occurrences(
    entries: list[RecordingScheduleEntry], *, since: datetime, now: datetime
) -> list[tuple[RecordingScheduleEntry, datetime]]:
    """Enabled schedule occurrences that fell in ``(since, now]`` (#4), excluding
    any whose window is still open at *now* (R2/11.7: those will start late on
    launch, so they are not "missed").

    Used at startup to report recordings whose time passed while the app was
    closed (``since`` = when it was last running). Returns (entry, moment)
    pairs, earliest first; an empty or future ``since`` yields nothing.
    """
    since_abs = _to_absolute(since)
    now_abs = _to_absolute(now)
    if since_abs >= now_abs:
        return []
    missed: list[tuple[RecordingScheduleEntry, datetime]] = []
    for entry in entries:
        if not entry.enabled:
            continue
        for moment in _occurrences_between(entry, since_abs, now_abs):
            # R2/11.7: if the window is still open, the scheduler will start it
            # late on this launch -- do not also announce it as missed.
            if now_abs < moment + timedelta(minutes=max(1, entry.duration_minutes)):
                continue
            missed.append((entry, moment))
    missed.sort(key=lambda pair: pair[1])
    return missed


def describe_missed(missed: list[tuple[RecordingScheduleEntry, datetime]]) -> str:
    """A spoken one-line summary of *missed* occurrences, or "" when none (#4).

    Names up to three stations with the local time each was due; more than
    three collapses to a count so the announcement stays short.
    """
    if not missed:
        return ""

    def _when(moment: datetime) -> str:
        return moment.astimezone().strftime("%a %b %d %I:%M %p").replace(" 0", " ")

    parts = [f"{entry.station_name} at {_when(moment)}" for entry, moment in missed[:3]]
    extra = len(missed) - 3
    if extra > 0:
        parts.append(f"and {extra} more")
    count = len(missed)
    noun, verb = ("recording", "was") if count == 1 else ("recordings", "were")
    return f"{count} scheduled {noun} {verb} missed while Quill Radio was closed: " + "; ".join(
        parts
    )
