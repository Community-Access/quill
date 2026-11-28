"""The next few hours, in words: rain starting soon, a four-hour glance ahead,
and the change in daylight since yesterday.

All of it comes from **one** Open-Meteo forecast request (:func:`fetch`):

* ``current`` for the fields chosen in Report Fields (:data:`FIELD_CATALOG`),
  which works for any hourly variable, each formatted from the unit Open-Meteo
  says it sent, never assumed.
* ``minutely_15`` precipitation for the next two hours -- "Light rain starting
  in about 30 minutes." Open-Meteo has true 15-minute data only over North
  America and central Europe; elsewhere the steps are filled in from hourly
  data, and the sentence says it is estimated (:func:`native_15_minute`).
* ``hourly`` for the next four hours -- the glance ahead: the temperature now
  and where it is heading, any change in the sky, the highest chance of
  precipitation, and the strongest wind when it is notable.
* ``daily`` ``daylight_duration`` for yesterday and today -- "8 hours 51
  minutes of daylight today, 2 minutes less than yesterday."

Units are asked for in the user's units. Pure parsing and wording are separate
from the one fetch, so all of it is testable without a network. wx-free and
strict-typed.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.weather.open_meteo import format_time, weather_code_text

GetJson = Callable[..., Any]

GLANCE_HOURS = 4
STEPS = 8  # 8 x 15 minutes = the next two hours


@dataclass(frozen=True, slots=True)
class FieldInfo:
    label: str
    help: str


#: The extra fields people can add to their report (item 9, "choose your
#: fields"). Every one is an Open-Meteo hourly variable, so it is also valid as
#: ``current``. Fields Weather Now already shows (temperature, humidity, wind,
#: cloud cover...) are left out, so nothing appears twice.
FIELD_CATALOG: dict[str, FieldInfo] = {
    "wind_gusts_10m": FieldInfo("Wind gusts", "The strongest gusts expected right now."),
    "precipitation": FieldInfo(
        "Precipitation in the last 15 minutes", "Rain, showers and snow, as water."
    ),
    "snowfall": FieldInfo("Snowfall in the last 15 minutes", "Fresh snow, as depth."),
    "snow_depth": FieldInfo("Snow on the ground", "How deep the snow is where you are."),
    "freezing_level_height": FieldInfo(
        "Freezing level", "The height above sea level where the air is at freezing."
    ),
    "visibility": FieldInfo("Visibility", "How far you could see, from the forecast model."),
    "dew_point_2m": FieldInfo("Dew point", "The temperature at which dew or fog forms."),
    "wet_bulb_temperature_2m": FieldInfo(
        "Wet-bulb temperature", "How well sweat can cool you; high values are dangerous."
    ),
    "pressure_msl": FieldInfo("Sea-level pressure", "Air pressure, adjusted to sea level."),
    "surface_pressure": FieldInfo("Surface pressure", "Air pressure where you are."),
    "cape": FieldInfo(
        "Thunderstorm energy (CAPE)",
        "Energy available for thunderstorms. Over 1000 is notable, over 2500 is high.",
    ),
    "uv_index": FieldInfo("UV index right now", "The sun's ultraviolet strength this hour."),
    "shortwave_radiation": FieldInfo(
        "Sunlight strength", "Solar radiation reaching the ground, in watts per square metre."
    ),
    "sunshine_duration": FieldInfo("Sunshine this hour", "Minutes of sunshine in the hour."),
    "cloud_cover_low": FieldInfo("Low cloud", "Cloud below about 2 kilometres, in percent."),
    "cloud_cover_high": FieldInfo("High cloud", "Cloud above about 8 kilometres, in percent."),
    "soil_temperature_0cm": FieldInfo(
        "Ground surface temperature", "The temperature of the ground's surface."
    ),
    "soil_moisture_0_to_1cm": FieldInfo(
        "Soil moisture near the surface", "How wet the top centimetre of soil is."
    ),
    "evapotranspiration": FieldInfo(
        "Evapotranspiration", "Water leaving soil and plants this hour, for gardeners."
    ),
    "vapour_pressure_deficit": FieldInfo(
        "Vapour pressure deficit", "How thirsty the air is; high values dry plants fast."
    ),
    "is_day": FieldInfo("Day or night", "Whether the sun is up."),
}


@dataclass(slots=True)
class Step:
    time: str
    precip: float  # in the unit asked for (mm or inch)
    snow: float  # cm or inch
    code: int | None


@dataclass(slots=True)
class Hour:
    time: str
    temperature: float | None
    precip_chance: int | None
    code: int | None
    wind: float | None


@dataclass(slots=True)
class Nowcast:
    current_time: str = ""
    steps: list[Step] = field(default_factory=list)
    hours: list[Hour] = field(default_factory=list)
    daylight_yesterday: float | None = None
    daylight_today: float | None = None
    metric: bool = False
    native_15_minute: bool = True
    #: field id -> (value, unit string Open-Meteo sent)
    extras: dict[str, tuple[Any, str]] = field(default_factory=dict)


def native_15_minute(latitude: float, longitude: float) -> bool:
    """True where Open-Meteo has real 15-minute data: North America and central
    Europe. Elsewhere its 15-minute steps are filled in from hourly data."""
    north_america = 14.0 <= latitude <= 72.0 and -170.0 <= longitude <= -50.0
    central_europe = 42.0 <= latitude <= 58.0 and -6.0 <= longitude <= 25.0
    return north_america or central_europe


def request_url(
    latitude: float, longitude: float, *, unit: str, extra_fields: list[str] | None = None
) -> str:
    metric = unit == "C"
    params: dict[str, Any] = {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": "temperature_2m",
        "minutely_15": "precipitation,snowfall,weather_code",
        "forecast_minutely_15": STEPS,
        "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m",
        "forecast_hours": GLANCE_HOURS + 1,
        "past_hours": 0,
        "daily": "daylight_duration",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "auto",
        "temperature_unit": "celsius" if metric else "fahrenheit",
        "wind_speed_unit": "kmh" if metric else "mph",
        "precipitation_unit": "mm" if metric else "inch",
    }
    chosen = [f for f in extra_fields or [] if f in FIELD_CATALOG]
    if chosen:
        params["current"] = ",".join(["temperature_2m", *chosen])
    return "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)


def _at(values: Any, index: int) -> float | None:
    if isinstance(values, list) and index < len(values):
        value = values[index]
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def parse(
    data: Any, *, unit: str, latitude: float | None = None, longitude: float | None = None
) -> Nowcast:
    """Parse the one forecast reply into a Nowcast (pure)."""
    native = (
        True if latitude is None or longitude is None else native_15_minute(latitude, longitude)
    )
    cast = Nowcast(metric=unit == "C", native_15_minute=native)
    if not isinstance(data, dict):
        return cast
    current = data.get("current")
    units = data.get("current_units")
    if isinstance(current, dict):
        cast.current_time = str(current.get("time", ""))
        for key in FIELD_CATALOG:
            if key in current:
                sent = units.get(key, "") if isinstance(units, dict) else ""
                cast.extras[key] = (current[key], str(sent))
    minutely = data.get("minutely_15")
    if isinstance(minutely, dict):
        for i, when in enumerate(minutely.get("time") or []):
            code = _at(minutely.get("weather_code"), i)
            cast.steps.append(
                Step(
                    time=str(when),
                    precip=_at(minutely.get("precipitation"), i) or 0.0,
                    snow=_at(minutely.get("snowfall"), i) or 0.0,
                    code=round(code) if code is not None else None,
                )
            )
    if not cast.current_time and cast.steps:
        cast.current_time = cast.steps[0].time
    hourly = data.get("hourly")
    if isinstance(hourly, dict):
        for i, when in enumerate(hourly.get("time") or []):
            when = str(when)
            if cast.current_time and when[:13] <= cast.current_time[:13]:
                continue  # the hour already under way
            code = _at(hourly.get("weather_code"), i)
            chance = _at(hourly.get("precipitation_probability"), i)
            cast.hours.append(
                Hour(
                    time=when,
                    temperature=_at(hourly.get("temperature_2m"), i),
                    precip_chance=round(chance) if chance is not None else None,
                    code=round(code) if code is not None else None,
                    wind=_at(hourly.get("wind_speed_10m"), i),
                )
            )
        cast.hours = cast.hours[:GLANCE_HOURS]
    daily = data.get("daily")
    if isinstance(daily, dict):
        lengths = daily.get("daylight_duration") or []
        cast.daylight_yesterday = _at(lengths, 0)
        cast.daylight_today = _at(lengths, 1)
    return cast


def fetch(
    latitude: float,
    longitude: float,
    *,
    unit: str = "F",
    extra_fields: list[str] | None = None,
    get: GetJson | None = None,
) -> Nowcast:
    """The one request. Raises the transport's errors (``HTTP_ERRORS``)."""
    if get is None:
        from quill.core.weather.open_meteo_limits import get_json

        get = get_json
    data = get(request_url(latitude, longitude, unit=unit, extra_fields=extra_fields))
    return parse(data, unit=unit, latitude=latitude, longitude=longitude)


# -- words -----------------------------------------------------------------------


def _minutes_between(start: str, end: str) -> int:
    from datetime import datetime

    try:
        delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    except ValueError:
        return 0
    return max(0, round(delta.total_seconds() / 60))


def _about(minutes: int) -> str:
    if minutes < 10:
        return "in the next few minutes"
    if minutes >= 60:
        hours, rest = divmod(minutes, 60)
        if rest < 15:
            return "in about an hour" if hours == 1 else f"in about {hours} hours"
        return f"in about {hours} and a half hours" if hours > 1 else "in about an hour and a half"
    return f"in about {round(minutes / 15) * 15} minutes"


def _kind(step: Step) -> str:
    code = step.code or 0
    if code >= 95:
        return "thunderstorms"
    if step.snow > 0 and (code in (71, 73, 75, 77, 85, 86) or step.precip <= 0):
        return "snow"
    if 51 <= code <= 57:
        return "drizzle"
    return "rain"


def _intensity(step: Step, metric: bool) -> str:
    rate = step.precip * 4  # per 15 minutes -> per hour
    if metric:
        light, heavy = 2.5, 7.6
    else:
        light, heavy = 0.1, 0.3
    if rate < light:
        return "light"
    if rate < heavy:
        return "moderate"
    return "heavy"


def _wet(step: Step) -> bool:
    return step.precip > 0 or step.snow > 0


def rain_soon_text(cast: Nowcast) -> str:
    """'Light rain starting in about 30 minutes.' or 'No rain or snow expected in
    the next 2 hours.' -- with 'estimated' where there is no 15-minute data."""
    if not cast.steps:
        return ""
    tail = "" if cast.native_15_minute else " This is estimated from hourly data here."
    first = cast.steps[0]
    if _wet(first):
        stop = next((s for s in cast.steps[1:] if not _wet(s)), None)
        what = f"{_intensity(first, cast.metric).capitalize()} {_kind(first)} now"
        if stop is None:
            return f"{what}, for at least the next 2 hours.{tail}"
        return f"{what}, stopping {_about(_minutes_between(first.time, stop.time))}.{tail}"
    start = next((s for s in cast.steps if _wet(s)), None)
    if start is None:
        return f"No rain or snow expected in the next 2 hours.{tail}"
    minutes = _minutes_between(first.time, start.time)
    peak = max((s for s in cast.steps if _wet(s)), key=lambda s: s.precip + s.snow)
    return (
        f"{_intensity(peak, cast.metric).capitalize()} {_kind(start)} starting "
        f"{_about(minutes)}.{tail}"
    )


def _duration(seconds: float) -> str:
    total = round(seconds / 60)
    hours, minutes = divmod(total, 60)
    out = f"{hours} hour{'s' if hours != 1 else ''}"
    if minutes:
        out += f" {minutes} minute{'s' if minutes != 1 else ''}"
    return out


def daylight_text(cast: Nowcast) -> str:
    """'10 hours 15 minutes of daylight today, 2 minutes less than yesterday.'"""
    today, yesterday = cast.daylight_today, cast.daylight_yesterday
    if today is None:
        return ""
    lead = f"{_duration(today)} of daylight today"
    if yesterday is None:
        return lead + "."
    diff = today - yesterday
    if abs(diff) < 30:
        return f"{lead}, about the same as yesterday."
    minutes = round(abs(diff) / 60)
    amount = f"{minutes} minute{'s' if minutes != 1 else ''}"
    return f"{lead}, {amount} {'more' if diff > 0 else 'less'} than yesterday."


def _hour(iso: str) -> str:
    """'2026-11-27T17:00' -> '5 PM' (hourly data is always on the hour, and
    some synthesizers read ':00' as 'oh oh')."""
    return format_time(iso).replace(":00 ", " ")


def glance_text(cast: Nowcast, *, wind_word: str = "miles per hour") -> str:
    """The next four hours in two or three sentences, the first hour as 'now'."""
    hours = [h for h in cast.hours if h.temperature is not None]
    if not hours:
        return ""
    first, last = hours[0], hours[-1]
    t0, t1 = round(first.temperature or 0), round(last.temperature or 0)
    lead = f"Through {_hour(last.time)}"
    if t1 == t0:
        temps = f"{lead}: steady near {t0}."
    else:
        verb = "rising" if t1 > t0 else "falling"
        temps = f"{lead}: {t0} now, {verb} to {t1}."
    parts = [temps]
    changes: list[str] = []
    previous = ""
    for h in hours:
        sky = weather_code_text(h.code) if h.code is not None else ""
        if sky and sky != previous:
            when = "now" if h is first else f"from {_hour(h.time)}"
            changes.append(f"{sky.lower()} {when}")
            previous = sky
    if changes:
        parts.append(f"Sky: {', then '.join(changes)}.")
    chances = [h.precip_chance for h in hours if h.precip_chance is not None]
    if chances and max(chances) >= 20:
        parts.append(f"Chance of precipitation up to {max(chances)} percent.")
    winds = [h.wind for h in hours if h.wind is not None]
    if winds and max(winds) >= 15:
        parts.append(f"Wind up to {round(max(winds))} {wind_word}.")
    return " ".join(parts)


def _fmt_number(value: float) -> str:
    if value != 0 and abs(value) < 0.1:
        return f"{value:.2f}"  # 0.04 inches, not "0.0"
    return f"{value:.0f}" if abs(value) >= 10 or value == int(value) else f"{value:.1f}"


_SINGULAR = {
    "inches": "inch",
    "millimetres": "millimetre",
    "centimetres": "centimetre",
    "metres": "metre",
    "feet": "foot",
    "miles": "mile",
    "kilometres": "kilometre",
    "minutes": "minute",
    "degrees": "degree",
    "miles per hour": "mile per hour",
    "kilometres per hour": "kilometre per hour",
    "knots": "knot",
    "metres per second": "metre per second",
    "hectopascals": "hectopascal",
    "kilopascals": "kilopascal",
    "watts per square metre": "watt per square metre",
    "joules per kilogram": "joule per kilogram",
}


def _one(words: str) -> str:
    """'1 inches' -> '1 inch': a unit after exactly 1 is singular."""
    number, _, unit = words.partition(" ")
    if number in ("1", "1.0", "-1") and unit in _SINGULAR:
        return f"{number} {_SINGULAR[unit]}"
    return words


def extra_field_text(key: str, value: Any, sent_unit: str, *, metric: bool) -> str:
    """One chosen field as a sentence, formatted from the unit Open-Meteo sent."""
    info = FIELD_CATALOG.get(key)
    if info is None or value is None or isinstance(value, bool):
        return ""
    if key == "is_day":
        return "It is daytime." if value else "It is night."
    if not isinstance(value, int | float):
        return ""
    number = float(value)
    unit = sent_unit.replace("Â", "").strip()  # a stray byte some replies carry
    if unit in ("°F", "°C"):
        words = f"{round(number)} degrees"
    elif unit == "m":
        if key == "snow_depth":
            words = f"{number * 100:.0f} centimetres" if metric else f"{number * 39.37:.0f} inches"
        elif key == "visibility":
            words = f"{number / 1000:.1f} kilometres" if metric else f"{number / 1609.34:.1f} miles"
        else:
            words = f"{number:,.0f} metres" if metric else f"{number * 3.281:,.0f} feet"
    elif unit == "ft":
        if key == "snow_depth":
            words = f"{number * 12:.0f} inches"
        elif key == "visibility":
            words = f"{number / 5280:.1f} miles"
        else:
            words = f"{number:,.0f} feet"
    elif unit in ("mm", "inch", "cm"):
        names = {"mm": "millimetres", "inch": "inches", "cm": "centimetres"}
        words = f"{_fmt_number(number)} {names[unit]}"
    elif unit in ("mp/h", "mph", "km/h", "kn", "m/s"):
        names = {
            "mp/h": "miles per hour",
            "mph": "miles per hour",
            "km/h": "kilometres per hour",
            "kn": "knots",
            "m/s": "metres per second",
        }
        words = f"{round(number)} {names[unit]}"
    elif unit == "%":
        words = f"{round(number)} percent"
    elif unit == "hPa":
        words = f"{round(number)} hectopascals"
    elif unit == "s":
        words = f"{round(number / 60)} minutes"
    elif unit in ("m³/m³", "m3/m3"):
        words = f"{round(number * 100)} percent"
    elif unit == "W/m²":
        words = f"{round(number)} watts per square metre"
    elif unit == "J/kg":
        words = f"{round(number)} joules per kilogram"
    elif unit == "kPa":
        words = f"{number:.1f} kilopascals"
    else:
        words = f"{_fmt_number(number)} {unit}".strip()
    return f"{info.label}: {_one(words)}."


def extras_text(cast: Nowcast, order: list[str]) -> str:
    """The chosen fields, in the order the user put them."""
    bits = [
        extra_field_text(key, *cast.extras[key], metric=cast.metric)
        for key in order
        if key in cast.extras
    ]
    return " ".join(b for b in bits if b)
