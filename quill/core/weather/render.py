"""Deterministic, speech-first text rendering for QUILL Weather (PRD 6.2, 9.6).

Pure functions that turn a normalized report into warm, fully spelled-out
sentences meant to be read aloud by a screen reader or spoken by a text-to-
speech voice: no abbreviations ("miles per hour", not "mph"; "west-northwest",
not "WNW"; "degrees", not a symbol). No wx, no clock, no randomness -- so every
line is unit-tested exactly. Speech and text share these strings, so they can
never drift apart.
"""

from __future__ import annotations

from quill.core.weather.models import CurrentConditions, DailyOutlook, WeatherReport
from quill.core.weather.settings import WeatherSettings

#: Compass abbreviation -> spoken words.
_WIND_WORDS = {
    "N": "north",
    "NNE": "north-northeast",
    "NE": "northeast",
    "ENE": "east-northeast",
    "E": "east",
    "ESE": "east-southeast",
    "SE": "southeast",
    "SSE": "south-southeast",
    "S": "south",
    "SSW": "south-southwest",
    "SW": "southwest",
    "WSW": "west-southwest",
    "W": "west",
    "WNW": "west-northwest",
    "NW": "northwest",
    "NNW": "north-northwest",
}
_WIND_UNIT_WORDS = {
    "mph": "miles per hour",
    "km/h": "kilometers per hour",
    "kts": "knots",
    "m/s": "meters per second",
}


def convert_temp(fahrenheit: float | None, unit: str) -> float | None:
    if fahrenheit is None:
        return None
    return round((fahrenheit - 32) * 5 / 9, 1) if unit == "C" else fahrenheit


def convert_wind_mph(mph: float | None, unit: str) -> float | None:
    if mph is None:
        return None
    factor = {"mph": 1.0, "km/h": 1.609344, "kts": 0.868976, "m/s": 0.44704}.get(unit, 1.0)
    return round(mph * factor, 1)


def _unit_word(unit: str) -> str:
    return "Celsius" if unit == "C" else "Fahrenheit"


def temp_phrase(
    fahrenheit: float | None, settings: WeatherSettings, *, with_unit: bool = True
) -> str:
    """A temperature spoken as words: '96 degrees Fahrenheit' (or without the
    scale for a follow-on mention like 'it feels like 98')."""
    value = convert_temp(fahrenheit, settings.temperature_unit)
    if value is None:
        return "an unknown temperature"
    number = int(round(value))
    if with_unit:
        return f"{number} degrees {_unit_word(settings.temperature_unit)}"
    return f"{number} degrees"


def wind_phrase(
    mph: float | None, direction: str, gust_mph: float | None, settings: WeatherSettings
) -> str:
    """A full sentence describing the wind, gust included when stronger."""
    value = convert_wind_mph(mph, settings.wind_unit)
    if value is None or int(round(value)) == 0:
        return "The air is calm."
    unit = _WIND_UNIT_WORDS.get(settings.wind_unit, settings.wind_unit)
    heading = _WIND_WORDS.get(direction, "")
    from_part = f"from the {heading} " if heading else ""
    sentence = f"The wind is blowing {from_part}at {int(round(value))} {unit}"
    gust = convert_wind_mph(gust_mph, settings.wind_unit)
    if gust is not None and int(round(gust)) > int(round(value)):
        sentence += f", gusting to {int(round(gust))} {unit}"
    return sentence + "."


def uv_phrase(index: int | None) -> str:
    if index is None:
        return ""
    if index <= 2:
        level = "low"
    elif index <= 5:
        level = "moderate"
    elif index <= 7:
        level = "high"
    elif index <= 10:
        level = "very high"
    else:
        level = "extreme"
    return f"The ultraviolet index reaches {index} today, which is {level}."


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


def friendly_datetime(iso: str, tz_name: str = "") -> str:
    """'2026-07-19T20:55:00+00:00' -> 'July 19 at 1:55 PM', converting a
    timestamp that carries a UTC offset into the location's local zone when
    ``tz_name`` (an IANA name like 'America/Phoenix') is given. Pure: it parses
    an existing timestamp, it never reads the clock."""
    from datetime import datetime

    if not isinstance(iso, str) or "T" not in iso:
        return ""
    try:
        moment = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return ""
    if tz_name and moment.tzinfo is not None:
        try:
            from zoneinfo import ZoneInfo

            moment = moment.astimezone(ZoneInfo(tz_name))
        except Exception:  # noqa: BLE001 - unknown zone: fall back to the given time
            pass
    suffix = "AM" if moment.hour < 12 else "PM"
    hour12 = moment.hour % 12 or 12
    return f"{_MONTHS[moment.month - 1]} {moment.day} at {hour12}:{moment.minute:02d} {suffix}"


def moon_phrase(today: object) -> str:
    """A spoken sentence for today's moon (duck-typed against a DailyOutlook to
    avoid an import cycle); '' when no moon phase is available."""
    phase = getattr(today, "moon_phase", "")
    if not phase:
        return ""
    illum = getattr(today, "moon_illumination_percent", None)
    sentence = f"The moon is a {phase.lower()}"
    if illum is not None:
        sentence += f", {illum} percent lit"
    sentence += "."
    rise = getattr(today, "moonrise", "")
    setting = getattr(today, "moonset", "")
    if rise and setting:
        sentence += f" It rises at {rise} and sets at {setting}."
    elif rise:
        sentence += f" It rises at {rise}."
    elif setting:
        sentence += f" It sets at {setting}."
    return sentence


_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def local_time_phrase(now: object, tz_name: str) -> str:
    """The current local time at the location as a spoken sentence, e.g. "The
    local time there is Thursday, April 27, 9:51 AM." ``now`` is a timezone-aware
    datetime (the caller reads the clock -- this module stays clock-free); it is
    converted into ``tz_name`` (an IANA zone like 'America/New_York'). Returns ''
    when the zone is unknown or ``now`` is not a usable aware datetime."""
    from datetime import datetime

    if not tz_name or not isinstance(now, datetime) or now.tzinfo is None:
        return ""
    try:
        from zoneinfo import ZoneInfo

        local = now.astimezone(ZoneInfo(tz_name))
    except Exception:  # noqa: BLE001 - unknown zone: no local-time line rather than a crash
        return ""
    weekday = _WEEKDAYS[local.weekday()]
    suffix = "AM" if local.hour < 12 else "PM"
    hour12 = local.hour % 12 or 12
    return (
        f"The local time there is {weekday}, {_MONTHS[local.month - 1]} {local.day}, "
        f"{hour12}:{local.minute:02d} {suffix}."
    )


def air_quality_phrase(air: object) -> str:
    """A spoken sentence for an AirQuality value (duck-typed to avoid a model
    import cycle in the signature); '' when nothing usable."""
    aqi = getattr(air, "us_aqi", None)
    category = getattr(air, "category", "")
    if aqi is None:
        return ""
    tail = f", which is {category.lower()}" if category else ""
    return f"The air quality index is {aqi}{tail}."


def current_conditions_block(
    current: CurrentConditions,
    today: DailyOutlook | None,
    settings: WeatherSettings,
    air_quality: object = None,
) -> str:
    """A warm, complete, spoken-ready paragraph of the current data points the
    user has chosen to include. Temperature and the sky condition always show;
    every other point is gated by its Settings toggle."""
    parts: list[str] = []
    if current.temperature_f is not None:
        lead = f"Right now it is {temp_phrase(current.temperature_f, settings)}"
        if current.text_description:
            lead += f" and {current.text_description.lower()}"
        parts.append(lead + ".")
    elif current.text_description:
        parts.append(f"Right now it is {current.text_description.lower()}.")

    if (
        settings.show_feels_like
        and current.feels_like_f is not None
        and current.temperature_f is not None
        and abs(current.feels_like_f - current.temperature_f) >= 1
    ):
        parts.append(
            f"It feels like {temp_phrase(current.feels_like_f, settings, with_unit=False)}."
        )
    if settings.show_humidity and current.humidity_percent is not None:
        parts.append(f"The humidity is {int(current.humidity_percent)} percent.")
    if settings.show_dew_point and current.dewpoint_f is not None:
        parts.append(
            f"The dew point is {temp_phrase(current.dewpoint_f, settings, with_unit=False)}."
        )
    if settings.show_wind:
        parts.append(
            wind_phrase(
                current.wind_speed_mph, current.wind_direction, current.wind_gust_mph, settings
            )
        )
    if settings.show_cloud_cover and current.cloud_cover_percent is not None:
        parts.append(f"Cloud cover is {int(current.cloud_cover_percent)} percent.")
    if settings.show_pressure and current.pressure_inhg is not None:
        parts.append(f"The barometric pressure is {current.pressure_inhg} inches of mercury.")
    if settings.show_visibility and current.visibility_mi is not None:
        parts.append(f"Visibility is {current.visibility_mi:g} miles.")
    if (
        settings.show_precip_chance
        and today is not None
        and today.precipitation_percent is not None
    ):
        parts.append(
            f"There is a {today.precipitation_percent} percent chance of precipitation today."
        )
    if settings.show_sunrise_sunset and today is not None and today.sunrise and today.sunset:
        parts.append(f"The sun rises at {today.sunrise} and sets at {today.sunset}.")
    if settings.show_moon and today is not None:
        moon = moon_phrase(today)
        if moon:
            parts.append(moon)
    if settings.show_uv_index and today is not None:
        uv = uv_phrase(today.uv_index)
        if uv:
            parts.append(uv)
    if settings.show_air_quality:
        aq = air_quality_phrase(air_quality)
        if aq:
            parts.append(aq)
    if not parts:
        return "No current observation is available right now."
    return " ".join(parts)


def current_conditions_line(current: CurrentConditions, settings: WeatherSettings) -> str:
    """A short spoken line of current conditions (for Quick Weather)."""
    parts: list[str] = []
    if current.temperature_f is not None:
        lead = f"{temp_phrase(current.temperature_f, settings)}"
        if current.text_description:
            lead += f" and {current.text_description.lower()}"
        parts.append(lead)
    elif current.text_description:
        parts.append(current.text_description)
    if current.wind_speed_mph:
        parts.append(
            wind_phrase(current.wind_speed_mph, current.wind_direction, None, settings).rstrip(".")
        )
    if current.humidity_percent is not None:
        parts.append(f"humidity {int(current.humidity_percent)} percent")
    return ", ".join(parts) if parts else "No current observation is available."


def quick_weather_line(report: WeatherReport, settings: WeatherSettings) -> str:
    """The one-line Quick Weather summary (PRD 6.2), composed per the user's
    include-toggles -- friendly and fully spoken."""
    place = report.location.resolved_name or report.location.label
    bits: list[str] = [f"Here is the weather for {place}."]
    current = report.current
    if current and current.temperature_f is not None:
        lead = f"It is {temp_phrase(current.temperature_f, settings)}"
        if current.text_description:
            lead += f" and {current.text_description.lower()}"
        bits.append(lead + ".")
    if settings.quick_include_feels_like and current and current.feels_like_f is not None:
        bits.append(
            f"It feels like {temp_phrase(current.feels_like_f, settings, with_unit=False)}."
        )
    if settings.quick_include_wind and current and current.wind_speed_mph:
        bits.append(
            wind_phrase(
                current.wind_speed_mph, current.wind_direction, current.wind_gust_mph, settings
            )
        )
    if settings.quick_include_humidity and current and current.humidity_percent is not None:
        bits.append(f"The humidity is {int(current.humidity_percent)} percent.")
    if settings.quick_include_alert_count:
        count = report.active_alert_count
        if count == 0:
            bits.append("There are no active alerts.")
        else:
            verb = "is" if count == 1 else "are"
            plural = "" if count == 1 else "s"
            bits.append(
                f"There {verb} {count} active alert{plural}. "
                f"The most urgent is a {report.alerts[0].event}."
            )
    return " ".join(bits)


def filtered_alerts(report: WeatherReport, settings: WeatherSettings) -> list:
    """The report's alerts passing the user's severity floor and mute list,
    still sorted most-severe first."""
    return [a for a in report.alerts if settings.alert_passes(a.severity, a.event)]
