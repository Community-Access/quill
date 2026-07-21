"""Tests for optimal-time suggestions (PRD 18.11)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from quill_social.services import optimal_time as ot


def _ms(year, month, day, hour, tz="UTC"):
    dt = datetime(year, month, day, hour, 0, tzinfo=ZoneInfo(tz))
    return int(dt.timestamp() * 1000)


def test_empty_history_returns_nothing():
    assert ot.suggest([], "UTC") == []


def test_ranking_by_average_engagement():
    history = []
    # Monday 09:00 (weekday 0): high engagement, several samples.
    for month, day in ((7, 6), (7, 13), (7, 20), (7, 27), (8, 3)):  # five Mondays
        history.append((_ms(2026, month, day, 9), 100.0))
    # Tuesday 14:00 (weekday 1): low engagement.
    for day in (7, 14, 21):
        history.append((_ms(2026, 7, day, 14), 10.0))
    suggestions = ot.suggest(history, "UTC", top_n=2)
    assert suggestions[0].weekday == 0 and suggestions[0].hour == 9
    assert suggestions[0].score == 100.0
    assert suggestions[1].weekday == 1 and suggestions[1].hour == 14


def test_small_sample_flagged_honestly():
    history = [(_ms(2026, 7, 6, 9), 50.0)]  # single sample
    suggestions = ot.suggest(history, "UTC")
    s = suggestions[0]
    assert s.sample_size == 1
    assert not s.confident
    assert "few" in s.explanation.lower()


def test_explanation_present_and_non_committal():
    history = [
        (_ms(2026, m, d, 9), 20.0)
        for m, d in ((7, 6), (7, 13), (7, 20), (7, 27), (8, 3))
    ]
    suggestions = ot.suggest(history, "UTC")
    s = suggestions[0]
    assert s.confident
    assert s.explanation
    assert "guarantee" in s.explanation.lower() or "suggestion" in s.explanation.lower()
    assert "certain" not in s.explanation.lower()


def test_timezone_shifts_bucket():
    # 02:00 UTC is 22:00 previous day in America/New_York (weekday shifts too).
    history = [(_ms(2026, 7, 14, 2), 30.0)]  # Tuesday 02:00 UTC
    utc = ot.suggest(history, "UTC")[0]
    ny = ot.suggest(history, "America/New_York")[0]
    assert utc.hour == 2 and utc.weekday == 1  # Tuesday
    assert ny.hour == 22 and ny.weekday == 0  # Monday 22:00


def test_top_n_limits_results():
    history = [
        (_ms(2026, 7, 6, 9), 5.0),
        (_ms(2026, 7, 7, 10), 4.0),
        (_ms(2026, 7, 8, 11), 3.0),
        (_ms(2026, 7, 9, 12), 2.0),
    ]
    assert len(ot.suggest(history, "UTC", top_n=2)) == 2


def test_suggestion_to_dict():
    history = [(_ms(2026, 7, 6, 9), 20.0)]
    d = ot.suggest(history, "UTC")[0].to_dict()
    assert d["weekday_name"] == "Monday"
    assert d["hour"] == 9
    assert "explanation" in d
