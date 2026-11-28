"""Weather on a Past Date, in words: the day read like the current report,
each hour as a row, the comparison with normal, and the range export.

Order of the day text, as the current report reads: the summary line (date,
place, sky), high and low, feels like, precipitation and snow, wind, sunrise
and sunset with the daylight length, then "Compared with normal". The hours
are a list of their own in the window and follow the day in Copy.

Pure and strict-typed.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

from quill.core.weather.date_query import long_date
from quill.core.weather.history_cache import DayRecord
from quill.core.weather.history_text import (
    Climate,
    departure,
    precip_text,
    temp_text,
    temp_value,
)
from quill.core.weather.open_meteo import compass_name, format_time, weather_code_text
from quill.core.weather.past_day import HourRow, PastDay

_WIND_FACTOR = {"mph": 1 / 1.609344, "km/h": 1.0, "kts": 1 / 1.852, "m/s": 1 / 3.6}
_WIND_WORDS = {
    "mph": "miles per hour",
    "km/h": "kilometres per hour",
    "kts": "knots",
    "m/s": "metres per second",
}


@dataclass(slots=True)
class Units:
    temperature: str = "F"  # "F" or "C"
    wind: str = "mph"  # one of settings.WIND_UNITS


def wind_text(kmh: float | None, units: Units) -> str:
    if kmh is None:
        return ""
    value = round(kmh * _WIND_FACTOR.get(units.wind, 1 / 1.609344))
    return f"{value} {_WIND_WORDS.get(units.wind, units.wind)}"


def _daylight(seconds: float) -> str:
    total = round(seconds / 60)
    hours, minutes = divmod(total, 60)
    text = f"{hours} hour{'s' if hours != 1 else ''}"
    return text + (f" {minutes} minute{'s' if minutes != 1 else ''}" if minutes else "")


def summary_line(day: PastDay, place: str) -> str:
    """'Monday, March 14, 2011 in Tucson: partly cloudy.'"""
    when = long_date(date.fromisoformat(day.date))
    sky = weather_code_text(day.code).lower() if day.code is not None else ""
    return f"{when} in {place}: {sky}." if sky and sky != "unknown" else f"{when} in {place}."


def spoken_summary(day: PastDay, place: str, units: Units) -> str:
    """The short version said after a move: the summary line, then high and low."""
    del place
    sky = weather_code_text(day.code) if day.code is not None else ""
    bits = [sky] if sky and sky != "Unknown" else []
    if day.high_c is not None:
        bits.append(f"high {temp_text(day.high_c, units.temperature)}")
    if day.low_c is not None:
        bits.append(f"low {temp_text(day.low_c, units.temperature)}")
    return (", ".join(bits) + ".") if bits else "No data for this day."


def day_lines(
    day: PastDay, place: str, units: Units, *, compared: str = ""
) -> list[str]:  # fmt: skip
    """The day as the current report reads it, one sentence per line."""
    t = units.temperature
    lines = [summary_line(day, place)]
    if day.high_c is not None or day.low_c is not None:
        parts = []
        if day.high_c is not None:
            parts.append(f"High {temp_text(day.high_c, t)} degrees")
        if day.low_c is not None:
            parts.append(f"low {temp_text(day.low_c, t)}")
        lines.append(", ".join(parts) + ".")
    if day.feels_high_c is not None and day.feels_low_c is not None:
        lines.append(
            f"Feels like {temp_text(day.feels_high_c, t)} at the warmest and "
            f"{temp_text(day.feels_low_c, t)} at the coldest."
        )
    if day.precip_mm is not None:
        if day.precip_mm <= 0:
            lines.append("No precipitation.")
        else:
            hours = ""
            if day.precip_hours:
                count = round(day.precip_hours)
                hours = f" over {count} hour{'s' if count != 1 else ''}"
            lines.append(f"Precipitation {precip_text(day.precip_mm, t)}{hours}.")
    if day.snow_cm:
        lines.append(f"Snow {precip_text(day.snow_cm, t, snow=True)}.")
    if day.wind_max_kmh is not None:
        wind = f"Wind up to {wind_text(day.wind_max_kmh, units)}"
        if day.gust_max_kmh is not None and day.gust_max_kmh > day.wind_max_kmh:
            wind += f", gusts to {wind_text(day.gust_max_kmh, units)}"
        if day.wind_from is not None:
            wind += f", mostly from the {compass_name(day.wind_from)}"
        lines.append(wind + ".")
    sun = []
    if day.sunrise:
        sun.append(f"Sunrise {format_time(day.sunrise)}")
    if day.sunset:
        sun.append(f"sunset {format_time(day.sunset)}")
    if day.daylight_s:
        sun.append(f"{_daylight(day.daylight_s)} of daylight")
    if sun:
        lines.append(", ".join(sun) + ".")
    if compared:
        lines.append(compared)
    return lines


def compared_line(
    day: PastDay,
    units: Units,
    *,
    climate: Climate | None = None,
    average: tuple[float | None, float | None, int] | None = None,
) -> str:
    """'Compared with normal: the high was 6 degrees below the 1991 to 2020
    normal of 67 at Tucson International Airport. Record high for the date: 88
    in 1989.' -- or against the multi-year average outside the US."""
    t = units.temperature
    high = temp_value(day.high_c, t)
    if high is None:
        return ""
    normals = climate.normals if climate else None
    normal_high = temp_value(normals.get("high_c"), t) if normals else None
    if normal_high is not None and climate is not None:
        text = (
            f"Compared with normal: the high was {departure(high, normal_high, t)} the "
            f"1991 to 2020 normal of {normal_high} at {climate.station_name}."
        )
        records = climate.records or {}
        warm, cold = records.get("warmest_high"), records.get("coldest_low")
        bits = []
        if isinstance(warm, dict) and warm.get("value") is not None:
            bits.append(f"high {temp_text(warm['value'], t)} in {warm.get('year')}")
        if isinstance(cold, dict) and cold.get("value") is not None:
            bits.append(f"low {temp_text(cold['value'], t)} in {cold.get('year')}")
        if bits:
            text += f" Records for this date: {', '.join(bits)}."
        return text
    if average is not None and average[0] is not None and average[2]:
        avg = temp_value(average[0], t)
        if avg is None:
            return ""
        years = average[2]
        return (
            f"Compared with normal: the high was {departure(high, avg, t)} the average "
            f"for this date over the {years} years before, {avg}."
        )
    return ""


def hour_cells(hour: HourRow, units: Units) -> tuple[str, str, str, str, str, str]:
    """Time, conditions, temperature, feels like, precipitation, wind."""
    missing = "not recorded"
    t = units.temperature
    precip = precip_text(hour.precip_mm, t) if hour.precip_mm is not None else missing
    if hour.snow_cm:
        precip = f"snow {precip_text(hour.snow_cm, t, snow=True)}"
    wind = wind_text(hour.wind_kmh, units) or missing
    if hour.wind_from is not None and hour.wind_kmh:
        wind += f" from the {compass_name(hour.wind_from)}"
    return (
        format_time(hour.time) or hour.time,
        weather_code_text(hour.code) if hour.code is not None else missing,
        temp_text(hour.temperature_c, t) or missing,
        temp_text(hour.feels_like_c, t) or missing,
        precip,
        wind if hour.wind_kmh else ("calm" if hour.wind_kmh == 0 else wind),
    )


def hour_sentence(hour: HourRow, units: Units) -> str:
    when, sky, temp, feels, precip, wind = hour_cells(hour, units)
    return (
        f"{when}: {sky.lower()}, {temp}, feels like {feels}, precipitation {precip}, wind {wind}."
    )


def day_text(
    day: PastDay, place: str, units: Units, *, compared: str = "", credits: str = ""
) -> str:
    """Everything Copy puts on the clipboard: the day, each hour, the credits."""
    lines = day_lines(day, place, units, compared=compared)
    if day.hours:
        lines.append("")
        lines.append("Hour by hour:")
        lines.extend(hour_sentence(h, units) for h in day.hours)
    if credits:
        lines.extend(["", f"Sources: {credits}"])
    return "\n".join(lines)


# -- the range export -----------------------------------------------------------


def range_csv(rows: list[DayRecord], units: Units) -> str:
    """Days as CSV, oldest first, with units in the column names."""
    t = units.temperature
    precip_unit, snow_unit = ("mm", "cm") if t == "C" else ("in", "in")
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([
        "Date",
        "Conditions",
        f"High ({t})",
        f"Low ({t})",
        f"Precipitation ({precip_unit})",
        f"Snow ({snow_unit})",
        f"Wind max ({units.wind})",
    ])
    for r in sorted(rows, key=lambda r: r.date):
        precip = r.precip_mm if t == "C" or r.precip_mm is None else r.precip_mm / 25.4
        snow = r.snow_cm if t == "C" or r.snow_cm is None else r.snow_cm / 2.54
        wind = (
            round(r.wind_max_kmh * _WIND_FACTOR.get(units.wind, 1.0), 1)
            if r.wind_max_kmh is not None
            else ""
        )
        writer.writerow([
            r.date,
            weather_code_text(r.code) if r.code is not None else "",
            temp_text(r.high_c, t),
            temp_text(r.low_c, t),
            "" if precip is None else f"{precip:.2f}",
            "" if snow is None else f"{snow:.1f}",
            wind,
        ])
    return out.getvalue()


def range_text(rows: list[DayRecord], place: str, units: Units, *, credits: str) -> str:
    """Days as plain sentences, oldest first, with the credits at the end."""
    from quill.core.weather.history_text import row_sentence

    ordered = sorted(rows, key=lambda r: r.date)
    lines = [f"Weather in {place}, {len(ordered)} day{'s' if len(ordered) != 1 else ''}.", ""]
    lines.extend(row_sentence(r, units.temperature) for r in ordered)
    lines.extend(["", f"Sources: {credits}"])
    return "\n".join(lines)
