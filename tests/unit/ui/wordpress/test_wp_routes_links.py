"""9.16, behaviourally: Hear Where a Link Goes, Fix Link Text, dead links, Insert Icon."""

from __future__ import annotations

import io
from urllib.error import HTTPError

import pytest

from quill.ui.wordpress_commands import WordPressCommands
from quill.ui.wordpress_route_commands import WordPressRouteCommands

API = "/wp-json/wp/v2"
EDITOR = {
    "id": 7,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["editor"],
    "capabilities": {"edit_posts": True, "upload_files": True, "publish_posts": True},
}
ALL_ROUTES = {
    "/wp-block-editor/v1/url-details": {},
    "/wp/v2/icons": {},
    "/wp/v2/posts": {},
    "/wp/v2/pages": {},
    "/wp/v2/media": {},
}


class Routes(WordPressCommands, WordPressRouteCommands):
    pass


@pytest.fixture
def wpr(wp):
    commands = Routes(wp.host, data_dir=wp._data_dir, opener=wp._opener)
    commands.profile = wp.profile
    return commands


def site(wp_site, routes=None, account=None):
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": routes or ALL_ROUTES})
    wp_site.on("GET", f"{API}/users/me", account or EDITOR)
    return wp_site


def gone(code="no_response", status=404):
    body = ('{"code":"' + code + '","message":"URL not found."}').encode()
    return HTTPError("u", status, "x", {}, io.BytesIO(body))


def open_doc(wpr, text, text_format="markdown"):
    from quill.core.wordpress import local as lc

    copy = lc.WorkingCopy(
        site_id="radio",
        kind="post",
        local_id=lc.new_local_id(),
        title="Notes",
        text=text,
        text_format=text_format,
        remote_id=5,
        status="publish",
        link="https://radio.example/notes",
    )
    wpr.host.open_path(wpr.local.write_document(copy))
    return copy


def details(title="Our Schedule", description="Every show, every week."):
    return lambda _req, query: {"title": title, "description": description}


# --------------------------------------------------------------------------- #
# Hear Where a Link Goes


def test_hear_link_outside_a_wordpress_document_says_why(wpr) -> None:
    wpr.cmd_hear_link()
    assert "works in a WordPress page or post" in wpr.host.said


def test_hear_link_reads_the_link_at_the_caret(wpr, wp_site) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", details())
    open_doc(wpr, "See [the schedule](https://radio.example/schedule) now.")
    wpr.host.caret = 8
    wpr.cmd_hear_link()
    assert wpr.host.announced[-1] == "Goes to 'Our Schedule'. Every show, every week."
    sent = wp_site.sent("GET", "/wp-json/wp-block-editor/v1/url-details")
    assert "radio.example%2Fschedule" in sent[0].full_url


def test_hear_link_says_when_the_page_is_gone(wpr, wp_site) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", gone())
    open_doc(wpr, "[x](https://radio.example/old)")
    wpr.host.caret = 1
    wpr.cmd_hear_link()
    assert "could not be reached: the page is not there." in wpr.host.announced[-1]


def test_a_site_without_the_route_is_never_asked(wpr, wp_site) -> None:
    site(wp_site, routes={"/wp/v2/posts": {}})
    open_doc(wpr, "[x](https://radio.example/a)")
    wpr.host.caret = 1
    wpr.cmd_hear_link()
    assert "cannot read where a link goes" in wpr.host.announced[-1]
    assert wp_site.sent("GET", "/wp-json/wp-block-editor/v1/url-details") == []


def test_a_subscriber_is_told_their_role_cannot(wpr, wp_site) -> None:
    site(wp_site, account=dict(EDITOR, roles=["subscriber"], capabilities={"read": True}))
    open_doc(wpr, "[x](https://radio.example/a)")
    wpr.host.caret = 1
    wpr.cmd_hear_link()
    assert "is a Subscriber, which cannot read where links go" in wpr.host.announced[-1]


def test_no_link_at_caret_asks_an_address_and_inserts_with_its_title(
    wpr, wp_site, wp_dialogs
) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", details())
    open_doc(wpr, "Hello ")
    wpr.host.caret = 6
    wp_dialogs.answer("ask_text", "https://radio.example/schedule").answer("confirm", True)
    wpr.cmd_hear_link()
    assert "[Our Schedule](https://radio.example/schedule)" in wpr.host.text
    assert wpr.host.announced[-1] == "Link to 'Our Schedule' inserted."


def test_no_link_and_cancel_asks_nothing_of_the_site(wpr, wp_site) -> None:
    site(wp_site)
    open_doc(wpr, "Hello")
    wpr.cmd_hear_link()
    assert wp_site.requests == []


def test_declining_the_insert_leaves_the_text(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", details())
    open_doc(wpr, "Hello")
    wp_dialogs.answer("ask_text", "https://radio.example/schedule")
    wpr.cmd_hear_link()
    assert wpr.host.text == "Hello"
    assert wpr.host.announced[-1].startswith("Goes to 'Our Schedule'")


def test_an_unreachable_address_is_not_offered(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", gone())
    open_doc(wpr, "Hello")
    wp_dialogs.answer("ask_text", "https://radio.example/typo")
    wpr.cmd_hear_link()
    assert not wp_dialogs.asked("confirm")


# --------------------------------------------------------------------------- #
# Fix Link Text


def test_fix_link_text_with_no_vague_links_says_so(wpr, wp_site) -> None:
    open_doc(wpr, "[Our schedule](https://radio.example/s)")
    wpr.cmd_fix_link_text()
    assert wpr.host.announced[-1] == "No 'click here' or 'read more' links in this document."
    assert wp_site.requests == []


def test_fix_link_text_uses_the_page_title(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", details())
    open_doc(wpr, "For times, [click here](https://radio.example/s).")
    wpr.cmd_fix_link_text()
    assert wp_dialogs.window["rows"] == ["'click here' goes to 'Our Schedule'"]
    rows = wp_dialogs.press("&Use the Page's Title", 0)
    assert wpr.host.text == "For times, [Our Schedule](https://radio.example/s)."
    assert rows == ["Fixed: now 'Our Schedule'"]
    assert wpr.host.announced[-1] == "The link now says 'Our Schedule'."


def test_fix_all_in_html(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", details())
    open_doc(
        wpr,
        '<p><a href="https://radio.example/a">here</a> '
        '<a href="https://radio.example/b">read more</a></p>',
        "html",
    )
    wpr.cmd_fix_link_text()
    wp_dialogs.press("Use &All Titles", None)
    assert wpr.host.text.count(">Our Schedule</a>") == 2
    assert wpr.host.announced[-1] == "2 links now say where they go."


def test_a_link_with_no_title_cannot_be_fixed(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", gone())
    open_doc(wpr, "[click here](https://radio.example/gone)")
    wpr.cmd_fix_link_text()
    wp_dialogs.press("&Use the Page's Title", 0)
    assert "click here" in wpr.host.text
    assert "write its words yourself" in wpr.host.announced[-1]


# --------------------------------------------------------------------------- #
# Dead links for Check This Page


def test_dead_links_for_lists_only_the_gone(wpr, wp_site) -> None:
    def answer(_req, query):
        return gone() if query["url"][0].endswith("old") else {"title": "Fine"}

    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", answer)
    copy = open_doc(wpr, "[a](https://radio.example/old) [b](https://radio.example/new) [c](#top)")
    dead, checked = wpr.dead_links_for(wpr.profile, wpr.api(wpr.profile), copy)
    assert checked == 2
    assert [d.url for d in dead] == ["https://radio.example/old"]


def test_dead_links_for_without_the_route_is_none(wpr, wp_site) -> None:
    site(wp_site, routes={"/wp/v2/posts": {}})
    copy = open_doc(wpr, "[a](https://radio.example/old)")
    assert wpr.dead_links_for(wpr.profile, wpr.api(wpr.profile), copy) is None
    assert wpr.dead_links_for(wpr.profile, wpr.api(wpr.profile), None) is None


def test_dead_links_refused_is_none_not_a_failure(wpr, wp_site) -> None:
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", gone("rest_forbidden", 403))
    copy = open_doc(wpr, "[a](https://radio.example/old)")
    assert wpr.dead_links_for(wpr.profile, wpr.api(wpr.profile), copy) is None


def test_check_this_page_adds_dead_links(wpr, wp_site, wp_dialogs, monkeypatch) -> None:
    from quill.core.wordpress import cdp
    from quill.core.wordpress import page_audit as pa

    monkeypatch.setattr(pa, "axe_available", lambda: True)
    monkeypatch.setattr(cdp, "find_browser", lambda: "browser")
    monkeypatch.setattr(pa, "audit_url", lambda url, **_k: pa.PageAudit(url, ()))
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/url-details", gone())
    wp_site.on("GET", f"{API}/themes", [])
    open_doc(wpr, "[a](https://radio.example/old)")
    wpr.cmd_check_page()
    assert "1 of 1 link goes nowhere" in wpr.host.said
    wp_dialogs.press("Dead &Links...", None)
    assert "1 of 1 links go nowhere" in wp_dialogs.reports[-1]["text"]


# --------------------------------------------------------------------------- #
# Insert Icon

ICONS = [
    {
        "name": "core/phone",
        "label": "Phone",
        "content": '<svg viewBox="0 0 24 24"><path d="M1"/></svg>',
    },
    {"name": "core/star", "label": "Star", "content": '<svg aria-hidden="true"><path/></svg>'},
]


def icon_site(wp_site):
    site(wp_site).on("GET", f"{API}/icons", ICONS).on(
        "GET", f"{API}/icon-collections", [{"slug": "core", "label": "WordPress"}]
    )


def test_insert_icon_with_a_label(wpr, wp_site, wp_dialogs) -> None:
    icon_site(wp_site)
    open_doc(wpr, "", "html")
    wp_dialogs.answer("ask_text", "Phone us")
    wpr.cmd_insert_icon()
    assert wp_dialogs.window["rows"] == ["Phone, WordPress", "Star, WordPress"]
    assert wp_dialogs.press("Insert with a &Label...", 0) is not None
    assert 'role="img" aria-label="Phone us"' in wpr.host.text
    assert wpr.host.announced[-1] == "Icon inserted, labelled 'Phone us'."


def test_insert_icon_decorative(wpr, wp_site, wp_dialogs) -> None:
    icon_site(wp_site)
    open_doc(wpr, "", "html")
    wpr.cmd_insert_icon()
    wp_dialogs.press("Insert as &Decorative", 1)
    assert wpr.host.text.count('aria-hidden="true"') == 1
    assert "screen readers skip it" in wpr.host.announced[-1]


def test_an_empty_label_inserts_nothing(wpr, wp_site, wp_dialogs) -> None:
    icon_site(wp_site)
    open_doc(wpr, "", "html")
    wp_dialogs.answer("ask_text", "  ")
    wpr.cmd_insert_icon()
    wp_dialogs.press("Insert with a &Label...", 0)
    assert "<svg" not in wpr.host.text
    assert "Nothing was inserted" in wpr.host.announced[-1]


def test_icon_search_narrows_the_list(wpr, wp_site, wp_dialogs) -> None:
    icon_site(wp_site)
    open_doc(wpr, "", "html")
    wpr.cmd_insert_icon()
    assert wp_dialogs.window["on_filter"]("star") == ["Star, WordPress"]


def test_a_site_with_no_icons(wpr, wp_site) -> None:
    site(wp_site).on("GET", f"{API}/icons", [])
    open_doc(wpr, "")
    wpr.cmd_insert_icon()
    assert wpr.host.announced[-1] == "Community Radio has no icons to insert."


def test_a_site_without_icons_route(wpr, wp_site) -> None:
    site(wp_site, routes={"/wp/v2/posts": {}})
    open_doc(wpr, "")
    wpr.cmd_insert_icon()
    assert "Icons arrived in WordPress 7.0" in wpr.host.announced[-1]
