"""Audio Studio sleep timer (Phase 2 port-in).

Stop playback after a delay. One :class:`SleepTimerSetting`, persisted as
atomic JSON, checked by a lightweight daemon thread while the app runs.
Mirrors the shape of ``quill/core/radio/wake_timer.py`` (its twin): a pure
:func:`should_fire` the watcher thread and tests run, plus a
:class:`SleepTimerWatcher` that calls ``on_sleep`` once on the watcher thread
then stops. Hosts marshal to the UI thread via ``wx.CallAfter`` at the call
site, not inside the watcher. wx-free, strict-typed.

Honest about the same limit as the wake timer: the Studio must be running
(in the tray is fine) for the sleep to fire; nothing is installed into the OS.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILE_NAME = "audio_studio_sleep_timer.json"


@dataclass(slots=True)
class SleepTimerSetting:
    """The configured sleep timer."""

    enabled: bool = False
    delay_minutes: float = 30.0
    #: Stop at the end of the current chapter instead of after the fixed delay.
    #: Resolved by the host at the player's end-of-track callback, not here.
    end_of_chapter: bool = False
    #: Wall-clock seconds the current run started (set by the watcher's start).
    last_started_at: float = 0.0


def should_fire(setting: SleepTimerSetting, now: float, *, started_at: float) -> bool:
    """Pure check for the *delay* watcher: has ``delay_minutes`` elapsed?

    Returns ``False`` in end-of-chapter mode: that stop is resolved by the host
    at the player's end-of-track callback, so the elapsed-delay watcher must not
    also fire -- otherwise it would cut playback off mid-chapter after
    ``delay_minutes`` regardless of the chapter boundary the user asked for.
    """
    if not setting.enabled or setting.end_of_chapter:
        return False
    return (now - started_at) >= setting.delay_minutes * 60


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_sleep_setting(data_dir: Path) -> SleepTimerSetting:
    """Read the setting (an absent or broken file reads as disabled, 30 min)."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SleepTimerSetting()
    if not isinstance(raw, dict):
        return SleepTimerSetting()
    try:
        delay = float(raw.get("delay_minutes", 30.0))
    except (TypeError, ValueError):
        delay = 30.0
    return SleepTimerSetting(
        enabled=bool(raw.get("enabled", False)),
        delay_minutes=delay,
        end_of_chapter=bool(raw.get("end_of_chapter", False)),
        last_started_at=float(raw.get("last_started_at", 0.0) or 0.0),
    )


def save_sleep_setting(data_dir: Path, setting: SleepTimerSetting) -> None:
    """Persist the setting atomically (temp file + ``os.replace``)."""
    write_json_atomic(
        _store_path(data_dir),
        {
            "enabled": setting.enabled,
            "delay_minutes": setting.delay_minutes,
            "end_of_chapter": setting.end_of_chapter,
            "last_started_at": setting.last_started_at,
        },
    )


class SleepTimerWatcher:
    """Background thread that fires ``on_sleep`` once after the delay.

    The callback runs on the watcher thread; hosts marshal to the UI thread
    themselves (same contract as the radio wake timer). ``start`` begins a
    run; ``cancel`` voids the current run without stopping the thread;
    ``shutdown`` stops the thread for good (call at close).
    """

    def __init__(
        self,
        *,
        on_sleep: Callable[[], None],
        check_interval: float = 5.0,
    ) -> None:
        self._on_sleep = on_sleep
        self._check_interval = check_interval
        self._stop = threading.Event()
        self._started_at = 0.0
        self._setting: SleepTimerSetting | None = None
        self._fired = False
        self._thread = threading.Thread(target=self._run, daemon=True, name="quill-as-sleep-timer")
        self._thread.start()

    def start(self, setting: SleepTimerSetting, *, now: float) -> None:
        """Begin a run; ``now`` is the wall-clock seconds the run starts at."""
        self._started_at = now
        self._setting = setting
        self._fired = False

    def cancel(self) -> None:
        """Void the current run; the thread stays alive for a future start."""
        self._setting = None
        self._fired = False

    def shutdown(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(self._check_interval):
            setting = self._setting
            if setting is None or self._fired or not setting.enabled:
                continue
            if should_fire(setting, now=time.time(), started_at=self._started_at):
                self._fired = True
                self._on_sleep()
                return
