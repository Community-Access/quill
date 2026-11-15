"""wordpress.md 9.17, gap 11: the editor's WordPress commands that had only QUILL Lite's
delegation test, each now called against a fake site: Previous Versions, Move to Trash,
Compare with Site, Open by Web Address, Open Local Draft, Open on Site, Switch Site, Sites
and Connect a Site."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import sites as st

API = "/wp-json/wp/v2"
SITE_URL = "https://radio.example"


def _on_site(wp: Any, *, remote_id: int = 41, link: str = "") -> lc.WorkingCopy:
    """A working copy of page 41, open in the editor."""
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=remote_id,
        title="Our Schedule",
        text="Mine\n",
        text_format="html",
        link=link,
        status="publish",
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.host.text = "Mine\n"
    return wp.local.copy_for_path(wp.host.current_path())


def _item(content: str = "<p>Theirs</p>") -> dict[str, Any]:
    return {
        "id": 41,
        "type": "page",
        "title": {"raw": "Our Schedule"},
        "content": {"raw": content},
        "status": "publish",
        "link": f"{SITE_URL}/schedule",
        "modified_gmt": "2026-11-04T10:00:00",
    }


def _two_sites(wp: Any, data_dir: Any) -> None:
    store = wp.sites()
    store.sites.append(
        st.SiteProfile(id="news", name="Newsroom", site_url="https://news.example", username="j")
    )
    wp.save_sites(store)


def test_previous_versions_lists_the_sites_history_and_restore_puts_it_in_the_editor(
    wp: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _on_site(wp)
    wp_site.on(
        "GET",
        f"{API}/pages/41/revisions",
        [
            {
                "id": 7,
                "date_gmt": "2026-11-01T09:00:00",
                "title": {"raw": "Old"},
                "content": {"raw": "Then"},
            }
        ],
    )
    wp_site.on("GET", f"{API}/pages/41/autosaves", [])
    wp.cmd_versions()
    assert any("On the site" in row for row in wp_dialogs.window["rows"])
    wp_dialogs.press("&Restore", len(wp_dialogs.window["rows"]) - 1)
    assert wp.host.text == "Then"
    assert "Nothing was sent" in wp.host.announced[-1]
    assert wp_site.sent("POST", f"{API}/pages/41") == []


def test_move_to_trash_asks_then_marks_the_working_copy(
    wp: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _on_site(wp)
    wp.cmd_trash()
    assert wp_site.sent("DELETE", f"{API}/pages/41") == []  # the question was cancelled
    wp_site.on("DELETE", f"{API}/pages/41", {**_item(), "status": "trash"})
    wp_dialogs.answer("confirm", True)
    wp.cmd_trash()
    assert len(wp_site.sent("DELETE", f"{API}/pages/41")) == 1
    assert "moved to the Trash on Community Radio" in wp.host.announced[-1]
    assert wp.local.copy_for_path(wp.host.current_path()).status == "trash"


def test_move_to_trash_of_a_local_only_draft_sends_nothing(wp: Any, wp_site: Any) -> None:
    _on_site(wp, remote_id=0)
    wp.cmd_trash()
    assert "only on this computer" in wp.host.announced[-1]
    assert wp_site.requests == []


def test_compare_with_site_reports_both_copies(wp: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _on_site(wp)
    wp_site.on("GET", f"{API}/pages/41", _item())
    wp.cmd_compare()
    report = wp_dialogs.reports[-1]
    assert report["title"] == "Compare with Site"
    assert "Theirs" in report["text"] and "Mine" in report["text"]


def test_open_by_web_address_opens_the_working_copy_it_points_at(wp: Any, wp_site: Any) -> None:
    _on_site(wp)
    wp.host.opened.clear()
    wp.host.clipboard = f"{SITE_URL}/?page_id=41"
    wp.cmd_open_by_address()
    assert len(wp.host.opened) == 1
    assert "Opened your working copy of Our Schedule" in wp.host.announced[-1]


def test_open_by_web_address_on_an_unknown_site_offers_to_connect(
    wp: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    wp.host.clipboard = "https://elsewhere.example/hello/"
    wp.cmd_open_by_address()
    assert "not on any of your connected sites" in wp.host.announced[0]
    assert wp_dialogs.asked("ask_connect")  # Connect a Site, at that address
    assert wp_site.requests == []


def test_open_local_draft_lists_drafts_and_opens_the_chosen_one(
    wp: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    wp.cmd_open_local_draft()
    assert wp.host.announced[-1] == "You have no local WordPress drafts yet."
    _on_site(wp, remote_id=0)
    wp.host.opened.clear()
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_open_local_draft()
    assert wp_dialogs.asked("ask_choice")[0]["rows"][0].startswith(
        "Our Schedule, page, Community Radio"
    )
    assert len(wp.host.opened) == 1


def test_open_on_site_opens_the_address_or_says_it_has_none(wp: Any) -> None:
    _on_site(wp, link="")
    wp.cmd_open_on_site()
    assert "not on Community Radio yet" in wp.host.announced[-1]
    _on_site(wp, link=f"{SITE_URL}/schedule")
    wp.cmd_open_on_site()
    assert wp.host.browsed == [f"{SITE_URL}/schedule"]


def test_switch_site_with_one_site_and_with_two(wp: Any, wp_dialogs: Any, tmp_path: Any) -> None:
    wp.cmd_switch_site()
    assert wp.host.announced[-1] == "Community Radio is your only site."
    _two_sites(wp, tmp_path)
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_switch_site()
    assert wp.host.announced[-1] == "Default site: Newsroom."
    assert wp.sites().default_id == "news"


def test_sites_renames_and_makes_default(wp: Any, wp_dialogs: Any, tmp_path: Any) -> None:
    _two_sites(wp, tmp_path)
    wp.cmd_sites()
    rows = wp_dialogs.window["rows"]
    assert rows[0].endswith(", default") and "Newsroom" in rows[1]
    wp_dialogs.answer("ask_text", "Radio Two")
    wp_dialogs.press("&Rename...", 0)
    assert wp.sites().sites[0].name == "Radio Two"
    wp_dialogs.press("Make &Default", 1)
    assert wp.sites().default_id == "news"
    assert wp.host.announced[-1] == "Newsroom is now your default site."


def test_connect_a_site_asks_for_the_address_and_cancel_sends_nothing(
    wp: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    wp.cmd_connect()
    assert len(wp_dialogs.asked("ask_connect")) == 1
    assert wp_site.requests == []
