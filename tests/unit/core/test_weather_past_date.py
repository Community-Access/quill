"""Weather on a Past Date: understanding typed dates, why a date cannot be used,
one day in full from one request, the comparison with normal, the words, the
export, and the recent-dates list."""

from __future__ import annotations

import csv
import io
import urllib.error
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from quill.core.weather import date_query as q
from quill.core.weather import past_day, past_day_service, past_day_text, recent_dates
from quill.core.weather.history_cache import DayRecord, HistoryCache

TODAY = date(2026, 11, 27)
NOW = 1_800_000_000.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2011-03-14", date(2011, 3, 14)),
        ("14 March 2011", date(2011, 3, 14)),
        ("March 14, 2011", date(2011, 3, 14)),
        ("Mar 14th 2011", date(2011, 3, 14)),
        ("yesterday", date(2026, 11, 26)),
        ("3 days ago", date(2026, 11, 24)),
        ("two weeks ago", date(2026, 11, 13)),
        ("last week", date(2026, 11, 20)),
        ("a year ago today", date(2025, 11, 27)),
        ("last month", date(2026, 10, 27)),
    ],
)
def test_one_day(text: str, expected: date) -> None:
    found = q.parse(text, today=TODAY)
    assert (found.start, found.end) == (expected, expected)


def test_numeric_dates_follow_the_system_order_and_say_so() -> None:
    mdy = q.parse("3/4/2011", today=TODAY, order="MDY")
    assert mdy.start == date(2011, 3, 4) and "month first, as your system" in mdy.note
    dmy = q.parse("3/4/2011", today=TODAY, order="DMY")
    assert dmy.start == date(2011, 4, 3) and "day first, as your system" in dmy.note
    forced = q.parse("14/3/2011", today=TODAY, order="MDY")
    assert forced.start == date(2011, 3, 14) and "because 14 cannot be a month" in forced.note


def test_years_and_months_are_spans() -> None:
    assert q.parse("2011", today=TODAY).end == date(2011, 12, 31)
    march = q.parse("March 2011", today=TODAY)
    assert march.is_span and (march.start, march.end) == (date(2011, 3, 1), date(2011, 3, 31))
    assert q.parse("2011-02", today=TODAY).end == date(2011, 2, 28)
    assert q.parse("2/2012", today=TODAY).end == date(2012, 2, 29)


def test_not_understood_and_impossible_dates() -> None:
    with pytest.raises(q.DateNotUnderstood, match="did not understand"):
        q.parse("the day the dam broke", today=TODAY)
    with pytest.raises(q.DateNotUnderstood, match="no such date"):
        q.parse("2011-02-30", today=TODAY)
    with pytest.raises(q.DateNotUnderstood, match="Type a date"):
        q.parse("   ", today=TODAY)


def test_check_says_why() -> None:
    assert q.check(date(2030, 1, 1), today=TODAY)[0] is False
    assert "in the future" in q.check(date(2030, 1, 1), today=TODAY)[1]
    assert "before 1940" in q.check(date(1939, 12, 31), today=TODAY)[1]
    ok, note = q.check(date(2026, 11, 25), today=TODAY)
    assert ok and "within the last 5 days" in note
    assert q.check(date(2011, 3, 14), today=TODAY) == (True, "")
    span, why = q.clip_span(q.parse("1930", today=TODAY), today=TODAY)
    assert span is None and "before 1940" in why


def test_shift_keeps_the_day_where_it_can() -> None:
    assert q.shift(date(2024, 2, 29), years=1) == date(2025, 2, 28)
    assert q.shift(date(2011, 1, 31), months=1) == date(2011, 2, 28)
    assert q.shift(date(2011, 3, 14), days=-7) == date(2011, 3, 7)


# -- one day ----------------------------------------------------------------------


def _reply(iso: str) -> dict[str, Any]:
    hours = [f"{iso}T{h:02d}:00" for h in range(24)]
    return {
        "daily": {
            "time": [iso],
            "weather_code": [61],
            "temperature_2m_max": [16.0],
            "temperature_2m_min": [4.0],
            "apparent_temperature_max": [14.0],
            "apparent_temperature_min": [1.0],
            "precipitation_sum": [3.048],
            "snowfall_sum": [0.0],
            "precipitation_hours": [3.0],
            "wind_speed_10m_max": [30.0],
            "wind_gusts_10m_max": [50.0],
            "wind_direction_10m_dominant": [225.0],
            "sunrise": [f"{iso}T06:35"],
            "sunset": [f"{iso}T18:30"],
            "daylight_duration": [42960.0],
        },
        "hourly": {
            "time": hours,
            "temperature_2m": [10.0] * 24,
            "apparent_temperature": [8.0] * 24,
            "precipitation": [0.0] * 24,
            "snowfall": [0.0] * 24,
            "weather_code": [3] * 24,
            "wind_speed_10m": [16.0] * 24,
            "wind_direction_10m": [270.0] * 24,
            "relative_humidity_2m": [60.0] * 24,
        },
    }


class Fake:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str, **_k: Any) -> Any:
        self.urls.append(url)
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        if "hourly" in query:
            return _reply(query["start_date"])
        start = date.fromisoformat(query["start_date"])
        end = date.fromisoformat(query["end_date"])
        days = [date.fromordinal(o) for o in range(start.toordinal(), end.toordinal() + 1)]
        return {
            "daily": {
                "time": [d.isoformat() for d in days],
                "temperature_2m_max": [10.0] * len(days),
                "temperature_2m_min": [0.0] * len(days),
                "precipitation_sum": [0.0] * len(days),
            }
        }


def test_one_request_for_a_day_then_the_cache(tmp_path: Path) -> None:
    fake = Fake()
    cache = HistoryCache(tmp_path, 52.5, 13.4)
    day = past_day.fetch_day(52.5, 13.4, date(2011, 3, 14), today=TODAY, cache=cache, get=fake)
    assert day is not None and len(day.hours) == 24
    assert "archive-api" in fake.urls[0] and "start_date=2011-03-14" in fake.urls[0]
    cache.save()
    again = HistoryCache(tmp_path, 52.5, 13.4)
    assert past_day.fetch_day(
        52.5, 13.4, date(2011, 3, 14), today=TODAY, cache=again, get=fake
    ).hours  # type: ignore[union-attr]
    assert len(fake.urls) == 1
    assert "api.open-meteo.com/v1/forecast" in past_day.day_url(1, 2, date(2026, 11, 25), TODAY)


def test_day_words_read_like_the_report() -> None:
    day = past_day.parse(_reply("2011-03-14"), "2011-03-14", "archive")
    assert day is not None
    units = past_day_text.Units("F", "mph")
    lines = past_day_text.day_lines(day, "Berlin", units, compared="Compared with normal: x.")
    assert lines[0] == "Monday, March 14, 2011 in Berlin: light rain."
    assert lines[1] == "High 61 degrees, low 39."
    assert lines[2] == "Feels like 57 at the warmest and 34 at the coldest."
    assert lines[3] == "Precipitation 0.12 inches over 3 hours."
    assert lines[4] == (
        "Wind up to 19 miles per hour, gusts to 31 miles per hour, mostly from the southwest."
    )
    assert lines[5] == "Sunrise 6:35 AM, sunset 6:30 PM, 11 hours 56 minutes of daylight."
    assert lines[-1] == "Compared with normal: x."
    assert past_day_text.hour_cells(day.hours[15], units) == (
        "3:00 PM",
        "Overcast",
        "50",
        "46",
        "none",
        "10 miles per hour from the west",
    )
    assert past_day_text.spoken_summary(day, "Berlin", units) == "Light rain, high 61, low 39."


def test_compared_with_normal_outside_the_us_uses_the_average(tmp_path: Path) -> None:
    fake = Fake()
    result = past_day_service.look_up_day(
        date(2011, 3, 14),
        place="Berlin",
        latitude=52.5,
        longitude=13.4,
        units=past_day_text.Units("C", "km/h"),
        data_dir=tmp_path,
        today=TODAY,
        now=NOW,
        get_open_meteo=fake,
    )
    assert "Compared with normal: the high was 6 degrees above the average for this date" in (
        result.text
    )
    assert "over the 10 years before, 10." in result.text
    assert "ERA5" in result.credits and "RCC-ACIS" not in result.credits
    # One request for the day, one 31-day window per year for the average.
    assert len(fake.urls) == 11


def test_a_failed_day_is_said_as_a_failure(tmp_path: Path) -> None:
    def down(url: str, **_k: Any) -> Any:
        raise urllib.error.URLError("down")

    result = past_day_service.look_up_day(
        date(2011, 3, 14),
        place="Berlin",
        latitude=52.5,
        longitude=13.4,
        units=past_day_text.Units(),
        data_dir=tmp_path,
        today=TODAY,
        get_open_meteo=down,
    )
    assert result.day is None and "not the same as no data" in result.error


def test_range_export() -> None:
    rows = [
        DayRecord("2011-03-02", 0, 10.0, 0.0, 25.4, 0.0, 16.09),
        DayRecord("2011-03-01", 61, 12.0, 1.0, 0.0, 2.54, 8.0),
    ]
    text = past_day_text.range_csv(rows, past_day_text.Units("F", "mph"))
    table = list(csv.reader(io.StringIO(text)))
    assert table[0][:3] == ["Date", "Conditions", "High (F)"]
    assert table[1][0] == "2011-03-01" and table[1][5] == "1.0"
    assert table[2][4] == "1.00" and table[2][6] == "10.0"
    plain = past_day_text.range_text(rows, "Berlin", past_day_text.Units(), credits="C.")
    assert plain.startswith("Weather in Berlin, 2 days.") and plain.endswith("Sources: C.")


def test_recent_dates_newest_first_no_repeats(tmp_path: Path) -> None:
    entries: list[recent_dates.RecentDate] = []
    for i in range(12):
        entries = recent_dates.remember(
            entries, recent_dates.RecentDate(f"2011-03-{i + 1:02d}", "home", "Home")
        )
    entries = recent_dates.remember(entries, recent_dates.RecentDate("2011-03-05", "home", "Home"))
    assert len(entries) == 10 and entries[0].date == "2011-03-05"
    assert [e.date for e in entries].count("2011-03-05") == 1
    recent_dates.save(tmp_path, entries)
    assert recent_dates.load(tmp_path) == entries
    (tmp_path / "weather_recent_dates.json").write_text("{bad", encoding="utf-8")
    assert recent_dates.load(tmp_path) == []
