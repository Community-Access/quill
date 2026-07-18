"""Tests for the Audio Studio sleep timer (Phase 2 port-in)."""

from __future__ import annotations

import time
from pathlib import Path

from quill.core.audio_studio.sleep_timer import (
    SleepTimerSetting,
    SleepTimerWatcher,
    load_sleep_setting,
    save_sleep_setting,
    should_fire,
)


def test_should_fire_after_delay() -> None:
    s = SleepTimerSetting(enabled=True, delay_minutes=1.0)
    assert should_fire(s, now=70.0, started_at=0.0) is True
    assert should_fire(s, now=50.0, started_at=0.0) is False


def test_disabled_never_fires() -> None:
    s = SleepTimerSetting(enabled=False, delay_minutes=1.0)
    assert should_fire(s, now=999.0, started_at=0.0) is False


def test_end_of_chapter_mode_suppresses_the_delay_watcher() -> None:
    # In end-of-chapter mode the host stops at the chapter boundary; the delay
    # watcher must not also fire and cut playback off mid-chapter.
    s = SleepTimerSetting(enabled=True, delay_minutes=1.0, end_of_chapter=True)
    assert should_fire(s, now=999.0, started_at=0.0) is False


def test_watcher_calls_on_sleep_once() -> None:
    fired: list[bool] = []
    w = SleepTimerWatcher(on_sleep=lambda: fired.append(True), check_interval=0.05)
    w.start(SleepTimerSetting(enabled=True, delay_minutes=0.02), now=0.0)
    time.sleep(0.2)
    assert fired == [True]
    w.shutdown()


def test_watcher_cancel_prevents_fire() -> None:
    fired: list[bool] = []
    w = SleepTimerWatcher(on_sleep=lambda: fired.append(True), check_interval=0.05)
    w.start(SleepTimerSetting(enabled=True, delay_minutes=0.02), now=0.0)
    w.cancel()
    time.sleep(0.2)
    assert fired == []
    w.shutdown()


def test_round_trip(tmp_path: Path) -> None:
    s = SleepTimerSetting(enabled=True, delay_minutes=45.0, end_of_chapter=True)
    save_sleep_setting(tmp_path, s)
    got = load_sleep_setting(tmp_path)
    assert got.enabled is True
    assert got.delay_minutes == 45.0
    assert got.end_of_chapter is True


def test_load_missing_returns_disabled(tmp_path: Path) -> None:
    got = load_sleep_setting(tmp_path)
    assert got.enabled is False
    assert got.delay_minutes == 30.0
