"""Tests for quill_radio_mac.core.wake_timer: parse_time_of_day,
should_fire's window logic, persistence round trip, and the watcher
thread firing once inside its check window (no network)."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from quill_radio_mac.core.models import RadioStation
from quill_radio_mac.core.wake_timer import (
    WakeUpSetting,
    WakeUpWatcher,
    load_wake_setting,
    parse_time_of_day,
    save_wake_setting,
    should_fire,
)

_STATION = RadioStation(name="WQXR", stream_url="https://wqxr.example.com")


def _setting(**overrides: object) -> WakeUpSetting:
    values: dict = {
        "enabled": True,
        "time_of_day": "07:00",
        "recurrence": "daily",
        "station": _STATION,
    }
    values.update(overrides)
    return WakeUpSetting(**values)


def test_parse_time_of_day_accepts_24h_and_12h():
    assert parse_time_of_day("07:30") == "07:30"
    assert parse_time_of_day("7:30 AM") == "07:30"
    assert parse_time_of_day("10 pm") == "22:00"
    assert parse_time_of_day("half past") == ""


def test_should_fire_only_in_the_window_and_once_per_day():
    setting = _setting()
    assert should_fire(setting, datetime(2026, 7, 15, 7, 0)) is True
    assert should_fire(setting, datetime(2026, 7, 15, 7, 4)) is True
    # Way past the window (app opened at night) must NOT retro-fire.
    assert should_fire(setting, datetime(2026, 7, 15, 21, 30)) is False
    # Before the time: no.
    assert should_fire(setting, datetime(2026, 7, 15, 6, 59)) is False
    # Already fired today: no.
    fired = _setting(last_fired_date="2026-07-15")
    assert should_fire(fired, datetime(2026, 7, 15, 7, 1)) is False


def test_should_fire_requires_ready_setting():
    assert should_fire(_setting(enabled=False), datetime(2026, 7, 15, 7, 0)) is False
    assert should_fire(_setting(station=None), datetime(2026, 7, 15, 7, 0)) is False
    assert should_fire(_setting(time_of_day=""), datetime(2026, 7, 15, 7, 0)) is False


def test_is_ready_property():
    assert _setting().is_ready is True
    assert WakeUpSetting().is_ready is False


def test_round_trip_and_defaults(tmp_path: Path):
    assert load_wake_setting(tmp_path).enabled is False
    setting = _setting(recurrence="once")
    save_wake_setting(tmp_path, setting)
    loaded = load_wake_setting(tmp_path)
    assert loaded.enabled is True
    assert loaded.time_of_day == "07:00"
    assert loaded.recurrence == "once"
    assert loaded.station is not None and loaded.station.name == "WQXR"


def test_load_wake_setting_corrupt_file_returns_defaults(tmp_path: Path):
    (tmp_path / "radio_wake_timer.json").write_text("not json", encoding="utf-8")
    assert load_wake_setting(tmp_path) == WakeUpSetting()


def test_load_wake_setting_invalid_recurrence_normalizes_to_once(tmp_path: Path):
    import json

    (tmp_path / "radio_wake_timer.json").write_text(
        json.dumps({"enabled": True, "time_of_day": "07:00", "recurrence": "monthly"}),
        encoding="utf-8",
    )
    assert load_wake_setting(tmp_path).recurrence == "once"


def test_spoken_summary_reads_naturally():
    assert "every day at 07:00" in _setting().spoken_summary()
    assert WakeUpSetting().spoken_summary() == "No wake-up timer is set."


# -- WakeUpWatcher (fast poll, no network) --------------------------------


def test_watcher_fires_once_and_disables_a_once_entry(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("quill_radio_mac.core.wake_timer._CHECK_SECONDS", 0.02)
    # 2 minutes in the past: already due (now >= time_of_day) and safely
    # inside the 5-minute window even if a minute ticks over mid-test.
    from datetime import timedelta

    due_time = (datetime.now() - timedelta(minutes=2)).strftime("%H:%M")
    save_wake_setting(tmp_path, _setting(recurrence="once", time_of_day=due_time))
    woken: list[RadioStation] = []
    watcher = WakeUpWatcher(tmp_path, on_wake=lambda station: woken.append(station))
    try:
        deadline = time.monotonic() + 3.0
        while not woken and time.monotonic() < deadline:
            time.sleep(0.02)
        assert woken and woken[0].name == "WQXR"
        reloaded = load_wake_setting(tmp_path)
        assert reloaded.enabled is False  # "once" disables itself after firing
        assert reloaded.last_fired_date
    finally:
        watcher.shutdown()
