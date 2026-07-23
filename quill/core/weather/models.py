"""Normalized, wx-free weather value objects shared by the NWS client, the
locations store, and the UI. Deliberately small: the 2.1.0 slice needs a
location, its current conditions, a period forecast, and active alerts -- the
fuller PRD model (time-series, revisions, delivery history) comes later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Alert priority tiers, most severe first. Derived deterministically from the
#: NWS severity/urgency fields (never a hidden score -- see PRD 10.6).
ALERT_TIERS = ("Critical", "Urgent", "Important", "Advisory", "Informational")

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def friendly_date(iso_date: str) -> str:
    """'2026-07-20' -> 'July 20' (pure); returns the input unchanged if it does
    not parse, so a display never shows nothing."""
    try:
        _year, month, day = (int(part) for part in iso_date.split("-"))
    except (ValueError, AttributeError):
        return iso_date
    if not 1 <= month <= 12:
        return iso_date
    return f"{_MONTHS[month - 1]} {day}"


@dataclass(slots=True)
class WeatherLocation:
    """A saved place to show weather for. Coordinates are what NWS needs; the
    rest is resolved metadata kept for display and offline labeling."""

    display_name: str
    latitude: float
    longitude: float
    #: Human place name resolved from the geocoder ("Tucson, AZ"); falls back
    #: to display_name when a bare lat/lon was entered.
    resolved_name: str = ""
    state: str = ""
    #: What the user typed to create it ("85701", "Tucson, AZ", "32.2,-110.9").
    query: str = ""
    #: Stable id for the store / settings references.
    id: str = ""

    @property
    def label(self) -> str:
        return self.display_name or self.resolved_name or f"{self.latitude},{self.longitude}"

    @property
    def point(self) -> str:
        """The ``lat,lon`` string NWS point/alert endpoints expect."""
        return f"{self.latitude:.4f},{self.longitude:.4f}"


@dataclass(slots=True)
class CurrentConditions:
    """Latest observation from the nearest reporting station."""

    text_description: str = ""
    temperature_f: float | None = None
    temperature_c: float | None = None
    feels_like_f: float | None = None  # heat index or wind chill
    humidity_percent: float | None = None
    dewpoint_f: float | None = None
    wind_speed_mph: float | None = None
    wind_gust_mph: float | None = None
    wind_direction: str = ""
    pressure_inhg: float | None = None
    visibility_mi: float | None = None
    cloud_cover_percent: int | None = None
    station_id: str = ""
    observed_at: str = ""  # ISO 8601 from the provider


@dataclass(slots=True)
class ForecastPeriod:
    """One named NWS forecast period ("This Afternoon", "Tonight", ...)."""

    name: str
    temperature: int
    temperature_unit: str
    short_forecast: str
    detailed_forecast: str = ""
    wind_speed: str = ""
    wind_direction: str = ""
    precipitation_percent: int | None = None
    is_daytime: bool = True


@dataclass(slots=True)
class DailyOutlook:
    """One day of the extended daily outlook (beyond the NWS 7-day product)."""

    date: str  # ISO date, e.g. "2026-07-21"
    weekday: str  # "Monday"
    high_temp: int | None
    low_temp: int | None
    temperature_unit: str  # "F" or "C"
    condition: str  # human text from the weather code
    precipitation_percent: int | None = None
    sunrise: str = ""  # friendly local time, e.g. "5:42 AM"
    sunset: str = ""
    uv_index: int | None = None
    # -- moon (computed locally in quill.core.weather.astronomy; empty until
    #    the caller fills it in) --
    moon_phase: str = ""  # "Waxing Gibbous", ...
    moon_illumination_percent: int | None = None
    moonrise: str = ""  # friendly local time
    moonset: str = ""

    @property
    def line(self) -> str:
        """A self-contained, friendly, copyable one-line summary for the day."""
        hi = f"{self.high_temp}" if self.high_temp is not None else "unknown"
        lo = f"{self.low_temp}" if self.low_temp is not None else "unknown"
        when = f"{self.weekday}, {friendly_date(self.date)}"
        parts = [f"{when}: {self.condition}.", f"High {hi}, low {lo} degrees."]
        if self.precipitation_percent not in (None, 0):
            parts.append(f"{self.precipitation_percent} percent chance of precipitation.")
        if self.sunrise and self.sunset:
            parts.append(f"Sunrise {self.sunrise}, sunset {self.sunset}.")
        if self.moon_phase:
            moon = f"Moon {self.moon_phase.lower()}"
            if self.moon_illumination_percent is not None:
                moon += f", {self.moon_illumination_percent} percent lit"
            parts.append(moon + ".")
            if self.moonrise and self.moonset:
                parts.append(f"Moonrise {self.moonrise}, moonset {self.moonset}.")
        return " ".join(parts)


@dataclass(slots=True)
class HourlyPeriod:
    """One hour of the NWS hourly forecast (its forecastHourly product)."""

    time: str  # friendly local time, e.g. "3 PM"
    temperature: int
    temperature_unit: str  # "F" or "C"
    short_forecast: str
    precipitation_percent: int | None = None
    wind_speed: str = ""
    wind_direction: str = ""
    is_daytime: bool = True

    @property
    def line(self) -> str:
        """A self-contained, fully spoken one-line summary for the hour."""
        scale = "Fahrenheit" if self.temperature_unit == "F" else "Celsius"
        parts = [f"{self.time}: {self.temperature} degrees {scale}, {self.short_forecast}."]
        if self.precipitation_percent not in (None, 0):
            parts.append(f"{self.precipitation_percent} percent chance of precipitation.")
        return " ".join(parts)


@dataclass(slots=True)
class AirQuality:
    """Current air quality (Open-Meteo air-quality API)."""

    us_aqi: int | None = None
    category: str = ""  # "Good", "Moderate", ...
    pm2_5: float | None = None


@dataclass(slots=True)
class WeatherAlert:
    """A normalized active NWS alert (watch/warning/advisory)."""

    id: str
    event: str
    severity: str = ""  # Extreme | Severe | Moderate | Minor | Unknown
    urgency: str = ""  # Immediate | Expected | Future | Past | Unknown
    certainty: str = ""  # Observed | Likely | Possible | Unlikely | Unknown
    headline: str = ""
    description: str = ""
    instruction: str = ""
    area_description: str = ""
    effective: str = ""
    onset: str = ""
    expires: str = ""
    ends: str = ""
    sender_name: str = ""

    @property
    def tier(self) -> str:
        """A transparent priority tier from severity + urgency (PRD 10.6).
        Never suppresses -- only orders and labels."""
        sev, urg = self.severity.lower(), self.urgency.lower()
        if sev == "extreme" and urg in ("immediate", "expected"):
            return "Critical"
        if sev == "severe" and urg in ("immediate", "expected"):
            return "Urgent"
        if sev in ("extreme", "severe"):
            return "Important"
        if sev == "moderate":
            return "Advisory"
        return "Informational"

    @property
    def tier_rank(self) -> int:
        """0 = most severe; for sorting the Active Alerts list."""
        try:
            return ALERT_TIERS.index(self.tier)
        except ValueError:
            return len(ALERT_TIERS)


@dataclass(slots=True)
class WeatherReport:
    """Everything one Weather Now refresh gathered for a location."""

    location: WeatherLocation
    current: CurrentConditions | None = None
    periods: list[ForecastPeriod] = field(default_factory=list)
    #: Hour-by-hour forecast (NWS forecastHourly), nearest hours first.
    hourly: list[HourlyPeriod] = field(default_factory=list)
    #: Extended daily outlook (Open-Meteo), beyond the ~7-day NWS periods.
    daily: list[DailyOutlook] = field(default_factory=list)
    air_quality: AirQuality | None = None
    alerts: list[WeatherAlert] = field(default_factory=list)
    #: NWS forecast office id (e.g. "TWC") and resolved zone/county, for the
    #: source-status line the PRD requires.
    office: str = ""
    forecast_zone: str = ""
    county_zone: str = ""
    time_zone: str = ""  # IANA name, for showing observation times in local time
    retrieved_at: str = ""  # ISO 8601, stamped by the caller (wx-free: no clock here)
    #: Non-fatal notes (e.g. "observation unavailable"); shown in status.
    notes: list[str] = field(default_factory=list)

    @property
    def active_alert_count(self) -> int:
        return len(self.alerts)

    @property
    def highest_tier(self) -> str:
        """The most severe active alert's tier, or "" when there are none."""
        if not self.alerts:
            return ""
        return ALERT_TIERS[min(a.tier_rank for a in self.alerts)]
