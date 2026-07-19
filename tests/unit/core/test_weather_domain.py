"""QUILL Weather domain: models, settings filtering/clamping, the locations
store, and deterministic text rendering. All pure -- no network, no wx."""

from __future__ import annotations

from quill.core.weather import locations as loc_store
from quill.core.weather import render
from quill.core.weather import settings as settings_mod
from quill.core.weather.models import (
    CurrentConditions,
    ForecastPeriod,
    WeatherAlert,
    WeatherLocation,
    WeatherReport,
)
from quill.core.weather.settings import WeatherSettings

# -- models -------------------------------------------------------------------


def test_alert_tier_mapping() -> None:
    assert WeatherAlert("i", "Tornado Warning", "Extreme", "Immediate").tier == "Critical"
    assert WeatherAlert("i", "Flash Flood Warning", "Severe", "Expected").tier == "Urgent"
    assert WeatherAlert("i", "Winter Storm Warning", "Severe", "Future").tier == "Important"
    assert WeatherAlert("i", "Heat Advisory", "Moderate", "Expected").tier == "Advisory"
    assert WeatherAlert("i", "Special Statement", "Minor", "Future").tier == "Informational"


def test_report_alert_counts_and_highest_tier() -> None:
    report = WeatherReport(
        location=WeatherLocation("Home", 1, 2),
        alerts=[
            WeatherAlert("a", "Heat Advisory", "Moderate", "Expected"),
            WeatherAlert("b", "Tornado Warning", "Extreme", "Immediate"),
        ],
    )
    assert report.active_alert_count == 2
    assert report.highest_tier == "Critical"
    empty = WeatherReport(location=WeatherLocation("Home", 1, 2))
    assert empty.highest_tier == ""


def test_location_point_and_label() -> None:
    loc = WeatherLocation("Home", 32.21389, -110.96944, resolved_name="Tucson, AZ")
    assert loc.point == "32.2139,-110.9694"
    assert loc.label == "Home"
    assert WeatherLocation("", 1.0, 2.0).label == "1.0,2.0"


# -- settings -----------------------------------------------------------------


def test_settings_normalized_clamps_everything() -> None:
    s = WeatherSettings(
        temperature_unit="K",
        wind_unit="furlongs",
        forecast_period_count=99,
        refresh_minutes=0,
        alert_severity_floor="bogus",
        section_order=["forecast", "forecast", "bogus", "alerts"],
    ).normalized()
    assert s.temperature_unit == "F" and s.wind_unit == "mph"
    assert s.forecast_period_count == 14 and s.refresh_minutes == 1
    assert s.alert_severity_floor == "all"
    assert s.section_order == ["forecast", "alerts"]  # de-duped, junk dropped


def test_settings_alert_passes_floor_and_mute() -> None:
    s = WeatherSettings(alert_severity_floor="Severe", muted_events=["Special Weather Statement"])
    assert s.alert_passes("Extreme", "Tornado Warning") is True
    assert s.alert_passes("Severe", "Flash Flood Warning") is True
    assert s.alert_passes("Moderate", "Heat Advisory") is False  # below floor
    assert s.alert_passes("Extreme", "Special Weather Statement") is False  # muted
    assert WeatherSettings().alert_passes("Minor", "anything") is True  # "all" floor


def test_settings_round_trip(tmp_path) -> None:
    s = WeatherSettings(
        temperature_unit="C",
        wind_unit="kts",
        forecast_period_count=5,
        alert_severity_floor="Moderate",
        muted_events=["Frost Advisory"],
        refresh_minutes=30,
        quick_include_humidity=True,
    )
    settings_mod.save_settings(tmp_path, s)
    back = settings_mod.load_settings(tmp_path)
    assert back.temperature_unit == "C" and back.wind_unit == "kts"
    assert back.forecast_period_count == 5 and back.alert_severity_floor == "Moderate"
    assert back.muted_events == ["Frost Advisory"] and back.refresh_minutes == 30
    assert back.quick_include_humidity is True


def test_settings_missing_file_is_defaults(tmp_path) -> None:
    assert settings_mod.load_settings(tmp_path).temperature_unit == "F"


# -- locations store ----------------------------------------------------------


def test_locations_add_first_is_primary_and_move() -> None:
    store = loc_store.WeatherLocationStore()
    a = store.add(WeatherLocation("Home", 1, 2))
    b = store.add(WeatherLocation("Work", 3, 4))
    assert store.primary_id == a.id and store.primary().display_name == "Home"
    assert a.id != b.id
    assert store.set_primary(b.id) and store.primary().display_name == "Work"
    assert store.move(b.id, delta=-1)  # Work now first
    assert [loc.display_name for loc in store.locations] == ["Work", "Home"]


def test_locations_remove_reassigns_primary() -> None:
    store = loc_store.WeatherLocationStore()
    a = store.add(WeatherLocation("Home", 1, 2))
    b = store.add(WeatherLocation("Work", 3, 4))
    assert store.remove(a.id)
    assert store.primary_id == b.id


def test_locations_contains_point() -> None:
    store = loc_store.WeatherLocationStore()
    store.add(WeatherLocation("Home", 32.2139, -110.9694))
    assert store.contains_point(32.2139, -110.9694)
    assert not store.contains_point(40.0, -80.0)


def test_locations_round_trip(tmp_path) -> None:
    store = loc_store.WeatherLocationStore()
    store.add(
        WeatherLocation("Home", 32.2, -110.9, resolved_name="Tucson, AZ", state="AZ", query="85701")
    )
    store.add(WeatherLocation("Work", 30.27, -97.74))
    store.set_primary(store.locations[1].id)
    loc_store.save_locations(tmp_path, store)
    back = loc_store.load_locations(tmp_path)
    assert [loc.display_name for loc in back.locations] == ["Home", "Work"]
    assert back.primary().display_name == "Work"
    assert back.locations[0].resolved_name == "Tucson, AZ"


# -- render -------------------------------------------------------------------


def _report_with_current() -> WeatherReport:
    return WeatherReport(
        location=WeatherLocation("Home", 32.2, -110.9, resolved_name="Tucson, AZ"),
        current=CurrentConditions(
            text_description="Clear",
            temperature_f=96.0,
            wind_speed_mph=5.0,
            wind_direction="WNW",
            humidity_percent=20,
        ),
        periods=[ForecastPeriod("This Afternoon", 96, "F", "Hot")],
        alerts=[WeatherAlert("a", "Excessive Heat Warning", "Severe", "Expected")],
    )


def test_temp_and_wind_phrases_are_spelled_out() -> None:
    f = WeatherSettings(temperature_unit="F", wind_unit="mph")
    c = WeatherSettings(temperature_unit="C", wind_unit="km/h")
    assert render.temp_phrase(212.0, f) == "212 degrees Fahrenheit"
    assert render.temp_phrase(212.0, c) == "100 degrees Celsius"
    assert render.temp_phrase(98.0, f, with_unit=False) == "98 degrees"
    assert (
        render.wind_phrase(10.0, "WNW", None, f)
        == "The wind is blowing from the west-northwest at 10 miles per hour."
    )
    assert "gusting to 22 miles per hour" in render.wind_phrase(10.0, "NW", 22.0, f)
    assert render.wind_phrase(0.0, "NW", None, f) == "The air is calm."


def test_uv_and_air_quality_phrases() -> None:
    from quill.core.weather.models import AirQuality

    assert "very high" in render.uv_phrase(9)
    assert render.uv_phrase(None) == ""
    assert render.air_quality_phrase(AirQuality(us_aqi=42, category="Good")) == (
        "The air quality index is 42, which is good."
    )
    assert render.air_quality_phrase(None) == ""


def test_friendly_datetime() -> None:
    assert render.friendly_datetime("2026-07-19T18:30:00-07:00") == "July 19 at 6:30 PM"
    assert render.friendly_datetime("2026-07-19T05:05") == "July 19 at 5:05 AM"
    assert render.friendly_datetime("bad") == ""


def test_current_conditions_block_is_complete_and_toggleable() -> None:
    from quill.core.weather.models import AirQuality, DailyOutlook

    current = CurrentConditions(
        text_description="Clear",
        temperature_f=96.0,
        feels_like_f=101.0,
        humidity_percent=20,
        dewpoint_f=54.0,
        wind_speed_mph=5.0,
        wind_direction="WNW",
        wind_gust_mph=15.0,
        pressure_inhg=29.92,
        visibility_mi=10.0,
        cloud_cover_percent=5,
    )
    today = DailyOutlook(
        "2026-07-20",
        "Monday",
        98,
        75,
        "F",
        "Clear",
        precipitation_percent=10,
        sunrise="5:42 AM",
        sunset="7:38 PM",
        uv_index=9,
    )
    aq = AirQuality(us_aqi=42, category="Good")
    block = render.current_conditions_block(current, today, WeatherSettings(), aq)
    for want in (
        "96 degrees Fahrenheit and clear",
        "It feels like 101 degrees",
        "humidity is 20 percent",
        "dew point is 54 degrees",
        "west-northwest at 5 miles per hour, gusting to 15",
        "Cloud cover is 5 percent",
        "29.92 inches of mercury",
        "Visibility is 10 miles",
        "10 percent chance of precipitation",
        "sun rises at 5:42 AM and sets at 7:38 PM",
        "ultraviolet index reaches 9",
        "air quality index is 42",
    ):
        assert want in block, want
    # a toggle off removes exactly that point
    off = WeatherSettings(show_air_quality=False, show_uv_index=False)
    block2 = render.current_conditions_block(current, today, off, aq)
    assert "air quality" not in block2 and "ultraviolet" not in block2


def test_quick_weather_line_is_friendly() -> None:
    report = _report_with_current()
    line = render.quick_weather_line(report, WeatherSettings())
    assert line.startswith("Here is the weather for Tucson, AZ.")
    assert "It is 96 degrees Fahrenheit and clear." in line
    assert "The most urgent is a Excessive Heat Warning." in line


def test_quick_weather_line_no_alerts() -> None:
    report = _report_with_current()
    report.alerts = []
    line = render.quick_weather_line(report, WeatherSettings())
    assert "There are no active alerts." in line


def test_filtered_alerts_applies_settings() -> None:
    report = _report_with_current()
    report.alerts = [
        WeatherAlert("a", "Tornado Warning", "Extreme", "Immediate"),
        WeatherAlert("b", "Heat Advisory", "Moderate", "Expected"),
    ]
    s = WeatherSettings(alert_severity_floor="Severe")
    kept = render.filtered_alerts(report, s)
    assert [a.event for a in kept] == ["Tornado Warning"]
