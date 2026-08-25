"""Refreshing the ACB Media schedule, and being able to tell that it happened.

All three of these pin the same bug from different sides. The schedule is
cached for an hour and the summary line said nothing at all about a *live*
fetch, so pressing Refresh rewrote the sentence to an identical sentence --
and closing the app and opening it again did not re-read anything, because the
cache outlived the process. "It will not refresh" was the reported symptom
(2026-08-25); the feed was fine every time.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quill.core.radio import acb_calendar, calendar_actions
from quill.core.radio.ics import CalendarEvent

NOW = datetime(2026, 8, 25, 16, 47, tzinfo=UTC)


def _event(day: int = 24) -> CalendarEvent:
    start = datetime(2026, 8, day, 13, 0, tzinfo=UTC)
    return CalendarEvent(
        uid=f"uid-{day}",
        summary="ACB Presents the Daily Schedule",
        start=start,
        end=start + timedelta(hours=1),
        categories=("ACB Media 5",),
    )


def test_a_live_pull_says_so_rather_than_saying_nothing() -> None:
    """The whole bug: a successful Refresh used to change not one word."""
    events = [_event()]

    said = calendar_actions.summarise_schedule(events, events, NOW, None, pulled_at=NOW)

    assert "Pulled from ACB just now" in said


def test_a_cached_copy_carries_a_clock_time_not_only_a_phrase() -> None:
    """ "Three hours ago" is not answerable on a second press. A time is."""
    pulled = NOW - timedelta(hours=3)
    events = [_event()]

    said = calendar_actions.summarise_schedule(events, events, NOW, 3 * 3600.0, pulled_at=pulled)

    assert "3 hours ago" in said
    assert pulled.astimezone().strftime("%I:%M %p").lstrip("0") in said


def test_a_pull_from_another_day_says_which_day() -> None:
    pulled = NOW - timedelta(hours=30)

    said = calendar_actions.pull_note(30 * 3600.0, pulled, NOW)

    assert "yesterday" in said
    assert f"{pulled.astimezone().day} {pulled.astimezone().strftime('%B')}" in said


def test_a_pull_from_today_does_not_recite_the_date() -> None:
    """A timestamp that reads out a date every time is one nobody hears out."""
    said = calendar_actions.pull_note(600.0, NOW - timedelta(minutes=10), NOW)

    assert "August" not in said


def test_a_caller_with_no_pull_time_keeps_the_old_fragment() -> None:
    """summarise_schedule's fourth argument is positional and pre-dates this."""
    events = [_event()]

    said = calendar_actions.summarise_schedule(events, events, NOW, None)

    assert "Pulled from ACB" not in said


def test_an_empty_month_still_says_when_it_was_looked_for() -> None:
    """The emptiest list is where "is this current?" matters most."""
    said = calendar_actions.summarise_schedule([], [], NOW, None, pulled_at=NOW)

    assert "ACB has published no schedule" in said
    assert "Pulled from ACB just now" in said


def test_a_listener_asked_fetch_tells_intermediaries_not_to_cache(monkeypatch) -> None:
    """Our disk cache is bypassed by then; a CDN's is not, unless we say so."""
    seen: dict[str, str] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"

    def _urlopen(request, **_kwargs):
        seen.update(request.headers)
        return _Response()

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)

    acb_calendar._fetch_ics(NOW, no_cache=True)
    assert seen.get("Cache-control") == "no-cache"
    assert seen.get("Pragma") == "no-cache"

    seen.clear()
    acb_calendar._fetch_ics(NOW)
    assert "Cache-control" not in seen
    assert "Pragma" not in seen


def test_the_forced_fetch_is_the_one_a_refresh_asks_for(monkeypatch) -> None:
    """refresh=True has to reach _fetch_ics as no_cache, not stop at resolve."""
    asked: list[bool] = []

    def _fetch(_moment, *, no_cache: bool = False):
        asked.append(no_cache)
        return [
            {
                "uid": "u",
                "summary": "s",
                "start": "2026-08-24T13:00:00+00:00",
                "end": "2026-08-24T14:00:00+00:00",
                "categories": ["ACB Media 5"],
                "description": "",
                "location": "",
            }
        ]

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _fetch)
    monkeypatch.setattr(
        acb_calendar,
        "cache_key",
        lambda moment: f"test-acb-refresh-{moment:%Y-%m}",
    )

    acb_calendar.fetch_schedule(when=NOW, refresh=True)

    assert asked == [True]


@pytest.mark.parametrize("safe", [True, False])
def test_safe_mode_never_fetches_however_hard_refresh_is_pressed(monkeypatch, safe: bool) -> None:
    calls: list[int] = []

    def _fetch(_moment, *, no_cache: bool = False):
        calls.append(1)
        return []

    monkeypatch.setattr(acb_calendar, "_fetch_ics", _fetch)
    monkeypatch.setattr(acb_calendar, "cache_key", lambda moment: f"test-acb-safe-{moment:%Y-%m}")

    acb_calendar.fetch_schedule(when=NOW, refresh=True, safe_mode=safe)

    assert bool(calls) is not safe
