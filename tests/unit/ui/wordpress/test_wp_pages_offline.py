"""Sends that got no answer, and the offline queue (wordpress.md 5.10; 15, "Working offline")."""

from __future__ import annotations

from typing import Any
from urllib.error import URLError

from quill.core.wordpress import local as lc
from quill.ui import wordpress_item_dialogs as idlg

API = "/wp-json/wp/v2"

EDITOR = {
    "id": 7,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["editor"],
    "capabilities": {"publish_posts": True, "publish_pages": True},
}


def _saved(status: str = "draft", item_id: int = 41, **over: Any) -> dict[str, Any]:
    raw = {
        "id": item_id,
        "type": "page",
        "title": {"raw": "Hours"},
        "content": {"raw": "<p>Hi</p>"},
        "slug": "hours",
        "status": status,
        "link": f"https://radio.example/?page_id={item_id}",
        "modified_gmt": "2099-01-01T00:00:00",
    }
    raw.update(over)
    return raw


def _new_page(wp: Any, wp_dialogs: Any, title: str = "Hours") -> None:
    wp_dialogs.answer(
        "ask_new_item",
        idlg.NewItemAnswer(
            site_index=0,
            title=title,
            slug="hours",
            text_format="html",
            category_ids=[],
            tag_ids=[],
        ),
    )
    wp.cmd_new_page()
    wp.host.text = "<p>Hi</p>"


def _offline(wp_site: Any) -> None:
    for route in list(wp_site.routes):
        wp_site.routes.pop(route)
    for method in ("GET", "POST"):
        for path in (f"{API}/users/me", f"{API}/pages", f"{API}/pages/41"):
            wp_site.on(method, path, URLError("timed out"))


def _queue(wp: Any) -> list[Any]:
    return wp.offline_queue().entries()


# --------------------------------------------------------------------------- #
# a send with no answer re-reads the site first (5.10)


def test_a_send_that_landed_after_all_is_not_sent_twice(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("POST", f"{API}/pages", URLError("timed out"))
    wp_site.on("GET", f"{API}/pages", [_saved()])  # the re-read finds it
    wp.cmd_save_draft()
    assert len(wp_site.sent("POST", f"{API}/pages")) == 1
    assert wp_dialogs.asked("confirm") == []
    assert wp.host.announced[-1] == "Draft saved to Community Radio. It is not public."
    assert wp.local.copy_for_path(wp.host.current_path()).remote_id == 41


def test_a_send_that_did_not_land_offers_try_again(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("POST", f"{API}/pages", URLError("timed out"))
    wp_site.on("GET", f"{API}/pages", [])
    wp_dialogs.answer("confirm", True)  # Try Again
    tries: list[int] = []

    def second(request: Any, _query: Any) -> Any:
        tries.append(1)
        return _saved()

    wp.cmd_save_draft()
    offer = wp_dialogs.asked("confirm")[0]
    assert "did not reach Community Radio" in offer["message"]
    assert offer["yes_label"] == "Try Again"
    assert wp.host.current_path().exists()  # the draft is kept
    # The Try Again above failed the same way; now the site answers.
    wp_site.on("POST", f"{API}/pages", second)
    wp.cmd_save_draft()
    assert tries == [1]
    assert wp.host.announced[-1] == "Draft saved to Community Radio. It is not public."


def test_declining_try_again_keeps_the_draft_and_sends_nothing(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("POST", f"{API}/pages", URLError("timed out"))
    wp_site.on("GET", f"{API}/pages", [])
    wp.cmd_save_draft()
    assert len(wp_site.sent("POST", f"{API}/pages")) == 1
    assert _queue(wp) == []


def test_an_unconfirmed_update_that_landed_is_recorded(wp, wp_site, wp_dialogs) -> None:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id="x",
        remote_id=41,
        title="Hours",
        text="<p>Hi</p>",
        text_format="html",
        base_modified_gmt="2026-11-04T10:00:00",
        status="draft",
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    reads = iter([
        _saved(modified_gmt="2026-11-04T10:00:00"),  # conflict check
        _saved(modified_gmt="2026-11-04T10:00:00"),  # site copy before update
        _saved(),  # the re-read: it has our text, changed just now
    ])
    wp_site.on("GET", f"{API}/pages/41", lambda _r, _q: next(reads))
    wp_site.on("POST", f"{API}/pages/41", URLError("timed out"))
    wp.cmd_save_draft()
    assert wp_dialogs.asked("confirm") == []
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.base_modified_gmt == "2099-01-01T00:00:00"


def test_a_refusal_is_spoken_not_queued(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp.cmd_save_draft()  # 404 on POST pages: a refusal, not a lost connection
    assert _queue(wp) == []
    assert wp_site.sent("GET", f"{API}/pages") == []  # no re-read for a refusal


# --------------------------------------------------------------------------- #
# the offline queue


def test_an_unreachable_site_queues_the_send(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    _offline(wp_site)
    wp.cmd_save_draft()
    assert [e.title for e in _queue(wp)] == ["Hours"]
    assert wp.host.announced[-1] == (
        "Community Radio cannot be reached, so 'Hours' is queued. QUILL sends it when the "
        "site answers again; your copy is kept on this computer."
    )


def test_the_queue_starts_the_timer(wp, wp_site, wp_dialogs) -> None:
    started: list[float] = []
    wp.host.start_repeating = lambda seconds, _callback: started.append(seconds) or (lambda: None)
    _offline(wp_site)
    _new_page(wp, wp_dialogs)
    wp.cmd_save_draft()
    assert started == [120]


def test_back_online_sends_the_queue_and_says_so(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    _offline(wp_site)
    wp.cmd_save_draft()
    wp.retry_queue()  # still offline: stays queued, silent
    assert len(_queue(wp)) == 1
    before = len(wp.host.announced)
    wp_site.routes.clear()
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("GET", f"{API}/pages", [])  # it never landed
    wp_site.on("POST", f"{API}/pages", _saved())
    wp.tick()
    assert len(wp.host.announced) == before + 1
    assert wp.host.announced[-1] == "Back online: 1 draft sent to Community Radio."
    assert _queue(wp) == []
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.remote_id == 41 and copy.status == "draft"


def test_a_queued_new_item_that_landed_is_not_created_twice(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    _offline(wp_site)
    wp.cmd_save_draft()
    wp_site.routes.clear()
    wp_site.on("GET", f"{API}/pages", [_saved()])
    wp.retry_queue()
    assert wp.host.announced[-1] == "Back online: 1 draft sent to Community Radio."
    assert wp_site.sent("POST", f"{API}/pages") == []  # found on the site: never created
    assert wp.local.copy_for_path(wp.host.current_path()).remote_id == 41


def test_a_queued_publish_runs_the_conflict_check(wp, wp_site, wp_dialogs) -> None:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id="x",
        remote_id=41,
        title="Hours",
        text="<p>Hi</p>",
        text_format="html",
        base_modified_gmt="2026-11-04T10:00:00",
        status="publish",
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.queue_send(copy, wp.profile, True, "")
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("GET", f"{API}/pages/41", _saved("publish", modified_gmt="2026-11-04T12:00:00"))
    wp.retry_queue()
    assert wp_site.sent("POST", f"{API}/pages/41") == []
    assert "was waiting to go to Community Radio" in wp.host.announced[-1]
    assert "Nothing was sent" in wp.host.announced[-1]
    assert _queue(wp) == []


def test_a_queued_publish_with_no_conflict_publishes(wp, wp_site, wp_dialogs) -> None:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id="x",
        remote_id=41,
        title="Hours",
        text="<p>Hi</p>",
        text_format="html",
        base_modified_gmt="2026-11-04T10:00:00",
        status="draft",
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.queue_send(copy, wp.profile, True, "")
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("GET", f"{API}/pages/41", _saved(modified_gmt="2026-11-04T10:00:00"))
    wp_site.on("POST", f"{API}/pages/41", _saved("publish"))
    wp.retry_queue()
    assert wp_site.body(wp_site.sent("POST", f"{API}/pages/41")[0])["status"] == "publish"
    assert wp.host.announced[-1] == "Back online: 1 item published on Community Radio."


def test_a_queued_send_the_site_refuses_is_dropped_and_spoken(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    _offline(wp_site)
    wp.cmd_save_draft()
    wp_site.routes.clear()
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("GET", f"{API}/pages", [])
    wp.retry_queue()  # POST pages has no route: refused
    assert _queue(wp) == []
    assert "could not be sent to Community Radio from the queue" in wp.host.announced[-1]
    assert "still on this computer" in wp.host.announced[-1]


def test_a_queued_send_for_a_removed_site_is_dropped(wp, wp_site, wp_dialogs) -> None:
    from quill.core.wordpress import sites as st

    _new_page(wp, wp_dialogs)
    _offline(wp_site)
    wp.cmd_save_draft()
    wp.save_sites(st.SiteStore())
    wp.retry_queue()
    assert _queue(wp) == []
    assert "no longer connected" in wp.host.announced[-1]


def test_a_queued_copy_that_was_deleted_is_dropped_quietly(wp, wp_site, wp_dialogs) -> None:
    wp.offline_queue().add(key="radio/page-gone", site_id="radio", title="Gone", publish=False)
    wp.retry_queue()
    assert _queue(wp) == []
    assert wp.host.announced == []


def test_a_manual_send_that_works_empties_the_queue(wp, wp_site, wp_dialogs) -> None:
    _new_page(wp, wp_dialogs)
    _offline(wp_site)
    wp.cmd_save_draft()
    wp_site.routes.clear()
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("GET", f"{API}/pages", [])
    wp_site.on("POST", f"{API}/pages", _saved())
    wp.cmd_save_draft()
    assert _queue(wp) == []
