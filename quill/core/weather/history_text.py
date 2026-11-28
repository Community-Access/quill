"""Weather History in plain words: the summary for the ear, and the rows.

WeatherFast shows history as rows. Rows are fine to browse, but a listener has
to hold twenty of them in mind to know whether today is unusual. The summary
does that sum for them, in the order a person asks: how does this compare with
normal, what are the records, and how often does it rain on this date?

Every number is said in the user's units (degrees Fahrenheit with inches, or
degrees Celsius with millimetres). Station records and 1991-2020 normals come
from NOAA RCC-ACIS where there is a US station; otherwise the comparison is
with the years looked up, and the summary says so -- a "record" from twenty
years of reanalysis is not a record, and is never called one.

Pure, wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from quill.core.weather.history_cache import DayRecord
from quill.core.weather.open_meteo import weather_code_text

_MONTHS = (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
)  # fmt: skip

#: Shown in the window and in Help > About, for whichever sources a result used.
CREDIT_OPEN_METEO = "Weather data by Open-Meteo.com, under the CC BY 4.0 licence."
CREDIT_ERA5 = "Historical data: Copernicus Climate Change Service ERA5 reanalysis, via Open-Meteo."
CREDIT_ACIS = (
    "US station records and 1991 to 2020 normals: NOAA Regional Climate Centers, RCC-ACIS."
)


def credits_for(sources: Iterable[str], *, used_acis: bool) -> str:
    """The credit lines a result needs: Open-Meteo always, ERA5 when archive
    data was used, ACIS when station data was."""
    found = set(sources)
    lines = [CREDIT_OPEN_METEO]
    if "archive" in found:
        lines.append(CREDIT_ERA5)
    if used_acis:
        lines.append(CREDIT_ACIS)
    return " ".join(lines)


# -- units -----------------------------------------------------------------------


def temp_value(celsius: float | None, unit: str) -> int | None:
    if celsius is None:
        return None
    return round(celsius * 9 / 5 + 32) if unit != "C" else round(celsius)


def temp_text(celsius: float | None, unit: str) -> str:
    value = temp_value(celsius, unit)
    return "" if value is None else str(value)


def precip_text(mm: float | None, unit: str, *, snow: bool = False) -> str:
    """'0.26 inches', 'a trace', '6.6 millimetres', '3 centimetres' (snow)."""
    if mm is None:
        return ""
    if mm <= 0:
        return "none"
    if unit == "C":
        if not snow and mm < 0.1:
            return "a trace"
        number = f"{mm:.1f}".removesuffix(".0")
        word = "centimetre" if snow else "millimetre"
        return f"{number} {word}" if number == "1" else f"{number} {word}s"
    inches = mm / 2.54 if snow else mm / 25.4
    if inches < 0.005:
        return "a trace"
    if snow:
        return f"{inches:.1f} inches".replace(".0 ", " ")
    return "1 inch" if f"{inches:.2f}" == "1.00" else f"{inches:.2f} inches"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def month_day_text(month: int, day: int) -> str:
    return f"{_MONTHS[month - 1]} {day}"


def date_text(iso: str, *, with_year: bool = True) -> str:
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    base = f"{_MONTHS[d.month - 1]} {d.day}"
    return f"{base}, {d.year}" if with_year else base


def departure(value: int, normal: int, unit: str) -> str:
    """'6 degrees below', '1 degree above', 'right at'."""
    del unit
    diff = value - normal
    if diff == 0:
        return "right at"
    word = "degree" if abs(diff) == 1 else "degrees"
    return f"{abs(diff)} {word} {'above' if diff > 0 else 'below'}"


# -- rows ------------------------------------------------------------------------


def row_cells(record: DayRecord, unit: str) -> tuple[str, str, str, str, str]:
    """Date, conditions, high, low, precipitation -- for the list control."""
    precip = precip_text(record.precip_mm, unit)
    if record.snow_cm:
        snow = precip_text(record.snow_cm, unit, snow=True)
        precip = f"{precip}, snow {snow}" if precip and precip != "none" else f"snow {snow}"
    return (
        date_text(record.date),
        weather_code_text(record.code) if record.code is not None else "not recorded",
        temp_text(record.high_c, unit) or "not recorded",
        temp_text(record.low_c, unit) or "not recorded",
        precip or "not recorded",
    )


def row_sentence(record: DayRecord, unit: str) -> str:
    """One row as a sentence, for Copy and for the row's spoken detail."""
    when, cond, high, low, precip = row_cells(record, unit)
    missing = "not recorded"
    bits = [when]
    if cond != missing:
        bits.append(cond.lower())
    if high != missing:
        bits.append(f"high {high}")
    if low != missing:
        bits.append(f"low {low}")
    if precip != missing:
        bits.append(f"precipitation {precip}")
    return ", ".join(bits) + "."


# -- summaries -------------------------------------------------------------------


@dataclass(slots=True)
class Climate:
    """What ACIS gave for the calendar day: station name, normals, records."""

    station_name: str = ""
    normals: dict[str, Any] | None = None
    records: dict[str, Any] | None = None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _extreme(rows: list[DayRecord], attr: str, *, highest: bool) -> tuple[DayRecord, float] | None:
    usable = [(r, getattr(r, attr)) for r in rows if getattr(r, attr) is not None]
    if not usable:
        return None
    pick = max(usable, key=lambda p: p[1]) if highest else min(usable, key=lambda p: p[1])
    return pick[0], float(pick[1])


def _lead(target: DayRecord | None, today: date, unit: str) -> tuple[str, int | None]:
    """'Today's forecast high of 41 degrees' and the high in user units."""
    if target is None or target.high_c is None:
        return "", None
    high = temp_value(target.high_c, unit)
    when = date.fromisoformat(target.date)
    if when == today:
        return f"Today's forecast high of {high} degrees", high
    if when.year == today.year:
        return f"This year's high on this date, {high} degrees,", high
    return f"The high on {date_text(target.date)}, {high} degrees,", high


def same_date_summary(
    place: str,
    month: int,
    day: int,
    rows: list[DayRecord],
    *,
    today: date,
    unit: str,
    climate: Climate | None = None,
    failed_count: int = 0,
    failure_text: str = "",
    years_asked: int = 0,
) -> str:
    """The plain-words summary for one calendar day over many years."""
    name = month_day_text(month, day)
    sentences: list[str] = [f"{name} in {place}."]
    this_year = [r for r in rows if r.date.startswith(f"{today.year}-")]
    target = this_year[0] if this_year else None
    past = [r for r in rows if r is not target]
    lead, high = _lead(target, today, unit)
    normals = climate.normals if climate else None
    station = climate.station_name if climate else ""
    normal_high = temp_value(normals.get("high_c"), unit) if normals else None
    normal_low = temp_text(normals.get("low_c"), unit) if normals else ""
    low_tail = f", where the normal low is {normal_low}" if normal_low else ""
    if lead and high is not None and normal_high is not None:
        sentences.append(
            f"{lead} is {departure(high, normal_high, unit)} the 1991 to 2020 normal "
            f"of {normal_high} at {station}{low_tail}."
        )
    elif normal_high is not None:
        sentences.append(f"The 1991 to 2020 normal high at {station} is {normal_high}{low_tail}.")
    elif lead and high is not None and len(past) >= 3:
        avg = _mean([r.high_c for r in past if r.high_c is not None])
        avg_high = temp_value(avg, unit)
        if avg_high is not None:
            sentences.append(
                f"{lead} is {departure(high, avg_high, unit)} the average of the "
                f"{_plural(len(past), 'year')} looked up, {avg_high}."
            )
    records = climate.records if climate else None
    if records:
        sentences.append(_station_records_sentence(records, station, unit))
    if past:
        sentences.extend(_years_sentences(past, unit, have_station=bool(records)))
    elif not rows and not failed_count:
        sentences.append("Open-Meteo had no data for this date.")
    if failed_count:
        asked = years_asked or (len(rows) + failed_count)
        sentences.append(
            f"{_plural(failed_count, 'year')} of {asked} could not be fetched. {failure_text}"
        )
    return " ".join(s for s in sentences if s).strip()


def _station_records_sentence(records: dict[str, Any], station: str, unit: str) -> str:
    since = records.get("since")
    head = f"Records at {station}" + (f" since {since}" if since else "")
    parts: list[str] = []
    labels = (
        ("warmest_high", "warmest high"),
        ("coldest_low", "coldest low"),
        ("coldest_high", "coldest high"),
        ("warmest_low", "warmest low"),
    )
    for key, label in labels:
        rec = records.get(key)
        if isinstance(rec, dict) and rec.get("value") is not None:
            parts.append(f"{label} {temp_text(rec['value'], unit)} in {rec.get('year')}")
    for key, label, snow in (("wettest", "wettest", False), ("snowiest", "snowiest", True)):
        rec = records.get(key)
        if isinstance(rec, dict) and rec.get("value") is not None:
            amount = precip_text(rec["value"], unit, snow=snow)
            parts.append(f"{label} {amount} in {rec.get('year')}")
    if not parts:
        return ""
    return f"{head}: {', '.join(parts)}."


def _years_sentences(past: list[DayRecord], unit: str, *, have_station: bool) -> list[str]:
    count = len(past)
    span = f"the {_plural(count, 'year')} looked up" if count > 1 else "the one year looked up"
    out: list[str] = []
    highs = [r.high_c for r in past if r.high_c is not None]
    lows = [r.low_c for r in past if r.low_c is not None]
    avg_high, avg_low = temp_text(_mean(highs), unit), temp_text(_mean(lows), unit)
    if count >= 2 and avg_high and avg_low:
        out.append(f"Over {span}, the high averaged {avg_high} and the low {avg_low}.")
    warm = _extreme(past, "high_c", highest=True)
    cold = _extreme(past, "low_c", highest=False)
    wet = _extreme(past, "precip_mm", highest=True)
    bits: list[str] = []
    if warm:
        bits.append(f"warmest {temp_text(warm[1], unit)} in {warm[0].date[:4]}")
    if cold:
        bits.append(f"coldest low {temp_text(cold[1], unit)} in {cold[0].date[:4]}")
    if wet and wet[1] > 0:
        bits.append(f"wettest {precip_text(wet[1], unit)} in {wet[0].date[:4]}")
    if bits and count >= 2:
        label = f"In Open-Meteo's data for {span}" if have_station else f"In {span}"
        out.append(f"{label}: {', '.join(bits)}.")
    wet_days = sum(1 for r in past if (r.precip_mm or 0) >= 0.2 or (r.snow_cm or 0) > 0)
    if count >= 2:
        out.append(f"Rain or snow fell on this date in {wet_days} of {count} years.")
    return out


def range_summary(
    place: str,
    rows: list[DayRecord],
    *,
    unit: str,
    asked_days: int,
    failed_count: int = 0,
    failure_text: str = "",
) -> str:
    """The plain-words summary for a date range."""
    if not rows:
        if failed_count:
            return f"No days could be fetched for {place}. {failure_text}".strip()
        return f"Open-Meteo had no data for those dates in {place}."
    ordered = sorted(rows, key=lambda r: r.date)
    first, last = ordered[0].date, ordered[-1].date
    sentences = [
        f"From {date_text(first)} to {date_text(last)} in {place}, {_plural(len(ordered), 'day')}."
    ]
    highs = [r.high_c for r in ordered if r.high_c is not None]
    lows = [r.low_c for r in ordered if r.low_c is not None]
    if highs and lows:
        sentences.append(
            f"Highs averaged {temp_text(_mean(highs), unit)} and lows "
            f"{temp_text(_mean(lows), unit)}."
        )
    warm = _extreme(ordered, "high_c", highest=True)
    cold = _extreme(ordered, "low_c", highest=False)
    if warm:
        sentences.append(
            f"The warmest day was {date_text(warm[0].date, with_year=False)}, at "
            f"{temp_text(warm[1], unit)}."
        )
    if cold:
        sentences.append(
            f"The coldest night was {date_text(cold[0].date, with_year=False)}, at "
            f"{temp_text(cold[1], unit)}."
        )
    wettest = _extreme(ordered, "precip_mm", highest=True)
    total = sum(r.precip_mm or 0.0 for r in ordered)
    wet_days = sum(1 for r in ordered if (r.precip_mm or 0) >= 0.2)
    if total > 0:
        sentences.append(
            f"Total precipitation {precip_text(total, unit)}, on {_plural(wet_days, 'day')}."
        )
        if wettest and wet_days > 1:
            sentences.append(
                f"The wettest day was {date_text(wettest[0].date, with_year=False)}, with "
                f"{precip_text(wettest[1], unit)}."
            )
    else:
        sentences.append("No precipitation.")
    snow = sum(r.snow_cm or 0.0 for r in ordered)
    if snow > 0:
        sentences.append(f"Snowfall {precip_text(snow, unit, snow=True)}.")
    if failed_count:
        sentences.append(
            f"{_plural(failed_count, 'day')} of {asked_days} could not be fetched. {failure_text}"
        )
    return " ".join(sentences).strip()
