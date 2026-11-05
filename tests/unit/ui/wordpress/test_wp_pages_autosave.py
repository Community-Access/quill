"""Autosaves every two minutes, and a newer autosave offered on Open (wordpress.md 9.3)."""

from __future__ import annotations

from typing import Any
from urllib.error import URLError

from quill.core.wordpress import local as lc

API = "/wp-json/wp/v2"


class Timer:
    """What ``host.start_repeating`` hands back: a callback the test fires by hand."""

    def __init__(self) -> None:
        self.started: list[float] = []
        self.callback: Any = None
        self.stopped = 0

    def start(self, seconds: float, callback: Any) -> Any:
        self.started.append(seconds)
        self.callback = callback

        def stop() -> None:
            self.stopped += 1

        return stop

    def fire(self) -> None:
        self.callback()


def _timer(wp: Any) -> Timer:
    timer = Timer()
    wp.host.start_repeating = timer.start
    return timer


def _open_copy(wp: Any, *, remote_id: int = 41) -> Any:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=remote_id,
        title="Our Schedule",
        text="<p>Hi</p>",
        text_format="html",
        status="publish",
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.watch_documents()
    return copy


def test_no_timer_on_a_host_without_one(wp) -> None:
    _open_copy(wp)  # FakeHost has no start_repeating: nothing breaks
    wp.tick()
    assert wp.host.announced == []


def test_the_timer_starts_once_every_two_minutes_and_stops(wp) -> None:
    timer = _timer(wp)
    _open_copy(wp)
    wp.watch_documents()
    assert timer.started == [120]
    wp.stop_watching()
    assert timer.stopped == 1


def test_new_page_starts_the_timer(wp, wp_dialogs) -> None:
    from quill.ui import wordpress_item_dialogs as idlg

    timer = _timer(wp)
    wp_dialogs.answer(
        "ask_new_item",
        idlg.NewItemAnswer(
            site_index=0,
            title="Hours",
            slug="hours",
            text_format="markdown",
            category_ids=[],
            tag_ids=[],
        ),
    )
    wp.cmd_new_page()
    assert timer.started == [120]


def test_an_unchanged_document_sends_no_autosave(wp, wp_site) -> None:
    timer = _timer(wp)
    _open_copy(wp)
    timer.fire()
    assert wp_site.requests == []


def test_a_changed_document_is_autosaved_to_the_site_and_locally(wp, wp_site) -> None:
    timer = _timer(wp)
    _open_copy(wp)
    wp_site.on("POST", f"{API}/pages/41/autosaves", {"id": 99})
    wp.host.text = "<p>Hi there</p>"
    timer.fire()
    sent = wp_site.sent("POST", f"{API}/pages/41/autosaves")
    assert len(sent) == 1
    assert wp_site.body(sent[0])["content"] == "<p>Hi there</p>"
    key = wp.local.copy_for_path(wp.host.current_path()).key
    assert wp.local.load(key).text == "<p>Hi there</p>"  # the local working copy
    assert wp.host.announced == []  # silent when it works
    timer.fire()  # nothing new since: nothing sent
    assert len(wp_site.sent("POST", f"{API}/pages/41/autosaves")) == 1


def test_a_local_only_draft_is_autosaved_locally_only(wp, wp_site) -> None:
    timer = _timer(wp)
    _open_copy(wp, remote_id=0)
    wp.host.text = "Draft words"
    timer.fire()
    assert wp_site.requests == []
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert wp.local.load(copy.key).text == "Draft words"


def test_only_the_first_autosave_failure_is_spoken(wp, wp_site) -> None:
    timer = _timer(wp)
    _open_copy(wp)
    wp_site.on("POST", f"{API}/pages/41/autosaves", URLError("timed out"))
    wp.host.text = "one"
    timer.fire()
    wp.host.text = "two"
    timer.fire()
    assert len(wp.host.announced) == 1
    assert "could not keep an autosave on Community Radio" in wp.host.announced[0]
    assert "kept on this computer" in wp.host.announced[0]
    wp_site.on("POST", f"{API}/pages/41/autosaves", {"id": 1})
    wp.host.text = "three"
    timer.fire()  # works again: re-armed
    wp_site.on("POST", f"{API}/pages/41/autosaves", URLError("timed out"))
    wp.host.text = "four"
    timer.fire()
    assert len(wp.host.announced) == 2


def test_an_ordinary_file_is_never_autosaved(wp, wp_site, tmp_path) -> None:
    timer = _timer(wp)
    _open_copy(wp)
    plain = tmp_path / "notes.txt"
    plain.write_text("x", encoding="utf-8")
    wp.host.open_path(plain)
    wp.host.text = "changed"
    timer.fire()
    assert wp_site.requests == []
    assert wp.host.announced == []


# --------------------------------------------------------------------------- #
# Open offers a newer autosave


def _page(**over: Any) -> dict[str, Any]:
    raw = {
        "id": 41,
        "type": "page",
        "title": {"raw": "Our Schedule"},
        "content": {"raw": "<p>Site</p>"},
        "status": "publish",
        "link": "https://radio.example/?page_id=41",
        "modified_gmt": "2026-11-01T10:00:00",
    }
    raw.update(over)
    return raw


def _autosave(content: str = "<p>Unsaved</p>", stamp: str = "2026-11-03T16:12:00") -> list[Any]:
    return [{"modified_gmt": stamp, "title": {"raw": "Our Schedule"}, "content": {"raw": content}}]


def test_open_offers_a_newer_autosave_and_opens_it(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages/41", _page())
    wp_site.on("GET", f"{API}/pages/41/autosaves", _autosave())
    wp_dialogs.answer("ask_choice", 0, 0)  # the unsaved version; then HTML
    wp.open_item(wp.profile, "page", 41)
    offer = wp_dialogs.asked("ask_choice")[0]
    assert offer["prompt"].startswith("There is an unsaved version from ")
    assert offer["prompt"].endswith("Open that &instead?")
    assert wp.host.text == "<p>Unsaved</p>"
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.base_modified_gmt == "2026-11-01T10:00:00"  # still the site's copy's stamp


def test_open_can_choose_the_site_copy_instead(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages/41", _page())
    wp_site.on("GET", f"{API}/pages/41/autosaves", _autosave())
    wp_dialogs.answer("ask_choice", 1, 0)
    wp.open_item(wp.profile, "page", 41)
    assert wp.host.text == "<p>Site</p>"


def test_cancelling_the_offer_opens_nothing(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages/41", _page())
    wp_site.on("GET", f"{API}/pages/41/autosaves", _autosave())
    wp.open_item(wp.profile, "page", 41)
    assert wp.host.opened == []


def test_no_offer_without_a_newer_autosave(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages/41", _page())
    wp_site.on("GET", f"{API}/pages/41/autosaves", _autosave(stamp="2026-10-01T00:00:00"))
    wp_dialogs.answer("ask_choice", 0)  # HTML
    wp.open_item(wp.profile, "page", 41)
    assert len(wp_dialogs.asked("ask_choice")) == 1
    assert wp.host.text == "<p>Site</p>"


def test_an_unreadable_autosave_list_never_stops_open(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages/41", _page())
    wp_site.on("GET", f"{API}/pages/41/autosaves", URLError("timed out"))
    wp_dialogs.answer("ask_choice", 0)
    wp.open_item(wp.profile, "page", 41)
    assert wp.host.text == "<p>Site</p>"
    assert wp.host.announced[-1] == "Opened Our Schedule from Community Radio."


def test_open_starts_the_timer(wp, wp_site, wp_dialogs) -> None:
    timer = _timer(wp)
    wp_site.on("GET", f"{API}/pages/41", _page())
    wp_dialogs.answer("ask_choice", 0)
    wp.open_item(wp.profile, "page", 41)
    assert timer.started == [120]
