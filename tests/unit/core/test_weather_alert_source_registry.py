"""Tests for the Quillin weather alert-source registry and headless-check use."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from quill.core.weather import alert_source_registry, headless_check, monitor
from quill.core.weather import locations as loc_store
from quill.core.weather.locations import WeatherLocationStore
from quill.core.weather.models import WeatherAlert, WeatherLocation


@pytest.fixture(autouse=True)
def _clear() -> Iterator[None]:
    alert_source_registry.clear_sources()
    yield
    alert_source_registry.clear_sources()


def test_source_rows_become_weather_alerts() -> None:
    alert_source_registry.register_source(
        "ext.s", lambda: [{"id": "a1", "event": "Flood Watch", "severity": "Moderate"}]
    )
    alerts = alert_source_registry.alerts_from_sources()
    assert len(alerts) == 1
    assert isinstance(alerts[0], WeatherAlert)
    assert alerts[0].id == "a1"
    assert alerts[0].event == "Flood Watch"
    assert alerts[0].severity == "Moderate"


def test_rows_missing_id_or_event_dropped() -> None:
    alert_source_registry.register_source(
        "ext.s", lambda: [{"id": "", "event": "X"}, {"id": "b", "event": ""}]
    )
    assert alert_source_registry.alerts_from_sources() == []


def test_faulty_source_skipped() -> None:
    def _boom() -> list[dict[str, str]]:
        raise RuntimeError("boom")

    alert_source_registry.register_source("ext.bad", _boom)
    alert_source_registry.register_source("ext.good", lambda: [{"id": "g", "event": "E"}])
    assert [a.id for a in alert_source_registry.alerts_from_sources()] == ["g"]


def test_register_replaces_by_id() -> None:
    alert_source_registry.register_source("ext.s", lambda: [])
    alert_source_registry.register_source("ext.s", lambda: [])
    assert alert_source_registry.registered_source_ids() == ("ext.s",)


def _seed_location(data_dir: Path) -> None:
    store = WeatherLocationStore()
    store.add(
        WeatherLocation(display_name="Home", latitude=1.0, longitude=2.0, id="loc1"),
        make_primary=True,
    )
    loc_store.save_locations(data_dir, store)


def test_headless_check_merges_contributed_alerts(tmp_path: Path) -> None:
    _seed_location(tmp_path)
    # Prime the notified set so the first real check reports, not baselines.
    monitor.save_notified_ids(tmp_path, set())
    alert_source_registry.register_source(
        "ext.s", lambda: [{"id": "contrib-1", "event": "Community Advisory"}]
    )

    def _fetch(_lat: float, _lon: float) -> list[WeatherAlert]:
        return [WeatherAlert(id="nws-1", event="Tornado Warning")]

    result = headless_check.run_check(tmp_path, fetch_alerts=_fetch)
    ids = {a.id for a in result.new_alerts}
    assert "contrib-1" in ids
    assert "nws-1" in ids
