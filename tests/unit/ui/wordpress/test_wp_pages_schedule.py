"""Schedule Publish, Change Schedule and Publish Now, behaviourally (wordpress.md 5.8)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.ui import wordpress_schedule_dialog as sdlg

API = "/wp-json/wp/v2"

EDITOR = {
    "id": 7,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["editor"],
    "capabilities": {"publish_posts": True, "publish_pages": True},
}


def _open_copy(wp: Any, *, status: str = "draft", remote_id: int = 41, **props: Any) -> Any:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=remote_id,
        title="Our Schedule",
        text="<p>Hi</p>",
        text_format="html",
        base_modified_gmt="2026-11-04T10:00:00" if remote_id else "",
        status=status,
        properties=dict(props),
    )
    wp.host.open_path(wp.local.write_document(copy))
    return copy


def _page(status: str, **over: Any) -> dict[str, Any]:
    raw = {
        "id": 41,
        "type": "page",
        "title": {"raw": "Our Schedule"},
        "content": {"raw": "<p>Hi</p>"},
        "status": status,
        "link": "https://radio.example/?page_id=41",
        "modified_gmt": "2026-11-04T10:00:00",
        "date_gmt": "2099-01-02T14:00:00",
    }
    raw.update(over)
    return raw


@pytest.fixture
def when(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Scripted answers for the Schedule Publish window; each call records its arguments."""
    answers: list[Any] = []
    asked: list[dict[str, Any]] = []

    def ask(_parent: Any, _show_modal: Any, **kwargs: Any) -> Any:
        asked.append(kwargs)
        return answers.pop(0) if answers else None

    monkeypatch.setattr(sdlg, "ask_schedule", ask)
    answers_and_asked: list[Any] = [answers, asked]
    return answers_and_asked


def _site(wp_site: Any, *, saved_status: str = "future", zone: str = "Europe/London") -> None:
    wp_site.on("GET", "/wp-json/", {"timezone_string": zone})
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("GET", f"{API}/pages/41", _page("draft"))
    wp_site.on("POST", f"{API}/pages/41", _page(saved_status))


def test_outside_a_wordpress_document_it_says_so(wp) -> None:
    wp.cmd_schedule()
    assert "not a WordPress document" in wp.host.said


def test_schedule_asks_with_the_sites_zone_first_and_sends_future(wp, wp_site, wp_dialogs, when):
    _open_copy(wp)
    _site(wp_site)
    when[0].append(sdlg.ScheduleAnswer("2099-01-02", "14:00", 0))
    wp_dialogs.answer("confirm", True)
    wp.cmd_schedule()
    asked = when[1][0]
    assert asked["zones"][0] == "The site's time zone, Europe/London"
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert "Our Schedule" in message and "Community Radio" in message
    assert "Friday 2 January 2099, 2:00 PM" in message
    body = wp_site.body(wp_site.sent("POST", f"{API}/pages/41")[0])
    assert body["status"] == "future"
    assert body["date_gmt"] == "2099-01-02T14:00:00"
    assert wp.host.announced[-1].startswith("Scheduled on Community Radio for Friday 2 January")
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.status == "future"
    assert copy.properties["date_gmt"] == "2099-01-02T14:00:00"


def test_a_site_with_no_zone_starts_on_this_computers(wp, wp_site, when) -> None:
    _open_copy(wp)
    _site(wp_site, zone="")
    wp.cmd_schedule()
    assert when[1][0]["zones"][0] == "This computer's time zone"


def test_a_bad_date_is_asked_again_with_the_reason(wp, wp_site, wp_dialogs, when) -> None:
    _open_copy(wp)
    _site(wp_site)
    when[0].extend([
        sdlg.ScheduleAnswer("2001-01-01", "09:00", 0),
        sdlg.ScheduleAnswer("2099-01-02", "14:00", 0),
    ])
    wp_dialogs.answer("confirm", True)
    wp.cmd_schedule()
    assert when[1][0]["error"] == ""
    assert "in the future" in when[1][1]["error"]
    assert when[1][1]["date_text"] == "2001-01-01"
    assert len(wp_site.sent("POST", f"{API}/pages/41")) == 1


def test_cancelling_the_window_or_the_confirmation_sends_nothing(wp, wp_site, when) -> None:
    _open_copy(wp)
    _site(wp_site)
    wp.cmd_schedule()  # window cancelled
    when[0].append(sdlg.ScheduleAnswer("2099-01-02", "14:00", 0))
    wp.cmd_schedule()  # confirmation cancelled (unscripted)
    assert wp_site.sent("POST", f"{API}/pages/41") == []


def test_a_new_page_is_created_scheduled(wp, wp_site, wp_dialogs, when) -> None:
    _open_copy(wp, remote_id=0)
    _site(wp_site)
    wp_site.on("POST", f"{API}/pages", _page("future"))
    when[0].append(sdlg.ScheduleAnswer("2099-01-02", "14:00", 1))
    wp_dialogs.answer("confirm", True)
    wp.cmd_schedule()
    assert wp_site.body(wp_site.sent("POST", f"{API}/pages")[0])["status"] == "future"
    assert wp.local.copy_for_path(wp.host.current_path()).remote_id == 41


def test_a_contributor_cannot_schedule(wp, wp_site, wp_dialogs, when) -> None:
    _open_copy(wp)
    _site(wp_site)
    wp_site.on("GET", f"{API}/users/me", dict(EDITOR, roles=["contributor"], capabilities={}))
    when[0].append(sdlg.ScheduleAnswer("2099-01-02", "14:00", 0))
    wp_dialogs.answer("confirm", True)
    wp.cmd_schedule()
    assert "cannot schedule" in wp.host.announced[-1]
    assert wp_site.sent("POST", f"{API}/pages/41") == []


def test_a_changed_site_copy_stops_the_schedule(wp, wp_site, wp_dialogs, when) -> None:
    _open_copy(wp)
    _site(wp_site)
    wp_site.on("GET", f"{API}/pages/41", _page("draft", modified_gmt="2026-11-04T11:00:00"))
    when[0].append(sdlg.ScheduleAnswer("2099-01-02", "14:00", 0))
    wp_dialogs.answer("confirm", True)
    wp.cmd_schedule()
    assert "Nothing was sent" in wp.host.announced[-1]
    assert wp_site.sent("POST", f"{API}/pages/41") == []


def test_a_scheduled_item_offers_change_schedule(wp, wp_site, wp_dialogs, when) -> None:
    _open_copy(wp, status="future", date_gmt="2099-01-01T09:00:00")
    _site(wp_site)
    wp_dialogs.answer("ask_choice", 0)
    when[0].append(sdlg.ScheduleAnswer("2099-01-02", "14:00", 0))
    wp_dialogs.answer("confirm", True)
    wp.cmd_schedule()
    rows = wp_dialogs.asked("ask_choice")[0]["rows"]
    assert rows == ["Change the schedule", "Publish now"]
    assert wp_site.body(wp_site.sent("POST", f"{API}/pages/41")[0])["status"] == "future"


def test_publish_now_publishes_a_scheduled_item_today(wp, wp_site, wp_dialogs, when) -> None:
    _open_copy(wp, status="future", date_gmt="2099-01-01T09:00:00")
    _site(wp_site, saved_status="publish")
    wp_dialogs.answer("ask_choice", 1, 1)  # Publish now; then "Not this time" for menus
    wp_dialogs.answer("confirm", True)
    wp.cmd_schedule()
    assert when[1] == []  # no date asked
    body = wp_site.body(wp_site.sent("POST", f"{API}/pages/41")[0])
    assert body["status"] == "publish"
    assert body["date_gmt"] < "2099"
    assert wp.host.clipboard == "https://radio.example/?page_id=41"
    assert any(a.startswith("Published on Community Radio") for a in wp.host.announced)


def test_cancelling_the_scheduled_choice_does_nothing(wp, wp_site, when) -> None:
    _open_copy(wp, status="future")
    _site(wp_site)
    wp.cmd_schedule()
    assert wp_site.requests == []
