"""Open-Meteo daily outlook -- the extended (up to 16-day) forecast NWS does
not provide. Free, no account, no API key (https://open-meteo.com). Used only
to reach further out than the NWS ~7-day period forecast; NWS remains the
source for current conditions, the rich period narrative, and alerts.

wx-free, strict-typed, HTTPS-only, egress-audited (shares the weather
``_http.http_json`` chokepoint), Safe-Mode-gated.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.weather._http import HTTP_ERRORS, http_json
from quill.core.weather.models import (
    AirQuality,
    CurrentConditions,
    DailyOutlook,
    WeatherLocation,
    WeatherReport,
)

#: WMO weather interpretation codes -> plain text (Open-Meteo's daily code).
_WMO_TEXT: dict[int, str] = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Freezing fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Showers",
    82: "Violent showers",
    85: "Light snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class OpenMeteoError(CodedError):
    """An Open-Meteo request failed (network, Safe Mode, or bad response)."""

    code = "QUILL-WEATHER-OPENMETEO-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    if safe_mode:
        raise OpenMeteoError("Weather is a network service and is disabled in Safe Mode.")


def weather_code_text(code: object) -> str:
    """WMO code -> human text; unknown codes read as 'Unknown'."""
    if isinstance(code, bool) or not isinstance(code, (int, float, str)):
        return "Unknown"
    try:
        return _WMO_TEXT.get(int(code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


def weekday_name(iso_date: str) -> str:
    """Weekday for an ISO ``YYYY-MM-DD`` (pure, no clock -- Zeller's congruence)."""
    try:
        year, month, day = (int(part) for part in iso_date.split("-"))
    except (ValueError, AttributeError):
        return ""
    if month < 3:
        month += 12
        year -= 1
    k, j = year % 100, year // 100
    # Zeller's congruence: h = 0 => Saturday.
    h = (day + (13 * (month + 1)) // 5 + k + k // 4 + j // 4 + 5 * j) % 7
    return ("Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday")[h]


def format_time(iso: object) -> str:
    """'2026-07-21T05:42' -> '5:42 AM' (pure, no clock). '' on anything odd."""
    if not isinstance(iso, str) or "T" not in iso:
        return ""
    clock = iso.split("T", 1)[1][:5]
    try:
        hour, minute = (int(part) for part in clock.split(":"))
    except (ValueError, IndexError):
        return ""
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def daily_from_json(data: object, *, unit: str) -> list[DailyOutlook]:
    """Parse an Open-Meteo daily block into DailyOutlook rows (pure)."""
    daily = data.get("daily") if isinstance(data, dict) else None
    if not isinstance(daily, dict):
        return []
    times = daily.get("time") or []
    codes = daily.get("weathercode") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_probability_max") or []
    sunrises = daily.get("sunrise") or []
    sunsets = daily.get("sunset") or []
    uv = daily.get("uv_index_max") or []
    rows: list[DailyOutlook] = []
    for i, date in enumerate(times):
        if not isinstance(date, str):
            continue
        rows.append(
            DailyOutlook(
                date=date,
                weekday=weekday_name(date),
                high_temp=_int_at(highs, i),
                low_temp=_int_at(lows, i),
                temperature_unit=unit,
                condition=weather_code_text(codes[i]) if i < len(codes) else "Unknown",
                precipitation_percent=_int_at(precip, i),
                sunrise=format_time(sunrises[i]) if i < len(sunrises) else "",
                sunset=format_time(sunsets[i]) if i < len(sunsets) else "",
                uv_index=_int_at(uv, i),
            )
        )
    return rows


def _int_at(values: object, index: int) -> int | None:
    if isinstance(values, list) and index < len(values):
        value = values[index]
        if isinstance(value, (int, float)):
            return round(value)
    return None


@dataclass(slots=True)
class OpenMeteoData:
    """The Open-Meteo forecast pieces: the extended daily outlook, plus the
    current cloud cover (a data point NWS observations don't expose cleanly)."""

    daily: list[DailyOutlook]
    cloud_cover_percent: int | None = None


def fetch(
    latitude: float,
    longitude: float,
    *,
    days: int = 10,
    unit: str = "F",
    safe_mode: bool = False,
) -> OpenMeteoData:
    """One Open-Meteo forecast call: the up-to-16-day daily outlook plus current
    cloud cover. ``unit`` is 'F' or 'C'."""
    refuse_in_safe_mode(safe_mode)
    days = max(1, min(16, days))
    query = urllib.parse.urlencode({
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": "cloud_cover",
        "daily": (
            "weathercode,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,sunrise,sunset,uv_index_max"
        ),
        "temperature_unit": "celsius" if unit == "C" else "fahrenheit",
        "timezone": "auto",
        "forecast_days": days,
    })
    try:
        data = http_json(f"https://api.open-meteo.com/v1/forecast?{query}")
    except HTTP_ERRORS as error:
        raise OpenMeteoError(f"Could not reach the extended-forecast service: {error}") from error
    current = data.get("current") if isinstance(data, dict) else None
    cloud = current.get("cloud_cover") if isinstance(current, dict) else None
    return OpenMeteoData(
        daily=daily_from_json(data, unit=unit),
        cloud_cover_percent=round(cloud) if isinstance(cloud, (int, float)) else None,
    )


def _to_fahrenheit(value: object, unit: str) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return round(float(value) * 9 / 5 + 32, 1) if unit == "C" else round(float(value), 1)


def _to_celsius(value: object, unit: str) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return round((float(value) - 32) * 5 / 9, 1) if unit == "F" else round(float(value), 1)


def _compass(degrees: object) -> str:
    """Wind direction in degrees -> 8-point compass label (empty if unknown)."""
    if not isinstance(degrees, (int, float)) or isinstance(degrees, bool):
        return ""
    points = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return points[round(float(degrees) / 45) % 8]


def fetch_report(
    location: WeatherLocation, *, unit: str = "F", days: int = 10, safe_mode: bool = False
) -> WeatherReport:
    """A complete worldwide report from Open-Meteo alone -- current conditions
    plus the daily outlook -- for locations outside the NWS's US coverage
    (#1187). No NWS-style period narrative or alerts (those are US-only)."""
    refuse_in_safe_mode(safe_mode)
    days = max(1, min(16, days))
    query = urllib.parse.urlencode({
        "latitude": f"{location.latitude:.4f}",
        "longitude": f"{location.longitude:.4f}",
        "current": (
            "temperature_2m,apparent_temperature,relative_humidity_2m,"
            "weather_code,wind_speed_10m,wind_direction_10m,cloud_cover"
        ),
        "daily": (
            "weathercode,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,sunrise,sunset,uv_index_max"
        ),
        "temperature_unit": "celsius" if unit == "C" else "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": days,
    })
    try:
        data = http_json(f"https://api.open-meteo.com/v1/forecast?{query}")
    except HTTP_ERRORS as error:
        raise OpenMeteoError(f"Could not reach the worldwide forecast service: {error}") from error
    cur = data.get("current") if isinstance(data, dict) else None
    current: CurrentConditions | None = None
    if isinstance(cur, dict):
        humidity = cur.get("relative_humidity_2m")
        wind = cur.get("wind_speed_10m")
        cloud = cur.get("cloud_cover")
        current = CurrentConditions(
            text_description=weather_code_text(cur.get("weather_code")),
            temperature_f=_to_fahrenheit(cur.get("temperature_2m"), unit),
            temperature_c=_to_celsius(cur.get("temperature_2m"), unit),
            feels_like_f=_to_fahrenheit(cur.get("apparent_temperature"), unit),
            humidity_percent=float(humidity) if isinstance(humidity, (int, float)) else None,
            wind_speed_mph=float(wind) if isinstance(wind, (int, float)) else None,
            wind_direction=_compass(cur.get("wind_direction_10m")),
            cloud_cover_percent=round(cloud) if isinstance(cloud, (int, float)) else None,
            observed_at=str(cur.get("time", "")),
        )
    report = WeatherReport(
        location=location,
        current=current,
        daily=daily_from_json(data, unit=unit),
        notes=[
            "Worldwide forecast from Open-Meteo. Local watches and warnings are "
            "shown only for US locations."
        ],
    )
    try:
        report.air_quality = air_quality(location.latitude, location.longitude, safe_mode=safe_mode)
    except OpenMeteoError:
        pass
    return report


def daily_forecast(
    latitude: float,
    longitude: float,
    *,
    days: int = 10,
    unit: str = "F",
    safe_mode: bool = False,
) -> list[DailyOutlook]:
    """The extended daily outlook alone (thin wrapper over :func:`fetch`)."""
    return fetch(latitude, longitude, days=days, unit=unit, safe_mode=safe_mode).daily


_AQI_CATEGORIES = (
    (50, "Good"),
    (100, "Moderate"),
    (150, "Unhealthy for sensitive groups"),
    (200, "Unhealthy"),
    (300, "Very unhealthy"),
    (10_000, "Hazardous"),
)


def aqi_category(us_aqi: object) -> str:
    """US Air Quality Index number -> its official category name."""
    if not isinstance(us_aqi, (int, float)):
        return ""
    for ceiling, name in _AQI_CATEGORIES:
        if us_aqi <= ceiling:
            return name
    return "Hazardous"


def air_quality(latitude: float, longitude: float, *, safe_mode: bool = False) -> AirQuality | None:
    """Current US Air Quality Index + fine-particulate level (Open-Meteo's free,
    keyless air-quality API). Returns None if unavailable."""
    refuse_in_safe_mode(safe_mode)
    query = urllib.parse.urlencode({
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": "us_aqi,pm2_5",
        "timezone": "auto",
    })
    try:
        data = http_json(f"https://air-quality-api.open-meteo.com/v1/air-quality?{query}")
    except HTTP_ERRORS:
        return None
    current = data.get("current") if isinstance(data, dict) else None
    if not isinstance(current, dict):
        return None
    aqi = current.get("us_aqi")
    pm = current.get("pm2_5")
    return AirQuality(
        us_aqi=round(aqi) if isinstance(aqi, (int, float)) else None,
        category=aqi_category(aqi),
        pm2_5=round(pm, 1) if isinstance(pm, (int, float)) else None,
    )
