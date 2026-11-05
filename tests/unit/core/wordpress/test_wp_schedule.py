"""Scheduling, autosaves and the "did it land" check, with no wx (wordpress.md 5.8, 9.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from quill.core.wordpress import schedule as sch
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import Item

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


class FakeApi:
    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def _answer(self, method: str, route: str, params: dict[str, Any]) -> Any:
        self.calls.append((method, route, params))
        value = self.answers.get(route)
        if isinstance(value, BaseException):
            raise value
        return value

    def get(self, route: str, **params: Any) -> Any:
        return self._answer("GET", route, params)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        params = dict(params, body=body)
        return self._answer("POST", route, params)


# -- reading what was typed ---------------------------------------------------- #


def test_a_future_time_in_a_named_zone() -> None:
    when = sch.parse_schedule("2026-11-20", "16:15", "America/New_York", now=NOW)
    assert sch.date_gmt(when) == "2026-11-20T21:15:00"


def test_twelve_hour_times_are_understood() -> None:
    when = sch.parse_schedule("2026-11-20", "4:15 PM", "UTC", now=NOW)
    assert (when.hour, when.minute) == (16, 15)
    assert sch.parse_schedule("2026-11-20", "12:05 am", "UTC", now=NOW).hour == 0


@pytest.mark.parametrize(
    ("day", "clock", "words"),
    [
        ("20/11/2026", "09:00", "year, month and day"),
        ("2026-11-20", "25:00", "24-hour"),
        ("2026-11-20", "9", "24-hour"),
        ("2026-11-01", "09:00", "in the future"),
    ],
)
def test_what_cannot_be_scheduled_says_what_to_fix(day: str, clock: str, words: str) -> None:
    with pytest.raises(sch.ScheduleError) as caught:
        sch.parse_schedule(day, clock, "UTC", now=NOW)
    assert words in caught.value.plain


def test_an_unknown_zone_is_refused_plainly() -> None:
    with pytest.raises(sch.ScheduleError, match="does not know"):
        sch.zone_for("Mars/Olympus")


def test_this_computers_zone_follows_the_operating_system() -> None:
    when = sch.parse_schedule("2099-06-01", "09:00", sch.LOCAL, now=NOW)
    assert when.tzinfo is not None
    assert (when.hour, when.minute) == (9, 0)


def test_fixed_offsets_from_the_site() -> None:
    assert sch.offset_key(-5) == "UTC-05:00"
    assert sch.offset_key(5.5) == "UTC+05:30"
    assert sch.zone_for("UTC+05:30") == timezone(timedelta(hours=5, minutes=30))


def test_the_sites_zone_comes_first_then_this_computer() -> None:
    keys = sch.zone_keys("Europe/London")
    assert keys[:3] == ["Europe/London", sch.LOCAL, "UTC"]
    assert keys.count("Europe/London") == 1
    assert sch.zone_keys("")[:2] == [sch.LOCAL, "UTC"]
    assert sch.zone_label("Europe/London", "Europe/London") == "The site's time zone, Europe/London"
    assert sch.zone_label(sch.LOCAL) == sch.LOCAL_LABEL


def test_the_sites_zone_is_read_from_its_rest_index() -> None:
    assert sch.site_time_zone(FakeApi({"": {"timezone_string": "Europe/Paris"}})) == "Europe/Paris"
    assert sch.site_time_zone(FakeApi({"": {"timezone_string": "", "gmt_offset": -5}})) == (
        "UTC-05:00"
    )
    assert sch.site_time_zone(FakeApi({"": {"name": "x"}})) == ""


def test_spoken_times() -> None:
    when = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
    assert sch.spoken_moment(when) == "Friday 20 November 2026, 9:00 AM"
    assert sch.when_spoken("2026-11-03T16:12:00", now=NOW, zone=UTC) == "yesterday, 4:12 PM"
    assert sch.when_spoken("2026-11-04T08:05:00", now=NOW, zone=UTC) == "today, 8:05 AM"
    assert sch.when_spoken("2025-10-01T13:00:00", now=NOW, zone=UTC) == "1 October 2025, 1:00 PM"


# -- on the site ------------------------------------------------------------------ #


def _item(**over: Any) -> Item:
    base: dict[str, Any] = dict(
        id=41, kind="page", title="Hours", content="<p>Old</p>", status="publish"
    )
    base.update(over)
    return Item(**base)


def test_send_scheduled_sends_future_with_the_date() -> None:
    api = FakeApi({"wp/v2/pages/41": {"id": 41, "status": "future", "type": "page"}})
    saved = sch.send_scheduled(api, _item(status="future"), "2026-11-20T21:15:00")
    body = api.calls[0][2]["body"]
    assert body["status"] == "future" and body["date_gmt"] == "2026-11-20T21:15:00"
    assert saved.status == "future"


def test_a_newer_different_autosave_is_offered() -> None:
    api = FakeApi({
        "wp/v2/pages/41/autosaves": [
            {"modified_gmt": "2026-11-03T16:12:00", "title": {"raw": "Hours"}, "content": "New"},
            {"modified_gmt": "2026-11-01T10:00:00", "title": {"raw": "Hours"}, "content": "Older"},
        ]
    })
    autosave = sch.newer_autosave(api, _item(modified_gmt="2026-11-02T00:00:00"))
    assert autosave is not None and autosave.content == "New"


def test_an_older_or_identical_autosave_is_not_offered() -> None:
    older = FakeApi({
        "wp/v2/pages/41/autosaves": [{"modified_gmt": "2026-11-01T00:00:00", "content": "x"}]
    })
    assert sch.newer_autosave(older, _item(modified_gmt="2026-11-02T00:00:00")) is None
    same = FakeApi({
        "wp/v2/pages/41/autosaves": [
            {"modified_gmt": "2026-11-03T00:00:00", "title": "Hours", "content": "<p>Old</p>"}
        ]
    })
    assert sch.newer_autosave(same, _item(modified_gmt="2026-11-02T00:00:00")) is None


def test_autosaves_the_account_cannot_read_are_simply_none() -> None:
    api = FakeApi({"wp/v2/pages/41/autosaves": WordPressApiError("no", status=403)})
    assert sch.latest_autosave(api, "page", 41) is None


def test_find_landed_for_a_new_item_matches_title_after_the_send_began() -> None:
    api = FakeApi({
        "wp/v2/pages": [
            {"id": 9, "title": {"raw": "Hours"}, "modified_gmt": "2026-10-01T00:00:00"},
            {"id": 12, "title": {"raw": "Hours"}, "modified_gmt": "2026-11-04T12:00:30"},
        ]
    })
    found = sch.find_landed(
        api, kind="page", title="Hours", slug="", since_gmt="2026-11-04T12:00:00"
    )
    assert found is not None and found.id == 12
    assert api.calls[0][2]["search"] == "Hours"


def test_find_landed_for_an_update_needs_the_same_content() -> None:
    raw = {"id": 41, "title": {"raw": "Hours"}, "content": {"raw": "<p>Mine</p>"}}
    api = FakeApi({"wp/v2/pages/41": dict(raw, modified_gmt="2026-11-04T12:01:00")})
    kwargs = dict(kind="page", title="Hours", slug="", since_gmt="2026-11-04T12:00:00", item_id=41)
    assert sch.find_landed(api, content="<p>Mine</p>", **kwargs) is not None
    assert sch.find_landed(api, content="<p>Other</p>", **kwargs) is None
