"""Weather History: routing between Open-Meteo's two services, one request per
year for the same date, the permanent cache, ACIS records and normals, the
plain-words summary, credits, and "could not reach" never read as "no data"."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from quill.core.weather import acis, data_feed_health, history, history_service, history_text
from quill.core.weather.history_cache import DayRecord, HistoryCache

TODAY = date(2026, 11, 27)
NOW = 1_800_000_000.0


def _daily(days: list[date], high: float = 20.0) -> dict[str, Any]:
    return {
        "daily": {
            "time": [d.isoformat() for d in days],
            "weather_code": [61] * len(days),
            "temperature_2m_max": [high + i for i in range(len(days))],
            "temperature_2m_min": [5.0] * len(days),
            "precipitation_sum": [2.0] * len(days),
            "snowfall_sum": [0.0] * len(days),
            "wind_speed_10m_max": [10.0] * len(days),
        }
    }


class FakeOpenMeteo:
    """Answers like Open-Meteo: archive by start/end, recent by past_days."""

    def __init__(self, *, fail_archive: bool = False) -> None:
        self.urls: list[str] = []
        self.fail_archive = fail_archive

    def __call__(self, url: str, *, weight: int = 1) -> Any:
        self.urls.append(url)
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        if "archive-api" in url:
            if self.fail_archive:
                raise urllib.error.URLError("down")
            start = date.fromisoformat(query["start_date"])
            end = date.fromisoformat(query["end_date"])
            return _daily([start + timedelta(days=i) for i in range((end - start).days + 1)])
        past = int(query["past_days"])
        return _daily([TODAY - timedelta(days=past - i) for i in range(past + 1)])


def test_route_splits_at_92_days() -> None:
    assert history.route(TODAY, TODAY) == "recent"
    assert history.route(TODAY - timedelta(days=92), TODAY) == "recent"
    assert history.route(TODAY - timedelta(days=93), TODAY) == "archive"


def test_same_date_dates_newest_first_and_leap_day() -> None:
    dates = history.same_date_dates(11, 27, 3, TODAY)
    assert dates == [date(2026, 11, 27), date(2025, 11, 27), date(2024, 11, 27)]
    later = history.same_date_dates(12, 25, 2, TODAY)
    assert later == [date(2025, 12, 25), date(2024, 12, 25)]  # not yet this year
    leap = history.same_date_dates(2, 29, 3, TODAY)
    assert [d.year for d in leap] == [2024, 2020, 2016]


def test_range_is_clipped_to_today_and_a_year() -> None:
    assert history.range_dates(TODAY, TODAY + timedelta(days=5), TODAY) == [TODAY]
    assert len(history.range_dates(date(2000, 1, 1), date(2003, 1, 1), TODAY)) == 366
    assert history.range_dates(date(1900, 1, 1), date(1900, 2, 1), TODAY) == []


def test_one_request_per_year_then_the_cache_answers(tmp_path: Path) -> None:
    get = FakeOpenMeteo()
    cache = HistoryCache(tmp_path, 32.2, -110.9)
    wanted = history.same_date_dates(11, 27, 20, TODAY)
    result = history.fetch_days(32.2, -110.9, wanted, today=TODAY, cache=cache, now=NOW, get=get)
    archive = [u for u in get.urls if "archive-api" in u]
    recent = [u for u in get.urls if "archive-api" not in u]
    assert len(archive) == 19 and len(recent) == 1  # this year's from past_days
    assert len(result.days) == 20 and result.sources == {"recent", "archive"}
    cache.save()

    get2 = FakeOpenMeteo()
    again = HistoryCache(tmp_path, 32.2, -110.9)
    result2 = history.fetch_days(32.2, -110.9, wanted, today=TODAY, cache=again, now=NOW, get=get2)
    # Only today is refetched: it is still happening. The past is kept for good.
    assert len(get2.urls) == 1 and "past_days" in get2.urls[0]
    assert len(result2.days) == 20


def test_a_range_is_one_request_per_stretch(tmp_path: Path) -> None:
    get = FakeOpenMeteo()
    cache = HistoryCache(tmp_path, 1.0, 2.0)
    wanted = history.range_dates(date(2024, 6, 1), date(2024, 6, 30), TODAY)
    result = history.fetch_days(1.0, 2.0, wanted, today=TODAY, cache=cache, now=NOW, get=get)
    assert len(get.urls) == 1 and len(result.days) == 30


def test_failure_is_kept_apart_from_no_data(tmp_path: Path) -> None:
    get = FakeOpenMeteo(fail_archive=True)
    outcomes: list[tuple[str, bool]] = []
    result = history.fetch_days(
        1.0,
        2.0,
        [date(2000, 1, 1)],
        today=TODAY,
        cache=HistoryCache(tmp_path, 1.0, 2.0),
        now=NOW,
        get=get,
        on_outcome=lambda feed, err: outcomes.append((feed, err is None)),
    )
    assert result.days == [] and "2000-01-01" in result.failed
    assert outcomes == [("open_meteo_archive", False)]
    sentence = data_feed_health.failure_sentence("open_meteo_archive", result.failures()[0][1])
    assert "not the same as no data" in sentence


def test_safe_mode_refuses() -> None:
    with pytest.raises(history.HistoryError):
        history.fetch_days(
            1, 2, [TODAY], today=TODAY, cache=HistoryCache(None, 1, 2), safe_mode=True
        )


# -- the words --------------------------------------------------------------------


def _rec(iso: str, high: float, low: float = 0.0, precip: float = 0.0) -> DayRecord:
    return DayRecord(date=iso, code=0, high_c=high, low_c=low, precip_mm=precip)


def test_summary_against_station_normals_and_records() -> None:
    rows = [_rec("2026-11-27", 5.0)] + [_rec(f"{y}-11-27", 8.0) for y in range(2006, 2026)]
    climate = history_text.Climate(
        station_name="Tucson International Airport",
        normals={"high_c": 8.33, "low_c": 0.0},
        records={
            "since": 1946,
            "warmest_high": {"value": 33.3, "year": 2017},
            "coldest_low": {"value": -3.3, "year": 1984},
            "wettest": {"value": 6.6, "year": 2008},
        },
    )
    text = history_text.same_date_summary(
        "Tucson", 11, 27, rows, today=TODAY, unit="F", climate=climate
    )
    assert "Today's forecast high of 41 degrees is 6 degrees below the 1991 to 2020 normal" in text
    assert "of 47 at Tucson International Airport, where the normal low is 32" in text
    assert "Records at Tucson International Airport since 1946: warmest high 92 in 2017" in text
    assert "wettest 0.26 inches in 2008" in text
    assert "Rain or snow fell on this date in 0 of 20 years." in text


def test_summary_without_a_station_says_years_not_records() -> None:
    rows = [_rec(f"{y}-01-15", 5.0 + (y - 2016), precip=1.0) for y in range(2016, 2026)]
    text = history_text.same_date_summary("Berlin", 1, 15, rows, today=TODAY, unit="C")
    assert "Records" not in text and "record" not in text
    assert "Over the 10 years looked up, the high averaged 10" in text
    assert "warmest 14 in 2025" in text and "wettest 1 millimetre in 2016" in text


def test_range_summary() -> None:
    rows = [_rec("2024-06-01", 40.0, 20.0, 0.0), _rec("2024-06-02", 44.0, 25.0, 5.08)]
    text = history_text.range_summary("Tucson", rows, unit="F", asked_days=2)
    assert "From June 1, 2024 to June 2, 2024 in Tucson, 2 days." in text
    assert "The warmest day was June 2, at 111." in text
    assert "Total precipitation 0.20 inches, on 1 day." in text


def test_units_and_rows() -> None:
    assert history_text.precip_text(0.0, "F") == "none"
    assert history_text.precip_text(0.05, "F") == "a trace"
    assert history_text.precip_text(25.4, "F") == "1 inch"
    assert history_text.precip_text(6.0, "C") == "6 millimetres"
    cells = history_text.row_cells(_rec("2024-06-01", 40.0, 20.0, 0.0), "F")
    assert cells == ("June 1, 2024", "Clear", "104", "68", "none")


def test_credits_follow_the_sources() -> None:
    assert history_text.credits_for({"recent"}, used_acis=False) == history_text.CREDIT_OPEN_METEO
    full = history_text.credits_for({"archive"}, used_acis=True)
    assert "ERA5" in full and "RCC-ACIS" in full and "Open-Meteo.com" in full


# -- ACIS -------------------------------------------------------------------------


META = {
    "meta": [
        {
            "name": "SHORT 1.0 N",
            "sids": ["US1 6"],
            "ll": [-110.95, 32.2],
            "valid_daterange": [["2015-01-01", "2026-11-26"]] * 3,
        },
        {
            "name": "TUCSON INTERNATIONAL AIRPORT",
            "sids": ["23160 1", "USW00023160 6"],
            "ll": [-110.956, 32.131],
            "valid_daterange": [["1946-06-01", "2026-11-26"]] * 3,
        },
        {
            "name": "RAIN GAUGE ONLY",
            "sids": ["X 6"],
            "ll": [-110.9, 32.2],
            "valid_daterange": [[], [], ["2000-01-01", "2026-11-26"]],
        },
    ]
}


def test_station_choice_prefers_a_long_record() -> None:
    found = acis.stations_from_meta(META, 32.2, -110.95, TODAY)
    assert [s.sid for s in found] == ["23160", "US1"]
    assert found[0].display_name == "Tucson International Airport"


def test_records_and_normals_parse(tmp_path: Path) -> None:
    station = acis.Station("23160", "TUCSON", 32.1, -110.9, 1946, 9.0)
    seen: list[dict[str, Any]] = []

    def get(url: str) -> Any:
        params = json.loads(
            dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))["params"]
        )
        seen.append(params)
        if "normal" in json.dumps(params):
            return {"data": [["2024-11-27", "70", "44", "0.02"]]}
        return {
            "smry": [
                ["92", "2017-11-27"],
                ["51", "1948-11-27"],
                ["55", "2024-11-27"],
                ["26", "1984-11-27"],
                ["T", "2008-11-27"],
                ["M", ""],
            ]
        }

    normals = acis.normals(station, 11, 27, get=get)
    assert round(normals["high_c"] * 9 / 5 + 32) == 70
    recs = acis.records(station, 11, 27, today=TODAY, get=get)
    assert recs["warmest_high"]["year"] == 2017 and "wettest" not in recs  # a trace is no record
    assert seen[1]["sdate"] == "1946-11-27" and seen[1]["edate"] == "2025-11-27"


def test_look_up_marks_acis_failure_without_losing_the_rest(tmp_path: Path) -> None:
    def broken_acis(url: str) -> Any:
        raise urllib.error.URLError("down")

    health = data_feed_health.DataFeedHealth()
    result = history_service.look_up(
        history_service.Query("on_this_day", years=5),
        place="Tucson",
        latitude=32.2,
        longitude=-110.9,
        unit="F",
        data_dir=tmp_path,
        today=TODAY,
        now=NOW,
        health=health,
        get_open_meteo=FakeOpenMeteo(),
        get_acis=broken_acis,
    )
    assert len(result.rows) == 5
    assert "Station records: Quill Weather could not get this from" in result.summary
    assert "RCC-ACIS" not in result.credits
    assert health.state_of("rcc_acis", NOW).value == "degraded"
    assert any("Open-Meteo history" in line for line in health.status_lines(NOW))


def test_cache_survives_a_damaged_file(tmp_path: Path) -> None:
    cache = HistoryCache(tmp_path, 1.0, 2.0)
    cache.put_day(_rec("2000-01-01", 1.0), NOW)
    cache.save()
    assert cache.path is not None
    cache.path.write_text("{not json", encoding="utf-8")
    assert HistoryCache(tmp_path, 1.0, 2.0).days == {}


def test_data_feed_health_round_trip(tmp_path: Path) -> None:
    health = data_feed_health.DataFeedHealth()
    health.record_success("open_meteo_archive", NOW)
    data_feed_health.save(tmp_path, health)
    again = data_feed_health.load(tmp_path)
    assert again.state_of("open_meteo_archive", NOW).value == "healthy"
    assert set(data_feed_health.FEEDS) >= {"open_meteo_archive", "rcc_acis", "open_meteo_recent"}
