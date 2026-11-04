"""Restore from the Trash in the Open list, and "Add it to a menu?" (wordpress.md 5.6, 5.9)."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import sites as st
from quill.ui import wordpress_item_dialogs as idlg

API = "/wp-json/wp/v2"

EDITOR = {
    "id": 7,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["editor"],
    "capabilities": {"publish_posts": True, "publish_pages": True},
}

LISTED = [
    {
        "id": 5,
        "type": "page",
        "title": {"rendered": "Old Hours"},
        "status": "trash",
        "modified_gmt": "2026-11-01T10:00:00",
        "link": "https://radio.example/?page_id=5",
    },
    {
        "id": 6,
        "type": "page",
        "title": {"rendered": "Contact"},
        "status": "publish",
        "modified_gmt": "2026-11-02T10:00:00",
        "link": "https://radio.example/contact/",
    },
]


def _open_list(wp: Any, wp_site: Any, wp_dialogs: Any) -> None:
    wp_site.on("GET", f"{API}/pages", LISTED)
    wp_dialogs.answer("ask_choice", 1)  # Pages
    wp.cmd_open()


def test_restore_brings_a_trashed_item_back_as_a_draft(wp, wp_site, wp_dialogs) -> None:
    _open_list(wp, wp_site, wp_dialogs)
    wp_site.on(
        "POST",
        f"{API}/pages/5",
        {"id": 5, "type": "page", "status": "draft", "modified_gmt": "2026-11-04T10:00:00"},
    )
    wp_dialogs.press("&Restore from Trash", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/pages/5")[0]) == {"status": "draft"}
    assert wp.host.announced[-1] == (
        "'Old Hours' is back on Community Radio as a draft. Open it to publish it again."
    )


def test_restore_updates_a_local_working_copy(wp, wp_site, wp_dialogs) -> None:
    copy = lc.WorkingCopy(
        site_id="radio", kind="page", local_id="x", remote_id=5, title="Old Hours", status="trash"
    )
    wp.local.save(copy)
    _open_list(wp, wp_site, wp_dialogs)
    wp_site.on(
        "POST",
        f"{API}/pages/5",
        {"id": 5, "type": "page", "status": "draft", "modified_gmt": "2026-11-04T10:00:00"},
    )
    wp_dialogs.press("Restore from Trash", 0)
    kept = wp.local.find("radio", "page", 5)
    assert kept.status == "draft" and kept.base_modified_gmt == "2026-11-04T10:00:00"


def test_restore_on_an_item_not_in_the_trash_says_so(wp, wp_site, wp_dialogs) -> None:
    _open_list(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Restore from Trash", 1)
    assert wp.host.announced[-1] == "'Contact' is not in the Trash."
    assert wp_site.sent("POST", f"{API}/pages/6") == []


def test_restore_with_nothing_selected_does_nothing(wp, wp_site, wp_dialogs) -> None:
    _open_list(wp, wp_site, wp_dialogs)
    assert wp_dialogs.press("&Restore from Trash", None) is None
    assert wp.host.announced == []


def test_a_failed_restore_is_spoken(wp, wp_site, wp_dialogs) -> None:
    _open_list(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Restore from Trash", 0)  # no route: the site answers 404
    assert "Community Radio" in wp.host.announced[-1]


# --------------------------------------------------------------------------- #
# Add it to a menu?


def _publish_new_page(wp: Any, wp_site: Any, wp_dialogs: Any, *, kind: str = "page") -> None:
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
    if kind == "page":
        wp.cmd_new_page()
    else:
        wp_site.on("GET", f"{API}/categories", []).on("GET", f"{API}/tags", [])
        wp.cmd_new_post()
    wp.host.text = "Hi\n"
    saved = {
        "id": 41,
        "type": kind,
        "title": {"raw": "Hours"},
        "status": "publish",
        "link": "https://radio.example/hours/",
        "modified_gmt": "2026-11-04T10:00:00",
    }
    route = f"{API}/pages" if kind == "page" else f"{API}/posts"
    wp_site.on("GET", f"{API}/users/me", EDITOR).on("POST", route, saved)
    wp_dialogs.answer("confirm", True)
    wp.cmd_publish()


def _menu_offers(wp_dialogs: Any) -> list[dict[str, Any]]:
    return [a for a in wp_dialogs.asked("ask_choice") if a["title"] == "Add to a Menu"]


def test_a_new_page_offers_menus_and_yes_opens_them(wp, wp_site, wp_dialogs) -> None:
    opened: list[dict[str, Any]] = []
    wp.cmd_menus = lambda page_id=0: opened.append({"page_id": page_id})
    wp_dialogs.answer("ask_choice", 0)
    _publish_new_page(wp, wp_site, wp_dialogs)
    assert _menu_offers(wp_dialogs)[0]["prompt"] == "&Add it to a menu?"
    assert opened == [{"page_id": 41}]


def test_yes_without_a_page_parameter_still_opens_menus(wp, wp_site, wp_dialogs) -> None:
    opened: list[bool] = []
    wp.cmd_menus = lambda: opened.append(True)
    wp_dialogs.answer("ask_choice", 0)
    _publish_new_page(wp, wp_site, wp_dialogs)
    assert opened == [True]


def test_yes_without_menus_says_where_to_go(wp, wp_site, wp_dialogs, monkeypatch) -> None:
    monkeypatch.setattr(type(wp), "cmd_menus", None, raising=False)
    wp_dialogs.answer("ask_choice", 0)
    _publish_new_page(wp, wp_site, wp_dialogs)
    assert wp.host.announced[-1].startswith("Menus is not available yet.")


def test_stop_asking_turns_the_offer_off_for_that_site(wp, wp_site, wp_dialogs) -> None:
    wp_dialogs.answer("ask_choice", 2)
    _publish_new_page(wp, wp_site, wp_dialogs)
    assert st.load_sites(wp._data_dir).get("radio").ask_add_to_menu is False
    assert "will not ask again for Community Radio" in wp.host.announced[-1]
    _publish_new_page(wp, wp_site, wp_dialogs)
    assert len(_menu_offers(wp_dialogs)) == 1


def test_not_this_time_asks_again_next_time(wp, wp_site, wp_dialogs) -> None:
    wp_dialogs.answer("ask_choice", 1)
    _publish_new_page(wp, wp_site, wp_dialogs)
    _publish_new_page(wp, wp_site, wp_dialogs)  # cancelled offer: same as not this time
    assert len(_menu_offers(wp_dialogs)) == 2
    assert st.load_sites(wp._data_dir).get("radio").ask_add_to_menu is True


def test_a_post_or_an_update_is_not_offered(wp, wp_site, wp_dialogs) -> None:
    _publish_new_page(wp, wp_site, wp_dialogs, kind="post")
    assert _menu_offers(wp_dialogs) == []
    _publish_new_page(wp, wp_site, wp_dialogs)  # a page: offered once (cancelled)
    wp_site.on("GET", f"{API}/pages/41", {"id": 41, "modified_gmt": "2026-11-04T10:00:00"})
    wp_site.on(
        "POST",
        f"{API}/pages/41",
        {"id": 41, "type": "page", "status": "publish", "modified_gmt": "2026-11-04T11:00:00"},
    )
    wp_dialogs.answer("confirm", True)
    wp.cmd_publish()  # an update of a page already public
    assert len(_menu_offers(wp_dialogs)) == 1
