"""Report Fields: the catalogue, each field worded from the unit Open-Meteo
sent, the request asking for exactly the chosen fields, the order kept, and
unknown or repeated ids dropped from settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.weather import nowcast, report_extras
from quill.core.weather import settings as settings_mod
from quill.core.weather.models import WeatherLocation


def test_fields_follow_the_sent_units() -> None:
    word = nowcast.extra_field_text
    assert word("wind_gusts_10m", 22.4, "mp/h", metric=False) == "Wind gusts: 22 miles per hour."
    assert word("visibility", 52800, "ft", metric=False) == "Visibility: 10.0 miles."
    assert word("snow_depth", 0.5, "m", metric=True) == "Snow on the ground: 50 centimetres."
    assert word("snow_depth", 1.5, "ft", metric=False) == "Snow on the ground: 18 inches."
    assert word("freezing_level_height", 1200, "m", metric=True) == "Freezing level: 1,200 metres."
    assert word("soil_moisture_0_to_1cm", 0.31, "m³/m³", metric=True) == (
        "Soil moisture near the surface: 31 percent."
    )
    assert word("is_day", 0, "", metric=True) == "It is night."
    assert word("not_a_field", 1, "", metric=True) == ""
    assert word("wind_gusts_10m", 1.2, "mp/h", metric=False) == "Wind gusts: 1 mile per hour."
    assert word("precipitation", 1, "inch", metric=False) == (
        "Precipitation in the last 15 minutes: 1 inch."
    )
    assert word("sunshine_duration", 60, "s", metric=True) == "Sunshine this hour: 1 minute."
    assert word("precipitation", 0.04, "inch", metric=False) == (
        "Precipitation in the last 15 minutes: 0.04 inches."
    )


def test_the_request_asks_for_the_chosen_fields_only() -> None:
    url = nowcast.request_url(1, 2, unit="F", extra_fields=["cape", "not_a_field"])
    assert "current=temperature_2m%2Ccape&" in url and "not_a_field" not in url
    assert "current=temperature_2m&" in nowcast.request_url(1, 2, unit="F")


def test_the_report_reads_them_in_the_chosen_order() -> None:
    reply = {
        "current": {"time": "2026-11-27T15:30", "cape": 1200, "wind_gusts_10m": 30},
        "current_units": {"cape": "J/kg", "wind_gusts_10m": "mp/h"},
    }
    asked: list[str] = []

    def get(url: str, **_k: Any) -> Any:
        asked.append(url)
        return reply

    settings = settings_mod.WeatherSettings()
    settings.show_rain_soon = settings.show_glance_ahead = settings.show_daylight_change = False
    settings.show_pollen = settings.show_marine = False
    settings.report_fields = ["wind_gusts_10m", "cape"]
    home = WeatherLocation("Home", 32.2, -110.9, id="h")
    lines = report_extras.gather(home, settings, get=get).lines()
    assert lines == [
        "Wind gusts: 30 miles per hour. Thunderstorm energy (CAPE): 1200 joules per kilogram."
    ]
    assert len(asked) == 1 and "wind_gusts_10m" in asked[0]


def test_settings_keep_only_known_fields_once(tmp_path: Path) -> None:
    saved = settings_mod.WeatherSettings()
    saved.report_fields = ["cape", "bogus", "cape", "uv_index"]
    settings_mod.save_settings(tmp_path, saved)
    assert settings_mod.load_settings(tmp_path).report_fields == ["cape", "uv_index"]
