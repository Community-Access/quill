"""QUILL Weather settings -- a rich, persisted preferences model (PRD 13).

Text-only 2.1.0 scope, but deliberately broad so the Settings surface feels
complete: units, what Weather Now shows and in what order, how many forecast
periods, the alert severity floor and event filters, the refresh cadence
(never below the NWS 30-second alert-poll floor), and the Quick Weather line's
composition. Speech-only fields (voices, earcons, interruption) are out of
scope until the speech phase and are intentionally absent rather than stubbed.

wx-free, strict-typed, JSON-persisted atomically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_STORE_NAME = "weather_settings.json"

TEMPERATURE_UNITS = ("F", "C")
WIND_UNITS = ("mph", "km/h", "kts", "m/s")
#: NWS asks for no more than one alert poll per 30 s (PRD 10.2); the UI floor.
MIN_REFRESH_MINUTES = 1
#: Severity floor options, least-to-most severe. "" (Unknown) is the lowest.
SEVERITY_FLOOR = ("all", "Minor", "Moderate", "Severe", "Extreme")


def _default_sections() -> list[str]:
    return ["alerts", "current", "forecast"]


@dataclass(slots=True)
class WeatherSettings:
    # -- units (PRD 11.5) --
    temperature_unit: str = "F"
    wind_unit: str = "mph"

    # -- Weather Now layout --
    #: Section order/visibility; a section absent from the list is hidden.
    section_order: list[str] = field(default_factory=_default_sections)
    #: 14 periods = the full ~7-day NWS forecast (day + night for each). NWS's
    #: public forecast product does not extend beyond about 7 days.
    forecast_period_count: int = 14
    show_detailed_forecast: bool = True
    #: Extended daily outlook length (Open-Meteo), for reaching past NWS's 7
    #: days. 0 disables it; capped at 16 (Open-Meteo's own limit).
    daily_outlook_days: int = 10

    # -- current-conditions data points to include (all on by default;
    #    temperature and the sky condition always show) --
    show_feels_like: bool = True
    show_humidity: bool = True
    show_dew_point: bool = True
    show_wind: bool = True
    show_pressure: bool = True
    show_visibility: bool = True
    show_cloud_cover: bool = True
    show_precip_chance: bool = True
    show_sunrise_sunset: bool = True
    show_uv_index: bool = True
    show_air_quality: bool = True

    # -- alerts (PRD 13.3) --
    #: Only show alerts at or above this severity ("all" shows every one).
    alert_severity_floor: str = "all"
    #: Event names to hide even if above the floor (e.g. "Special Weather
    #: Statement"); matched case-insensitively.
    muted_events: list[str] = field(default_factory=list)
    announce_alert_count_on_open: bool = True

    # -- refresh --
    refresh_minutes: int = 15
    refresh_on_open: bool = True

    # -- Quick Weather line composition (PRD 6.2) --
    quick_include_feels_like: bool = True
    quick_include_wind: bool = True
    quick_include_humidity: bool = False
    quick_include_alert_count: bool = True
    quick_include_data_age: bool = True

    def normalized(self) -> WeatherSettings:
        """Clamp every field to a legal value (defensive after load/edit)."""
        self.temperature_unit = (
            self.temperature_unit if self.temperature_unit in TEMPERATURE_UNITS else "F"
        )
        self.wind_unit = self.wind_unit if self.wind_unit in WIND_UNITS else "mph"
        self.forecast_period_count = max(1, min(14, int(self.forecast_period_count)))
        self.daily_outlook_days = max(0, min(16, int(self.daily_outlook_days)))
        self.alert_severity_floor = (
            self.alert_severity_floor if self.alert_severity_floor in SEVERITY_FLOOR else "all"
        )
        self.refresh_minutes = max(MIN_REFRESH_MINUTES, min(180, int(self.refresh_minutes)))
        allowed = {"alerts", "current", "forecast"}
        seen: list[str] = []
        for name in self.section_order:
            if name in allowed and name not in seen:
                seen.append(name)
        self.section_order = seen or _default_sections()
        self.muted_events = [str(e).strip() for e in self.muted_events if str(e).strip()]
        return self

    def alert_passes(self, severity: str, event: str) -> bool:
        """Whether an alert of this severity/event clears the user's filters."""
        if any(event.strip().lower() == m.lower() for m in self.muted_events):
            return False
        if self.alert_severity_floor == "all":
            return True
        floor = SEVERITY_FLOOR.index(self.alert_severity_floor)
        rank = SEVERITY_FLOOR.index(severity) if severity in SEVERITY_FLOOR else 0
        return rank >= floor


def _store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


def load_settings(data_dir: Path) -> WeatherSettings:
    """Read settings (absent or broken reads as defaults), always normalized."""
    import json

    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return WeatherSettings()
    if not isinstance(raw, dict):
        return WeatherSettings()
    s = WeatherSettings()
    for f in (
        "temperature_unit",
        "wind_unit",
        "alert_severity_floor",
    ):
        if isinstance(raw.get(f), str):
            setattr(s, f, raw[f])
    for f in ("forecast_period_count", "refresh_minutes", "daily_outlook_days"):
        if isinstance(raw.get(f), (int, float)):
            setattr(s, f, int(raw[f]))
    for f in (
        "show_detailed_forecast",
        "show_feels_like",
        "show_humidity",
        "show_dew_point",
        "show_wind",
        "show_pressure",
        "show_visibility",
        "show_cloud_cover",
        "show_precip_chance",
        "show_sunrise_sunset",
        "show_uv_index",
        "show_air_quality",
        "announce_alert_count_on_open",
        "refresh_on_open",
        "quick_include_feels_like",
        "quick_include_wind",
        "quick_include_humidity",
        "quick_include_alert_count",
        "quick_include_data_age",
    ):
        if isinstance(raw.get(f), bool):
            setattr(s, f, raw[f])
    if isinstance(raw.get("section_order"), list):
        s.section_order = [str(x) for x in raw["section_order"]]
    if isinstance(raw.get("muted_events"), list):
        s.muted_events = [str(x) for x in raw["muted_events"]]
    return s.normalized()


def save_settings(data_dir: Path, settings: WeatherSettings) -> None:
    """Persist settings atomically."""
    from quill.core.storage import write_json_atomic

    settings.normalized()
    write_json_atomic(
        _store_path(data_dir),
        {
            "temperature_unit": settings.temperature_unit,
            "wind_unit": settings.wind_unit,
            "section_order": list(settings.section_order),
            "forecast_period_count": settings.forecast_period_count,
            "daily_outlook_days": settings.daily_outlook_days,
            "show_detailed_forecast": settings.show_detailed_forecast,
            "show_feels_like": settings.show_feels_like,
            "show_humidity": settings.show_humidity,
            "show_dew_point": settings.show_dew_point,
            "show_wind": settings.show_wind,
            "show_pressure": settings.show_pressure,
            "show_visibility": settings.show_visibility,
            "show_cloud_cover": settings.show_cloud_cover,
            "show_precip_chance": settings.show_precip_chance,
            "show_sunrise_sunset": settings.show_sunrise_sunset,
            "show_uv_index": settings.show_uv_index,
            "show_air_quality": settings.show_air_quality,
            "alert_severity_floor": settings.alert_severity_floor,
            "muted_events": list(settings.muted_events),
            "announce_alert_count_on_open": settings.announce_alert_count_on_open,
            "refresh_minutes": settings.refresh_minutes,
            "refresh_on_open": settings.refresh_on_open,
            "quick_include_feels_like": settings.quick_include_feels_like,
            "quick_include_wind": settings.quick_include_wind,
            "quick_include_humidity": settings.quick_include_humidity,
            "quick_include_alert_count": settings.quick_include_alert_count,
            "quick_include_data_age": settings.quick_include_data_age,
        },
    )
