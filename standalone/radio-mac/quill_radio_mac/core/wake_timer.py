"""The sleep timer's twin: start a station playing at a set time.

One configured wake-up (once or daily), persisted as atomic JSON,
checked by a lightweight background thread while the app runs.
Deliberately honest about its limits: this app must be running -- hidden
behind Cmd+W is fine -- for the wake-up to fire; nothing is installed
into the OS task scheduler (macOS's ``launchd`` included).

Ported near-verbatim from upstream ``quill.core.radio.wake_timer``.

wx-free, strict-typed.

Threading contract: :class:`WakeUpWatcher` runs its own daemon thread
(``quill-radio-wake-timer``) that reloads the setting from disk every
``_CHECK_SECONDS`` and calls ``on_wake`` on that same thread when it is
time -- a UI caller marshals to the main thread itself, the same
contract the recorder and scheduler use. ``load_wake_setting`` /
``save_wake_setting`` are plain synchronous file IO, safe from any
thread.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quill_radio_mac.core.models import RadioStation

_FILE_NAME = "radio_wake_timer.json"
_CHECK_SECONDS = 20.0


@dataclass(slots=True)
class WakeUpSetting:
    """The single configured wake-up."""

    enabled: bool = False
    #: "HH:MM" 24-hour local time.
    time_of_day: str = ""
    #: "once" fires at the next occurrence then disables itself; "daily" repeats.
    recurrence: str = "once"
    station: RadioStation | None = None
    #: ISO date the wake-up last fired, so one occurrence never double-fires.
    last_fired_date: str = ""

    @property
    def is_ready(self) -> bool:
        return self.enabled and bool(self.time_of_day) and self.station is not None

    def spoken_summary(self) -> str:
        if not self.is_ready or self.station is None:
            return "No wake-up timer is set."
        cadence = "every day" if self.recurrence == "daily" else "once"
        return f"Wake up {cadence} at {self.time_of_day} with {self.station.display_name}."


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_wake_setting(data_dir: Path) -> WakeUpSetting:
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return WakeUpSetting()
    if not isinstance(raw, dict):
        return WakeUpSetting()
    station_data = raw.get("station")
    station = RadioStation.from_dict(station_data) if isinstance(station_data, dict) else None
    recurrence = str(raw.get("recurrence", "once"))
    return WakeUpSetting(
        enabled=bool(raw.get("enabled", False)),
        time_of_day=str(raw.get("time_of_day", "")),
        recurrence=recurrence if recurrence in ("once", "daily") else "once",
        station=station,
        last_fired_date=str(raw.get("last_fired_date", "")),
    )


def save_wake_setting(data_dir: Path, setting: WakeUpSetting) -> None:
    from quill_radio_mac.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "enabled": setting.enabled,
            "time_of_day": setting.time_of_day,
            "recurrence": setting.recurrence,
            "station": setting.station.to_dict() if setting.station is not None else None,
            "last_fired_date": setting.last_fired_date,
        },
    )


def parse_time_of_day(text: str) -> str:
    """Normalize a user-typed time to "HH:MM"; "" when it isn't one."""
    cleaned = text.strip()
    for fmt in ("%H:%M", "%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return ""


def should_fire(setting: WakeUpSetting, now: datetime) -> bool:
    """Pure check the watcher thread (and tests) run: is it wake-up time?"""
    if not setting.is_ready:
        return False
    if setting.last_fired_date == now.strftime("%Y-%m-%d"):
        return False
    return now.strftime("%H:%M") >= setting.time_of_day and (
        # Only within the same hour-ish window: a wake-up set for 07:00
        # must not fire when the app first opens at 21:30 that day.
        _minutes(now.strftime("%H:%M")) - _minutes(setting.time_of_day) <= 5
    )


def _minutes(hhmm: str) -> int:
    hours, _, minutes = hhmm.partition(":")
    try:
        return int(hours) * 60 + int(minutes)
    except ValueError:
        return -1


class WakeUpWatcher:
    """Background thread that fires ``on_wake(station)`` at the set time.

    The callback runs on the watcher thread; hosts marshal to the UI
    thread themselves (the same contract as the recorder and
    scheduler)."""

    def __init__(
        self,
        data_dir: Path,
        *,
        on_wake: Callable[[RadioStation], None],
    ) -> None:
        self._data_dir = data_dir
        self._on_wake = on_wake
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="quill-radio-wake-timer"
        )
        self._thread.start()

    def shutdown(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(_CHECK_SECONDS):
            setting = load_wake_setting(self._data_dir)
            now = datetime.now()
            if not should_fire(setting, now):
                continue
            setting.last_fired_date = now.strftime("%Y-%m-%d")
            if setting.recurrence == "once":
                setting.enabled = False
            save_wake_setting(self._data_dir, setting)
            if setting.station is not None:
                self._on_wake(setting.station)
