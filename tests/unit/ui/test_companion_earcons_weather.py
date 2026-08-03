"""Quill Weather cues an alert only when the alert is genuinely new (#1302).

The alert earcon rides the announcement the monitor already makes, gated on
``apply_poll`` reporting a fresh alert id. The point of these tests is what
does *not* sound: the baseline poll that records what is already in effect,
and every later poll that re-reports the same alert the user has already been
told about.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.sound_events import SoundEvent
from quill.core.weather import monitor
from quill.core.weather.models import WeatherAlert
from quill.ui.main_frame_weather import WeatherMixin


class _Host(WeatherMixin):
    def __init__(self, data_dir: Any) -> None:
        self._data_dir = data_dir
        location = SimpleNamespace(id="loc1", label="Springfield")
        self.location = location
        self.state = monitor.MonitorState()
        self._weather_monitor_states = {"loc1": self.state}
        self._weather_monitor_paused = False
        self._weather_monitor_round_pending = 1
        self._weather_monitor_round_active = False
        self._weather_monitor_baseline_counts: dict[str, int] = {}
        self.spoken: list[tuple[str, str]] = []
        self.alert_sounds = 0
        self.toasts: list[tuple[str, str]] = []

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.spoken.append((message, sound))

    def _play_weather_alert_sound(self) -> None:
        self.alert_sounds += 1

    def _show_weather_toast(self, title: str, body: str) -> None:
        self.toasts.append((title, body))

    def _finish_weather_monitor_round(self) -> None: ...

    def _weather_data_dir(self) -> Any:  # type: ignore[override]
        return self._data_dir

    def poll(self, alerts: list[WeatherAlert]) -> None:
        self._weather_monitor_round_pending = 1
        self._weather_monitor_poll_done(self.location, alerts)


@pytest.fixture
def host(tmp_path: Path) -> _Host:
    return _Host(tmp_path)


def _alert(alert_id: str, event: str = "Tornado Warning") -> WeatherAlert:
    return WeatherAlert(
        id=alert_id, event=event, severity="Extreme", urgency="Immediate", headline=f"{event}!"
    )


def test_the_baseline_poll_never_cues(host: _Host) -> None:
    host.poll([_alert("a1")])
    assert host.spoken == []  # baseline announces nothing at all
    assert host.alert_sounds == 0


def test_a_new_alert_cues_the_weather_alert_earcon(host: _Host) -> None:
    host.poll([])  # baseline: nothing active
    host.poll([_alert("a1")])
    assert [sound for _msg, sound in host.spoken] == [SoundEvent.WEATHER_ALERT]
    assert host.toasts


def test_repolling_the_same_alert_does_not_cue_again(host: _Host) -> None:
    host.poll([])
    host.poll([_alert("a1")])
    host.spoken.clear()
    for _ in range(5):
        host.poll([_alert("a1")])
    assert [sound for _msg, sound in host.spoken] == []


def test_an_all_clear_announces_without_the_alert_cue(host: _Host) -> None:
    host.poll([])
    host.poll([_alert("a1")])
    host.spoken.clear()
    host.poll([])
    assert host.spoken and all(sound == "" for _msg, sound in host.spoken)


def test_a_second_distinct_alert_cues_again(host: _Host) -> None:
    host.poll([])
    host.poll([_alert("a1")])
    host.spoken.clear()
    host.poll([_alert("a1"), _alert("a2", "Flash Flood Warning")])
    assert [sound for _msg, sound in host.spoken] == [SoundEvent.WEATHER_ALERT]
