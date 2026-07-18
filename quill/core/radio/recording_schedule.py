"""Scheduled radio recordings -- fires only while QUILL is running.

Deliberately not an OS-level scheduled task (Windows Task Scheduler, cron,
launchd): "add scheduling if QUILL is open to record" is the explicit, simpler
scope this implements -- an in-process scheduler thread wakes periodically and
starts any entry whose time has come. If QUILL isn't running at the scheduled
moment, that occurrence is missed; there is no catch-up, and no background
service keeps running after QUILL exits.

R2 firing model (replaces the exact-minute match that dropped occurrences if a
poll landed outside the target minute): each entry has an *occurrence window*
``[start, start + duration)`` -- ``start`` is today's wall-clock time in the
entry's own zone (or the once target). An entry fires whenever ``now`` falls in
that window and it has not already fired today, recording only the *remaining*
minutes so a late launch still catches the show instead of overshooting. That
also gives launch-time catch-up for free: a daily 08:00 show reopened at 08:30
records the last 30 minutes. A failure to start does **not** stamp the entry --
the next poll retries within the same window (so a busy recorder or a momentary
ffmpeg hiccup no longer burns a once-recording).

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from quill.core.radio.recording import RadioRecorder, RecordingError, RecordingSettings

logger = logging.getLogger(__name__)

Recurrence = Literal["once", "daily", "weekly"]

_POLL_SECONDS = 20.0
_FILE_NAME = "radio_recording_schedule.json"


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass(slots=True)
class RecordingScheduleEntry:
    """One scheduled recording.

    ``run_at`` is an ISO ``YYYY-MM-DDTHH:MM`` moment for ``"once"``; for
    ``"daily"``/``"weekly"`` only its ``HH:MM`` time-of-day is read. ``weekday``
    (0=Monday..6=Sunday) only matters for ``"weekly"``. ``timezone`` is an IANA
    zone name (e.g. ``"America/New_York"``); empty means the machine's local
    time, and the entry's wall-clock time is interpreted in that zone so a
    Pacific user can record an Eastern show at the right local moment.
    ``last_fired_date`` (an ISO date in the entry's zone) guards against firing
    more than once for the same day -- for ``"once"`` it also means "already
    used," and R2 additionally sets ``enabled=False`` on a successful once-fire.
    """

    id: str
    station_name: str
    stream_url: str
    recurrence: Recurrence
    run_at: str
    weekday: int = -1
    duration_minutes: int = 60
    timezone: str = ""
    enabled: bool = True
    last_fired_date: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "station_name": self.station_name,
            "stream_url": self.stream_url,
            "recurrence": self.recurrence,
            "run_at": self.run_at,
            "weekday": self.weekday,
            "duration_minutes": self.duration_minutes,
            "timezone": self.timezone,
            "enabled": self.enabled,
            "last_fired_date": self.last_fired_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RecordingScheduleEntry | None:
        entry_id = str(data.get("id", "")).strip()
        station_name = str(data.get("station_name", "")).strip()
        stream_url = str(data.get("stream_url", "")).strip()
        run_at = str(data.get("run_at", "")).strip()
        recurrence = str(data.get("recurrence", "once"))
        if not entry_id or not station_name or not stream_url or not run_at:
            return None
        if recurrence not in ("once", "daily", "weekly"):
            recurrence = "once"
        weekday = data.get("weekday")
        duration = data.get("duration_minutes")
        return cls(
            id=entry_id,
            station_name=station_name,
            stream_url=stream_url,
            recurrence=recurrence,  # type: ignore[arg-type]
            run_at=run_at,
            weekday=int(weekday) if isinstance(weekday, (int, float)) else -1,
            duration_minutes=int(duration) if isinstance(duration, (int, float)) else 60,
            timezone=str(data.get("timezone", "")).strip(),
            enabled=bool(data.get("enabled", True)),
            last_fired_date=str(data.get("last_fired_date", "")),
        )


def _time_of_day(run_at: str) -> tuple[int, int] | None:
    """Parse the ``HH:MM`` portion out of an ISO-ish ``run_at`` string."""
    try:
        parsed = datetime.fromisoformat(run_at)
    except ValueError:
        return None
    return parsed.hour, parsed.minute


def _entry_zone(entry: RecordingScheduleEntry) -> ZoneInfo | None:
    """The entry's IANA zone, or ``None`` for local time / an unknown name.

    An empty ``timezone`` means "local", and a bad name degrades to local too
    so a corrupt record can never crash the scheduler thread.
    """
    if not entry.timezone:
        return None
    try:
        return ZoneInfo(entry.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _to_absolute(moment: datetime) -> datetime:
    """A naive datetime is taken as system-local; an aware one is left as-is."""
    return moment if moment.tzinfo is not None else moment.astimezone()


def _local_now(entry: RecordingScheduleEntry, now: datetime) -> datetime:
    """*now* expressed in the entry's zone (naive *now* taken as system-local)."""
    zone = _entry_zone(entry)
    if zone is None:
        return now
    now_abs = now if now.tzinfo is not None else now.astimezone()
    return now_abs.astimezone(zone)


def occurrence_start(entry: RecordingScheduleEntry, now: datetime) -> datetime | None:
    """The absolute start moment of the occurrence in effect at *now*, or
    ``None`` if there is none today (R2 firing model).

    * once: the target moment, if it has not already fired (else ``None`` so a
      spent once-entry can never be due again).
    * daily: today's ``HH:MM`` in the entry's zone.
    * weekly: today's ``HH:MM`` in the entry's zone, but only on the entry's
      weekday -- ``None`` on the other six days.

    The returned datetime is absolute (aware); the caller compares *now* (made
    absolute the same way) against it and ``start + duration``.
    """
    if not entry.enabled:
        return None
    zone = _entry_zone(entry)
    if entry.recurrence == "once":
        if entry.last_fired_date:
            return None
        try:
            target = datetime.fromisoformat(entry.run_at)
        except ValueError:
            return None
        if zone is not None and target.tzinfo is None:
            target = target.replace(tzinfo=zone)
        return _to_absolute(target)
    time_of_day = _time_of_day(entry.run_at)
    if time_of_day is None:
        return None
    hour, minute = time_of_day
    local = _local_now(entry, now)
    if entry.recurrence == "weekly" and local.weekday() != entry.weekday:
        return None
    start_local = datetime(local.year, local.month, local.day, hour, minute, tzinfo=local.tzinfo)
    return _to_absolute(start_local)


def is_due(entry: RecordingScheduleEntry, now: datetime) -> bool:
    """Pure, testable: should *entry* fire right now (R2 window model)?

    Fires when *now* falls in the occurrence window ``[start, start + duration)``
    and the entry has not already fired today (in its own zone). ``start`` comes
    from :func:`occurrence_start`; an entry whose day/weekday has no occurrence,
    or a spent once-entry, returns ``False``. This replaces the old exact-minute
    match: a poll that lands a minute or more past the start still fires (with
    the remaining minutes), so a stall across the target minute no longer drops
    the occurrence, and a launch inside the window catches up automatically.
    """
    if not entry.enabled:
        return False
    start = occurrence_start(entry, now)
    if start is None:
        return False
    now_abs = _to_absolute(now)
    if now_abs < start:
        return False
    if _today_in_zone(entry, now) == entry.last_fired_date:
        return False
    end = start + timedelta(minutes=max(1, entry.duration_minutes))
    return now_abs < end


def _today_in_zone(entry: RecordingScheduleEntry, now: datetime) -> str:
    """ISO date of *now* in the entry's effective zone (local when unset).

    Used to stamp ``last_fired_date`` in the same frame of reference
    :func:`is_due` reads it, so the once-per-day guard is correct for a zoned
    entry even when the machine's local date differs from the entry-zone date.
    """
    return _local_now(entry, now).date().isoformat()


def due_entries(
    entries: list[RecordingScheduleEntry], now: datetime
) -> list[RecordingScheduleEntry]:
    return [entry for entry in entries if is_due(entry, now)]


def remaining_minutes(entry: RecordingScheduleEntry, now: datetime) -> int:
    """Minutes left in the current occurrence window, at least 1 (R2 late-start).

    A fire at the start returns the full duration; a fire halfway returns the
    remaining half, so a recording started late does not overshoot the intended
    end. Returns the full duration when *now* is at/before the start.
    """
    start = occurrence_start(entry, now)
    if start is None:
        return max(1, entry.duration_minutes)
    now_abs = _to_absolute(now)
    if now_abs <= start:
        return max(1, entry.duration_minutes)
    end = start + timedelta(minutes=max(1, entry.duration_minutes))
    left = math.ceil((end - now_abs).total_seconds() / 60)
    return max(1, left)


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


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_schedule(data_dir: Path) -> list[RecordingScheduleEntry]:
    """Read the saved schedule (an absent or broken file reads as empty)."""
    path = _store_path(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    entries: list[RecordingScheduleEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entry = RecordingScheduleEntry.from_dict(item)
        if entry is not None:
            entries.append(entry)
    return entries


def save_schedule(data_dir: Path, entries: list[RecordingScheduleEntry]) -> None:
    """Persist the schedule atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(_store_path(data_dir), [e.to_dict() for e in entries])


class RecordingScheduler:
    """Background thread: wakes every ``_POLL_SECONDS`` and starts any due
    entry on the shared :class:`RadioRecorder`."""

    def __init__(
        self,
        *,
        data_dir: Path,
        recorder: RadioRecorder,
        recording_settings: RecordingSettings,
        on_fired: Callable[[RecordingScheduleEntry, str], None] | None = None,
        on_busy: Callable[[RecordingScheduleEntry], None] | None = None,
        filter_graph_provider: Callable[[], str] | None = None,
    ) -> None:
        self._data_dir = data_dir
        self._recorder = recorder
        self._recording_settings = recording_settings
        self._on_fired = on_fired or (lambda _entry, _error: None)
        #: Fired once per entry when a fire is deferred because the recorder is
        #: busy (R2/11.3) -- the entry is held pending and retried within its
        #: window rather than burned. ``None`` means "stay silent."
        self._on_busy = on_busy or (lambda _entry: None)
        #: Called at fire time for the current Sound Enhancements filter
        #: graph (""  if apply_sound_enhancements is off) -- injected so this
        #: wx-free module never has to know about audio_enhance.py or the
        #: live RadioHistory state that owns the current EQ preset/compressor.
        self._filter_graph_provider = filter_graph_provider or (lambda: "")
        self._lock = threading.RLock()
        self.entries: list[RecordingScheduleEntry] = load_schedule(data_dir)
        #: Entry ids whose last fire outcome was already announced (R2): a busy
        #: deferral or a hard failure is spoken once, then retried silently until
        #: it succeeds (which clears the id).
        self._announced: set[str] = set()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="quill-radio-scheduler")
        self._thread.start()

    def set_recording_settings(self, settings: RecordingSettings) -> None:
        """Update the settings used by every future scheduled firing."""
        self._recording_settings = settings

    def add(self, entry: RecordingScheduleEntry) -> None:
        with self._lock:
            self.entries.append(entry)
            save_schedule(self._data_dir, self.entries)

    def update(self, entry: RecordingScheduleEntry) -> bool:
        """Replace the entry with the same id in place; ``False`` if absent."""
        with self._lock:
            for index, existing in enumerate(self.entries):
                if existing.id == entry.id:
                    self.entries[index] = entry
                    save_schedule(self._data_dir, self.entries)
                    return True
        return False

    def remove(self, entry_id: str) -> bool:
        with self._lock:
            before = len(self.entries)
            self.entries = [e for e in self.entries if e.id != entry_id]
            if len(self.entries) != before:
                save_schedule(self._data_dir, self.entries)
                return True
        return False

    def _run(self) -> None:
        # R2/11.4: the loop body is wrapped so one failing iteration (or a
        # concurrent mutation of self.entries) can never kill the thread and
        # silently drop every future scheduled recording for the session.
        while not self._stop_event.wait(timeout=_POLL_SECONDS):
            try:
                now = datetime.now()
                with self._lock:
                    snapshot = list(self.entries)
                for entry in due_entries(snapshot, now):
                    if self._stop_event.is_set():
                        break
                    self._fire(entry, now)
            except Exception:  # noqa: BLE001 - scheduler thread must never die
                logger.exception("Radio scheduler iteration failed; continuing.")

    def _fire(self, entry: RecordingScheduleEntry, now: datetime) -> None:
        """Start *entry* now, recording only the remaining minutes (R2).

        On a busy recorder the fire is deferred (announced once) and retried on
        the next poll within the window (11.3); on a hard failure it is also
        retried within the window without stamping the entry (11.2); only a
        successful start stamps ``last_fired_date`` (and disables a once-entry).
        """
        try:
            self._recorder.start(
                station_name=entry.station_name,
                stream_url=entry.stream_url,
                settings=self._recording_settings,
                duration_minutes=remaining_minutes(entry, now),
                filter_graph=self._filter_graph_provider(),
            )
            started = True
            error = ""
        except RecordingError as exc:
            started = False
            error = str(exc)

        if started:
            self._stamp_fired(entry, now)
            self._announced.discard(entry.id)
            self._on_fired(entry, "")
            return

        if "already in progress" in error.lower():
            # Recorder busy: hold the entry pending and retry within its window
            # instead of burning the occurrence (R2/11.3). Announce once.
            if entry.id not in self._announced:
                self._announced.add(entry.id)
                self._on_busy(entry)
            return
        # Hard failure (ffmpeg missing, etc.): announce once, then retry within
        # the window on later polls without stamping (R2/11.2).
        logger.warning("Scheduled radio recording %s could not start: %s", entry.id, error)
        if entry.id not in self._announced:
            self._announced.add(entry.id)
            self._on_fired(entry, error)

    def _stamp_fired(self, entry: RecordingScheduleEntry, now: datetime) -> None:
        """Stamp the live entry by id (not the snapshot ref) and disable a
        once-entry on success (R1/10.1 + R2/11.5)."""
        with self._lock:
            for existing in self.entries:
                if existing.id == entry.id:
                    existing.last_fired_date = _today_in_zone(existing, now)
                    if existing.recurrence == "once":
                        existing.enabled = False
                    save_schedule(self._data_dir, self.entries)
                    return

    def shutdown(self) -> None:
        self._stop_event.set()
