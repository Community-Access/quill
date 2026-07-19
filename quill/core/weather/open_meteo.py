"""Open-Meteo daily outlook -- the extended (up to 16-day) forecast NWS does
not provide. Free, no account, no API key (https://open-meteo.com). Used only
to reach further out than the NWS ~7-day period forecast; NWS remains the
source for current conditions, the rich period narrative, and alerts.

wx-free, strict-typed, HTTPS-only, egress-audited (shares the weather
``_http.http_json`` chokepoint), Safe-Mode-gated.
"""

from __future__ import annotations

import urllib.parse

from quill.core.error_codes import CodedError
from quill.core.weather._http import HTTP_ERRORS, http_json
from quill.core.weather.models import DailyOutlook

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
            )
        )
    return rows


def _int_at(values: object, index: int) -> int | None:
    if isinstance(values, list) and index < len(values):
        value = values[index]
        if isinstance(value, (int, float)):
            return round(value)
    return None


def daily_forecast(
    latitude: float,
    longitude: float,
    *,
    days: int = 10,
    unit: str = "F",
    safe_mode: bool = False,
) -> list[DailyOutlook]:
    """Fetch the extended daily outlook (up to 16 days). ``unit`` is 'F' or 'C'."""
    refuse_in_safe_mode(safe_mode)
    days = max(1, min(16, days))
    query = urllib.parse.urlencode({
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "temperature_unit": "celsius" if unit == "C" else "fahrenheit",
        "timezone": "auto",
        "forecast_days": days,
    })
    try:
        data = http_json(f"https://api.open-meteo.com/v1/forecast?{query}")
    except HTTP_ERRORS as error:
        raise OpenMeteoError(f"Could not reach the extended-forecast service: {error}") from error
    return daily_from_json(data, unit=unit)
