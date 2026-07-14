"""Scheduled radio recordings -- fires only while QUILL is running.

Deliberately not an OS-level scheduled task (Windows Task Scheduler, cron,
launchd): "add scheduling if QUILL is open to record" is the explicit,
simpler scope this implements -- an in-process scheduler thread wakes
periodically and starts any entry whose time has come. If QUILL isn't
running at the scheduled moment, that occurrence is simply missed; there is
no catch-up, and no background service keeps running after QUILL exits.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

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
    (0=Monday..6=Sunday) only matters for ``"weekly"``. ``last_fired_date``
    (an ISO date) guards against firing more than once for the same
    occurrence -- for ``"once"`` it also means "already used."
    """

    id: str
    station_name: str
    stream_url: str
    recurrence: Recurrence
    run_at: str
    weekday: int = -1
    duration_minutes: int = 60
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


def is_due(entry: RecordingScheduleEntry, now: datetime) -> bool:
    """Pure, testable: would *entry* fire right now?"""
    if not entry.enabled:
        return False
    today = now.date().isoformat()
    if entry.recurrence == "once":
        if entry.last_fired_date:
            return False
        try:
            target = datetime.fromisoformat(entry.run_at)
        except ValueError:
            return False
        return now >= target
    if entry.last_fired_date == today:
        return False
    time_of_day = _time_of_day(entry.run_at)
    if time_of_day is None:
        return False
    hour, minute = time_of_day
    if now.hour != hour or now.minute != minute:
        return False
    if entry.recurrence == "weekly" and now.weekday() != entry.weekday:
        return False
    return True


def due_entries(
    entries: list[RecordingScheduleEntry], now: datetime
) -> list[RecordingScheduleEntry]:
    return [entry for entry in entries if is_due(entry, now)]


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
    ) -> None:
        self._data_dir = data_dir
        self._recorder = recorder
        self._recording_settings = recording_settings
        self._on_fired = on_fired or (lambda _entry, _error: None)
        self.entries: list[RecordingScheduleEntry] = load_schedule(data_dir)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="quill-radio-scheduler")
        self._thread.start()

    def set_recording_settings(self, settings: RecordingSettings) -> None:
        """Update the settings used by every future scheduled firing."""
        self._recording_settings = settings

    def add(self, entry: RecordingScheduleEntry) -> None:
        self.entries.append(entry)
        save_schedule(self._data_dir, self.entries)

    def remove(self, entry_id: str) -> bool:
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.id != entry_id]
        if len(self.entries) != before:
            save_schedule(self._data_dir, self.entries)
            return True
        return False

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=_POLL_SECONDS):
            now = datetime.now()
            for entry in due_entries(self.entries, now):
                self._fire(entry, now)

    def _fire(self, entry: RecordingScheduleEntry, now: datetime) -> None:
        error: str = ""
        try:
            self._recorder.start(
                station_name=entry.station_name,
                stream_url=entry.stream_url,
                settings=self._recording_settings,
                duration_minutes=entry.duration_minutes,
            )
        except RecordingError as exc:
            error = str(exc)
            logger.warning("Scheduled radio recording %s could not start: %s", entry.id, exc)
        entry.last_fired_date = now.date().isoformat()
        save_schedule(self._data_dir, self.entries)
        self._on_fired(entry, error)

    def shutdown(self) -> None:
        self._stop_event.set()
