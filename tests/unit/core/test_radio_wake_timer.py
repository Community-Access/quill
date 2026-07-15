"""Tests for the wake-up timer's pure logic and persistence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from quill.core.radio.models import RadioStation
from quill.core.radio.wake_timer import (
    WakeUpSetting,
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


def test_parse_time_of_day_accepts_24h_and_12h() -> None:
    assert parse_time_of_day("07:30") == "07:30"
    assert parse_time_of_day("7:30 AM") == "07:30"
    assert parse_time_of_day("10 pm") == "22:00"
    assert parse_time_of_day("half past") == ""


def test_should_fire_only_in_the_window_and_once_per_day() -> None:
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


def test_should_fire_requires_ready_setting() -> None:
    assert should_fire(_setting(enabled=False), datetime(2026, 7, 15, 7, 0)) is False
    assert should_fire(_setting(station=None), datetime(2026, 7, 15, 7, 0)) is False
    assert should_fire(_setting(time_of_day=""), datetime(2026, 7, 15, 7, 0)) is False


def test_round_trip_and_defaults(tmp_path: Path) -> None:
    assert load_wake_setting(tmp_path).enabled is False
    setting = _setting(recurrence="once")
    save_wake_setting(tmp_path, setting)
    loaded = load_wake_setting(tmp_path)
    assert loaded.enabled is True
    assert loaded.time_of_day == "07:00"
    assert loaded.recurrence == "once"
    assert loaded.station is not None and loaded.station.name == "WQXR"


def test_spoken_summary_reads_naturally() -> None:
    assert "every day at 07:00" in _setting().spoken_summary()
    assert WakeUpSetting().spoken_summary() == "No wake-up timer is set."
