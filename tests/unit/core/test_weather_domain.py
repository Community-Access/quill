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


def test_temp_and_wind_units() -> None:
    f = WeatherSettings(temperature_unit="F", wind_unit="mph")
    c = WeatherSettings(temperature_unit="C", wind_unit="km/h")
    assert render.temp_str(212.0, f) == "212 deg F"
    assert render.temp_str(212.0, c) == "100 deg C"
    assert render.wind_str(10.0, "NW", f) == "NW 10 mph"
    assert render.wind_str(10.0, "NW", c) == "NW 16 km/h"
    assert render.wind_str(0.0, "NW", f) == "calm"


def test_quick_weather_line_composes_by_toggles() -> None:
    report = _report_with_current()
    s = WeatherSettings(
        quick_include_wind=True, quick_include_humidity=False, quick_include_alert_count=True
    )
    line = render.quick_weather_line(report, s)
    assert line.startswith("Tucson, AZ.")
    assert "96 deg F and clear" in line
    assert "Wind WNW 5 mph" in line
    assert "1 active alert; highest is Excessive Heat Warning" in line
    assert "Humidity" not in line  # toggle off


def test_quick_weather_line_no_alerts() -> None:
    report = _report_with_current()
    report.alerts = []
    line = render.quick_weather_line(report, WeatherSettings())
    assert "No active alerts." in line


def test_filtered_alerts_applies_settings() -> None:
    report = _report_with_current()
    report.alerts = [
        WeatherAlert("a", "Tornado Warning", "Extreme", "Immediate"),
        WeatherAlert("b", "Heat Advisory", "Moderate", "Expected"),
    ]
    s = WeatherSettings(alert_severity_floor="Severe")
    kept = render.filtered_alerts(report, s)
    assert [a.event for a in kept] == ["Tornado Warning"]


def test_current_conditions_line() -> None:
    c = CurrentConditions(
        text_description="Clear",
        temperature_f=96.0,
        wind_speed_mph=5.0,
        wind_direction="WNW",
        humidity_percent=20,
    )
    line = render.current_conditions_line(c, WeatherSettings())
    assert line == "Clear, 96 deg F, wind WNW 5 mph, humidity 20 percent"
    assert render.current_conditions_line(CurrentConditions(), WeatherSettings()).startswith(
        "No current"
    )
