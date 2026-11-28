"""A Weather file with 1e309 or NaN in it never stops the app (report.md A3):
the alert watch keeps its defaults and keeps the damaged file, feed health
reads the number as unknown, a place off the globe is left out, and a snooze
time of infinity is ignored."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import settings_recovery
from quill.core.weather import feed_health_store, locations, monitor, place_watch


@pytest.fixture(autouse=True)
def _fresh_launch():
    settings_recovery._forget()
    yield
    settings_recovery._forget()


def test_the_alert_watch_keeps_defaults_and_the_damaged_file(tmp_path: Path) -> None:
    (tmp_path / "weather_monitor.json").write_text(
        '{"enabled": true, "interval_minutes": 1e309, "fast_interval_seconds": NaN}',
        encoding="utf-8",
    )
    config = monitor.load_config(tmp_path)
    defaults = monitor.MonitorConfig().normalized()
    assert config.enabled is True
    assert config.interval_minutes == defaults.interval_minutes
    assert config.fast_interval_seconds == defaults.fast_interval_seconds
    kept = list(tmp_path.glob("weather_monitor.damaged-*.json"))
    assert len(kept) == 1
    notice = settings_recovery.take_notice("Quill Weather")
    assert "alert watch settings could not be read" in notice and kept[0].name in notice


def test_feed_health_reads_infinity_as_unknown(tmp_path: Path) -> None:
    (tmp_path / "weather_feed_health.json").write_text(
        '{"version": 1, "warned_at": 1e309, "places": [{"place_id": "x", '
        '"last_success": 1e309, "consecutive_failures": 1e309}]}',
        encoding="utf-8",
    )
    tracker = feed_health_store.load_tracker(tmp_path)
    health = tracker.places["x"]
    assert tracker.warned_at is None and health.last_success is None
    assert health.consecutive_failures == 0


def test_a_place_off_the_globe_is_left_out(tmp_path: Path) -> None:
    (tmp_path / "weather_locations.json").write_text(
        '{"locations": [{"display_name": "Nowhere", "latitude": 1e309, "longitude": 2, '
        '"id": "x"}, {"display_name": "Home", "latitude": 32.2, "longitude": -110.9, '
        '"id": "h"}]}',
        encoding="utf-8",
    )
    assert [loc.id for loc in locations.load_locations(tmp_path).locations] == ["h"]


def test_an_infinite_snooze_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "weather_place_watch.json").write_text(
        '{"version": 1, "places": {"x": {"snooze_until": 1e309, "until": NaN}}}',
        encoding="utf-8",
    )
    rule = place_watch.load_watches(tmp_path).rules["x"]
    assert rule.snooze_until is None and rule.until is None
