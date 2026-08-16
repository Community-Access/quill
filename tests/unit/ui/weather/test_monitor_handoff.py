"""The watch belongs to one app.

The alert-monitor config is shared across the family (one data store), so a
host that offers "Open the Quill Weather App" must NOT auto-resume the watch
at launch -- otherwise Quill Radio and Quill Weather both poll the same
alerts and the radio opens by talking about the weather (reported 2026-08-15).
"""

from __future__ import annotations

from pathlib import Path

from quill.core.weather import monitor
from quill.ui.main_frame_weather import WeatherMixin


class _Host(WeatherMixin):
    def __init__(self, data_dir: Path, *, offers_app_launch: bool) -> None:
        self._safe_mode = False
        self._weather_offers_app_launch = offers_app_launch
        self._data_dir = data_dir
        self.resumed = False

    def _weather_data_dir(self) -> Path:  # type: ignore[override]
        return self._data_dir

    def start_weather_monitoring(self, *, announce: bool = True) -> None:  # type: ignore[override]
        self.resumed = True


def _enable_monitoring(data_dir: Path) -> None:
    config = monitor.load_config(data_dir)
    config.enabled = True
    monitor.save_config(data_dir, config)


def test_a_hand_off_host_never_resumes_the_shared_watch(tmp_path: Path) -> None:
    _enable_monitoring(tmp_path)
    host = _Host(tmp_path, offers_app_launch=True)  # Quill Radio's shape
    host.start_weather_monitoring_if_enabled()
    assert host.resumed is False


def test_the_watcher_host_still_resumes(tmp_path: Path) -> None:
    _enable_monitoring(tmp_path)
    host = _Host(tmp_path, offers_app_launch=False)  # the Quill Weather app's shape
    host.start_weather_monitoring_if_enabled()
    assert host.resumed is True
