"""The wx glue around feed health, driven with a fake host: a failed poll is
recorded as a failure (never an empty list), the one notice is announced and
toasted once, and the status report and its spoken summary come from the tracker."""

from __future__ import annotations

import time
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.weather import feed_health as fh
from quill.core.weather.models import WeatherAlert
from quill.core.weather.nws import WeatherError
from quill.ui.main_frame_weather_health import WeatherHealthMixin


class _Host(WeatherHealthMixin):
    def __init__(self, data_dir: Path, *, safe_mode: bool = False) -> None:
        self._dir = data_dir
        self._safe_mode = safe_mode
        self.said: list[tuple[str, bool]] = []
        self.toasts: list[tuple[str, str]] = []
        self._weather_monitor_locations: list[Any] = []
        self._tray_icon = None

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append((message, force))

    def _show_weather_toast(self, title: str, body: str) -> None:
        self.toasts.append((title, body))

    def _weather_data_dir(self) -> Path:  # type: ignore[override]
        return self._dir


HOME = SimpleNamespace(id="home", label="Home")


def _down() -> WeatherError:
    error = WeatherError("Could not reach the weather service")
    error.__cause__ = urllib.error.URLError("offline")
    return error


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    state = {"now": 1_800_000_000.0}
    monkeypatch.setattr(time, "time", lambda: state["now"])
    return state


def test_failed_poll_is_a_failure_not_an_empty_answer(
    tmp_path: Path, clock: dict[str, float]
) -> None:
    host = _Host(tmp_path)
    alert = WeatherAlert(id="a", event="Tornado Warning", severity="Extreme")
    assert host._weather_health_record(HOME, [alert]) is True
    clock["now"] += 300
    assert host._weather_health_record(HOME, _down()) is False
    health = host._weather_feed_tracker().places["home"]
    assert [a.event for a in health.last_alerts] == ["Tornado Warning"]
    assert health.consecutive_failures == 1


def test_notice_is_announced_and_toasted_once_then_recovery(
    tmp_path: Path, clock: dict[str, float]
) -> None:
    host = _Host(tmp_path)
    host._weather_health_record(HOME, [])
    for _ in range(4):
        clock["now"] += 240
        host._weather_health_record(HOME, _down())
        host._weather_health_round_end()
    warnings = [m for m, _f in host.said if "cannot reach" in m]
    assert len(warnings) == 1 and len(host.toasts) == 1
    assert host.said[0][1] is True  # forced: it must not wait behind other speech
    clock["now"] += 240
    host._weather_health_record(HOME, [])
    host._weather_health_round_end()
    assert "can reach the National Weather Service again" in host.said[-1][0]
    assert host.said[-1][1] is False


def test_health_survives_a_restart(tmp_path: Path, clock: dict[str, float]) -> None:
    first = _Host(tmp_path)
    first._weather_health_record(HOME, [])
    first._weather_health_round_end()
    again = _Host(tmp_path)
    assert again._weather_feed_tracker().places["home"].last_success == clock["now"]


def test_safe_mode_is_checks_off_not_unreachable(tmp_path: Path) -> None:
    host = _Host(tmp_path, safe_mode=True)
    assert "Safe Mode" in host._weather_feed_tracker().summary(time.time(), ["home"])
    assert host._weather_feed_tracker().end_of_round(time.time()) is None


def test_unchecked_notes_name_the_last_good_check(tmp_path: Path, clock: dict[str, float]) -> None:
    host = _Host(tmp_path)
    host._weather_health_record(HOME, [])
    notes = host._weather_health_unchecked_notes({"home": "Home", "new": "New"})
    assert "last successful check" in notes["Home"]
    assert notes["New"] == ""
    assert isinstance(fh.FeedState.NEVER, str)
