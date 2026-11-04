"""Insert > Link to a Page on This Site, and where the WordPress rows live (wordpress.md 12)."""

from __future__ import annotations

from quill.core.wordpress import local as lc
from quill.core.wordpress.menu import DOCUMENT_ONLY, PLACES, all_rows
from quill.ui.wordpress_link_commands import link_markup

API = "/wp-json/wp/v2"


def _open_document(wp, text_format="markdown"):
    copy = lc.WorkingCopy(
        site_id="radio", kind="page", local_id="a1", title="Hours", text_format=text_format
    )
    path = wp.local.write_document(copy)
    wp.host.open_path(path)
    return path


def _published(kind, rows):
    return [
        {
            "id": i,
            "type": kind,
            "title": {"rendered": t},
            "status": "publish",
            "modified_gmt": "2026-11-01T10:00:00",
            "link": f"https://radio.example/{t.lower()}/",
        }
        for i, t in rows
    ]


def test_outside_a_wordpress_document_it_says_where_it_works(wp) -> None:
    wp.cmd_insert_link()
    assert wp.host.announced == [
        "Link to a Page on This Site works in a WordPress page or post. "
        "Open one with File, WordPress."
    ]


def test_the_chosen_page_goes_in_as_a_markdown_link_named_by_its_title(
    wp, wp_site, wp_dialogs
) -> None:
    _open_document(wp)
    wp_site.on("GET", f"{API}/pages", _published("page", [(3, "About")]))
    wp_site.on("GET", f"{API}/posts", _published("post", [(9, "News")]))
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_insert_link()
    assert wp_dialogs.asked("ask_choice")[0]["rows"] == ["About, page", "News, post"]
    assert wp.host.text == "[News](https://radio.example/news/)"
    assert wp.host.announced[-1] == "Link to 'News' inserted."


def test_the_selection_becomes_the_link_text_in_html(wp, wp_site, wp_dialogs) -> None:
    _open_document(wp, "html")
    wp.host.text = "see our hours"
    wp.host.selection = (4, 13)
    wp_site.on("GET", f"{API}/pages", _published("page", [(3, "About")]))
    wp_site.on("GET", f"{API}/posts", [])
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_insert_link()
    assert wp.host.text == 'see <a href="https://radio.example/about/">our hours</a>'


def test_cancel_inserts_nothing_and_an_empty_site_says_so(wp, wp_site, wp_dialogs) -> None:
    _open_document(wp)
    wp_site.on("GET", f"{API}/pages", _published("page", [(3, "About")]))
    wp_site.on("GET", f"{API}/posts", [])
    wp.cmd_insert_link()
    assert wp.host.text == ""
    wp_site.on("GET", f"{API}/pages", [])
    wp.cmd_insert_link()
    assert wp.host.announced[-1] == "Community Radio has no published pages or posts to link to."


def test_link_markup_escapes_what_would_break_it() -> None:
    assert link_markup("a [b]", "https://x.example/a b", "markdown") == (
        r"[a \[b\]](https://x.example/a%20b)"
    )
    assert link_markup("<b>", 'https://x.example/?q="1"', "html") == (
        '<a href="https://x.example/?q=&quot;1&quot;">&lt;b&gt;</a>'
    )


def test_placement_follows_section_12() -> None:
    where = {row[2]: path for path, row in all_rows()}
    assert where["cmd_insert_block"] == "&Insert"
    assert where["cmd_block_settings"] == "F&ormat|Word&Press"
    assert where["cmd_blocks_window"] == "&View"
    assert where["cmd_next_block"] == "&Edit|WordPress"
    assert where["cmd_check_page"] == "&Tools|WordPress"
    assert where["cmd_users"] == "&Tools|WordPress|&Manage"
    assert where["cmd_publish"] == "&File|&WordPress"
    assert set(PLACES) == {"file", "edit", "view", "insert", "format", "tools"}


def test_every_command_is_placed_once_and_document_only_names_real_rows() -> None:
    handlers = [row[2] for _p, row in all_rows()]
    assert len(handlers) == len(set(handlers))
    assert DOCUMENT_ONLY <= set(handlers)


def test_enter_in_the_open_list_opens_the_row(wp, wp_site, wp_dialogs) -> None:
    wp_dialogs.answer("ask_choice", 1)  # Pages
    wp_site.on("GET", f"{API}/pages", _published("page", [(3, "About")]))
    wp.cmd_open()
    opened = []
    wp.open_item = lambda profile, kind, item_id: opened.append((kind, item_id))
    wp_dialogs.enter(0)
    assert opened == [("page", 3)]


def test_open_offers_the_sites_own_types_and_lists_them(wp, wp_site, wp_dialogs) -> None:
    wp_site.on(
        "GET",
        f"{API}/types",
        {
            "post": {"rest_base": "posts", "name": "Posts"},
            "page": {"rest_base": "pages", "name": "Pages"},
            "attachment": {"rest_base": "media", "name": "Media"},
            "wp_block": {"rest_base": "blocks", "name": "Patterns"},
            "event": {"rest_base": "events", "name": "Events", "viewable": True},
        },
    )
    wp_site.on("GET", f"{API}/events", _published("event", [(12, "Open Day")]))
    wp_dialogs.answer("ask_choice", 2)
    wp.cmd_open()
    assert wp_dialogs.asked("ask_choice")[0]["rows"] == ["Posts", "Pages", "Events"]
    assert wp_dialogs.window["list_label"] == "&Items:"
    assert wp_dialogs.window["rows"][0].startswith("Open Day")


def test_open_falls_back_to_posts_and_pages_when_types_are_refused(wp, wp_dialogs) -> None:
    wp.cmd_open()
    assert wp_dialogs.asked("ask_choice")[0]["rows"] == ["Posts", "Pages"]
