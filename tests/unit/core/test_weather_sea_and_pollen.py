"""Pollen (Europe only) and the sea (coastal only): parsing, the words, no
request outside Europe, one request for an inland place, and failures said."""

from __future__ import annotations

import urllib.error
from typing import Any

from quill.core.weather import report_extras, sea_and_pollen
from quill.core.weather.models import WeatherLocation
from quill.core.weather.settings import WeatherSettings


def test_pollen_is_europe_only() -> None:
    calls: list[str] = []
    assert sea_and_pollen.fetch_pollen(32, -110, get=lambda u, **k: calls.append(u)) is None
    assert calls == []
    pollen = sea_and_pollen.parse_pollen({"current": {"birch_pollen": 120.0, "grass_pollen": 4.0}})
    assert sea_and_pollen.pollen_text(pollen) == "Pollen: birch high, grass low."
    zero = sea_and_pollen.parse_pollen({"current": {"birch_pollen": 0.0}})
    assert sea_and_pollen.pollen_text(zero) == "Pollen: none in the air right now."
    assert sea_and_pollen.parse_pollen({"current": {"birch_pollen": None}}) is None


def test_marine_inland_is_none_and_coast_is_words() -> None:
    assert sea_and_pollen.parse_marine({"current": {"wave_height": None}}) is None
    marine = sea_and_pollen.parse_marine({
        "current": {
            "wave_height": 3.0,
            "wave_direction": 282,
            "wave_period": 13.7,
            "swell_wave_height": 2.98,
            "sea_surface_temperature": 19.2,
        }
    })
    assert sea_and_pollen.marine_text(marine) == (
        "Sea: waves 10 feet from the west every 14 seconds, swell 10 feet, "
        "sea temperature 67 degrees."
    )
    assert sea_and_pollen.marine_text(marine, metric=True) == (
        "Sea: waves 3 metres from the west every 14 seconds, swell 3 metres, "
        "sea temperature 19 degrees."
    )


def _quiet_nowcast() -> WeatherSettings:
    settings = WeatherSettings()
    settings.show_rain_soon = settings.show_glance_ahead = settings.show_daylight_change = False
    return settings


def test_inland_is_asked_once_and_failures_are_said() -> None:
    report_extras.forget_inland()
    tucson = WeatherLocation("Tucson", 32.2, -110.9, id="t")
    asked: list[str] = []

    def get(url: str, **_k: Any) -> Any:
        asked.append(url)
        return {"current": {"wave_height": None}}

    settings = _quiet_nowcast()
    assert report_extras.gather(tucson, settings, get=get).lines() == []
    report_extras.gather(tucson, settings, get=get)
    assert sum("marine-api" in u for u in asked) == 1
    assert not any("air-quality" in u for u in asked)  # not in Europe

    def down(url: str, **_k: Any) -> Any:
        raise urllib.error.URLError("down")

    berlin = WeatherLocation("Berlin", 52.5, 13.4, id="b")
    lines = report_extras.gather(berlin, settings, get=down).lines()
    assert lines[0].startswith("Pollen: Quill Weather could not get this")
    assert lines[1].startswith("Sea conditions: Quill Weather could not get this")
    report_extras.forget_inland()


def test_pollen_and_sea_switches() -> None:
    report_extras.forget_inland()
    berlin = WeatherLocation("Berlin", 52.5, 13.4, id="b")
    settings = _quiet_nowcast()
    settings.show_pollen = settings.show_marine = False
    asked: list[str] = []
    assert report_extras.gather(berlin, settings, get=lambda u, **k: asked.append(u)).lines() == []
    assert asked == []
