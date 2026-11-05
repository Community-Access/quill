"""9.16, behaviourally: Send This Document, Publish to Another Site, Duplicate,
Download My Writing, Send a Folder as Drafts, Coming Up, What Changed."""

from __future__ import annotations

import pytest

from quill.core.wordpress import sites as st
from quill.ui import wordpress_route_dialogs as rdlg
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
ROUTES = {"/wp/v2/posts": {}, "/wp/v2/pages": {}, "/wp/v2/media": {}}


class Routes(WordPressCommands, WordPressRouteCommands):
    pass


@pytest.fixture
def wpr(wp):
    commands = Routes(wp.host, data_dir=wp._data_dir, opener=wp._opener)
    commands.profile = wp.profile
    return commands


def site(wp_site, routes=None):
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": routes or ROUTES})
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    return wp_site


def second_site(wpr):
    """A second connected site, Choir, on choir.example."""
    store = wpr.sites()
    store.upsert(
        st.SiteProfile(
            id="choir",
            name="Choir",
            site_url="https://choir.example",
            username="jeff",
            role="Editor",
            announce_waiting_comments=False,
        )
    )
    wpr.save_sites(store)


def saved(item_id=41, kind="post", title="Hello"):
    def answer(request, _query):
        import json

        sent = json.loads(request.data or b"{}")
        return {
            "id": item_id,
            "type": kind,
            "title": {"raw": sent.get("title", title)},
            "content": {"raw": sent.get("content", "")},
            "status": sent.get("status", "draft"),
            "link": f"https://radio.example/?p={item_id}",
            "modified_gmt": "2026-11-04T10:00:00",
            "categories": sent.get("categories", []),
            "tags": sent.get("tags", []),
        }

    return answer


# --------------------------------------------------------------------------- #
# Send This Document to WordPress


def test_send_document_makes_a_draft_from_an_ordinary_file(
    wpr, wp_site, wp_dialogs, tmp_path
) -> None:
    picture = tmp_path / "logo.png"
    picture.write_bytes(b"\x89PNG")
    doc = tmp_path / "notes.md"
    doc.write_text("# Spring News\n\nWe are back.\n\n![Our logo](logo.png)\n", encoding="utf-8")
    wpr.host.open_path(doc)
    site(wp_site).on("POST", f"{API}/posts", saved())
    wp_site.on(
        "POST",
        f"{API}/media",
        {"id": 3, "source_url": "https://radio.example/wp-content/uploads/logo.png"},
    )
    wp_site.on(
        "POST",
        f"{API}/media/3",
        {
            "id": 3,
            "source_url": "https://radio.example/wp-content/uploads/logo.png",
            "alt_text": "Our logo",
        },
    )
    wp_dialogs.answer("ask_choice", 0)
    wpr.cmd_send_document()
    body = wp_site.body(wp_site.sent("POST", f"{API}/posts")[0])
    assert body["title"] == "Spring News"
    assert body["status"] == "draft"
    assert "https://radio.example/wp-content/uploads/logo.png" in body["content"]
    assert "Spring News" not in body["content"]
    assert "its 1 pictures go to the Media Library" in wpr.host.said
    assert wpr.host.announced[-1] == "Draft saved to Community Radio. It is not public."
    assert wpr.local.copy_for_path(wpr.host.current_path()).remote_id == 41


def test_send_document_refuses_a_wordpress_document_and_an_empty_one(wpr, tmp_path) -> None:
    from quill.core.wordpress import local as lc

    copy = lc.WorkingCopy(site_id="radio", kind="post", local_id="a1", title="T", text="x")
    wpr.host.open_path(wpr.local.write_document(copy))
    wpr.cmd_send_document()
    assert "already a WordPress document" in wpr.host.announced[-1]
    empty = tmp_path / "e.txt"
    empty.write_text("  ", encoding="utf-8")
    wpr.host.open_path(empty)
    wpr.cmd_send_document()
    assert wpr.host.announced[-1] == "This document is empty, so there is nothing to send."


def test_send_document_cancel_sends_nothing(wpr, wp_site, tmp_path) -> None:
    doc = tmp_path / "a.txt"
    doc.write_text("Hello", encoding="utf-8")
    wpr.host.open_path(doc)
    wpr.cmd_send_document()
    assert wp_site.requests == []


def test_send_document_to_a_site_without_posts(wpr, wp_site, wp_dialogs, tmp_path) -> None:
    doc = tmp_path / "a.txt"
    doc.write_text("Hello", encoding="utf-8")
    wpr.host.open_path(doc)
    site(wp_site, routes={"/wp/v2/media": {}})
    wp_dialogs.answer("ask_choice", 1)
    wpr.cmd_send_document()
    assert "does not offer its pages and posts" in wpr.host.announced[-1]
    assert wp_site.sent("POST", f"{API}/pages") == []


# --------------------------------------------------------------------------- #
# Publish to Another Site, and Duplicate


def open_post(wpr, text="Hello\n", categories=(5,)):
    from quill.core.wordpress import local as lc

    copy = lc.WorkingCopy(
        site_id="radio",
        kind="post",
        local_id="p1",
        remote_id=12,
        title="Newsletter",
        text=text,
        properties={"categories": list(categories), "tags": []},
        status="publish",
    )
    wpr.host.open_path(wpr.local.write_document(copy))


def choir(wp_site, categories):
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": ROUTES})
    return wp_site


def test_publish_elsewhere_with_only_one_site(wpr) -> None:
    open_post(wpr)
    wpr.cmd_publish_elsewhere()
    assert "is your only site" in wpr.host.announced[-1]


def test_publish_elsewhere_matches_terms_and_creates_missing(wpr, wp_site, wp_dialogs) -> None:
    second_site(wpr)
    open_post(wpr, "Hi\n\n![a](https://radio.example/wp-content/uploads/a.png)\n", (5, 6))
    site(wp_site)
    wp_site.on("GET", f"{API}/categories", [{"id": 5, "name": "News"}, {"id": 6, "name": "Events"}])
    wp_site.on("GET", f"{API}/tags", [])
    wp_site.on("GET", "/wp-content/uploads/a.png", b"PNGDATA")
    # The same fake answers both hosts by path; Choir's categories are only News (id 5).
    wp_site.on("POST", f"{API}/categories", {"id": 77, "name": "Events"})
    wp_site.on("POST", f"{API}/media", {"id": 8, "source_url": "https://choir.example/up/a.png"})
    wp_site.on("POST", f"{API}/posts", saved(90))
    wp_dialogs.answer("confirm", True)
    wpr.cmd_publish_elsewhere()
    body = wp_site.body(wp_site.sent("POST", f"{API}/posts")[-1])
    assert body["status"] == "draft"
    assert "https://choir.example/up/a.png" in body["content"]
    assert sorted(body["categories"]) == [5, 6]
    assert "'Newsletter' is a draft on Choir. 1 pictures were uploaded there." in wpr.host.said
    picture = wp_site.sent("GET", "/wp-content/uploads/a.png")[0]
    assert "Authorization" not in picture.headers


def test_publish_elsewhere_declining_terms_leaves_them_off(wpr, wp_site, wp_dialogs) -> None:
    second_site(wpr)
    open_post(wpr, "Hi\n", (6,))
    site(wp_site)
    calls = {"n": 0}

    def categories(_req, _query):
        calls["n"] += 1
        return [{"id": 6, "name": "Events"}] if calls["n"] == 1 else []

    wp_site.on("GET", f"{API}/categories", categories).on("GET", f"{API}/tags", [])
    wp_site.on("POST", f"{API}/posts", saved(90))
    wpr.cmd_publish_elsewhere()
    body = wp_site.body(wp_site.sent("POST", f"{API}/posts")[-1])
    assert body["categories"] == []
    assert "Left without: Events." in wpr.host.announced[-1]


def test_duplicate_on_the_same_site_opens_the_copy(wpr, wp_site, wp_dialogs) -> None:
    open_post(wpr)
    site(wp_site).on("GET", f"{API}/posts/12", saved(12, title="Newsletter"))
    wp_site.on("POST", f"{API}/posts", saved(50))
    wp_site.on("GET", f"{API}/posts/50", saved(50, title="Newsletter (copy)"))
    wpr.cmd_duplicate()
    body = wp_site.body(wp_site.sent("POST", f"{API}/posts")[0])
    assert body["title"] == "Newsletter (copy)" and body["status"] == "draft"
    assert "'Newsletter (copy)' is a new draft on Community Radio." in wpr.host.said


def test_duplicate_picks_a_post_when_none_is_open(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on(
        "GET",
        f"{API}/posts",
        [{"id": 12, "type": "post", "title": {"rendered": "Old"}, "status": "publish"}],
    )
    wp_dialogs.answer("ask_choice", 0, 0)
    wp_site.on("GET", f"{API}/posts/12", saved(12, title="Old"))
    wp_site.on("POST", f"{API}/posts", saved(51))
    wpr.cmd_duplicate()
    assert wp_site.body(wp_site.sent("POST", f"{API}/posts")[0])["title"] == "Old (copy)"


def test_duplicate_to_another_site(wpr, wp_site, wp_dialogs) -> None:
    second_site(wpr)
    open_post(wpr, categories=())
    site(wp_site).on("GET", f"{API}/posts/12", saved(12, title="Newsletter"))
    wp_site.on("POST", f"{API}/posts", saved(52))
    wp_dialogs.answer("ask_choice", 1)
    wpr.cmd_duplicate()
    assert wp_site.body(wp_site.sent("POST", f"{API}/posts")[0])["title"] == "Newsletter"
    assert "is a draft on Choir" in wpr.host.announced[-1]


def test_duplicate_cancel(wpr, wp_site) -> None:
    wpr.cmd_duplicate()
    assert wp_site.requests == []


# --------------------------------------------------------------------------- #
# Download My Writing, Send a Folder as Drafts


POST = {
    "id": 12,
    "type": "post",
    "title": {"raw": "Spring", "rendered": "Spring"},
    "content": {
        "raw": '<!-- wp:paragraph -->\n<p>Hi <img src="https://radio.example/wp-content/'
        'uploads/2026/10/a.png" alt="A"/></p>\n<!-- /wp:paragraph -->'
    },
    "status": "publish",
    "modified_gmt": "2026-10-01T00:00:00",
    "link": "https://radio.example/spring",
}


def test_download_my_writing_then_resume(wpr, wp_site, monkeypatch, tmp_path) -> None:
    out = tmp_path / "archive"
    monkeypatch.setattr(rdlg, "pick_folder", lambda *_a, **_k: out)
    site(wp_site).on("GET", f"{API}/posts", [POST]).on("GET", f"{API}/pages", [])
    wp_site.on("GET", f"{API}/posts/12", POST)
    wp_site.on("GET", "/wp-content/uploads/2026/10/a.png", b"PNG")
    wpr.cmd_download_writing()
    page = (out / "spring-12.md").read_text(encoding="utf-8")
    assert page.startswith("# Spring\n")
    assert "pictures/2026-10-a.png" in page
    assert (out / "pictures" / "2026-10-a.png").read_bytes() == b"PNG"
    assert "- [Spring](spring-12.md)" in (out / "index.md").read_text(encoding="utf-8")
    assert (
        wpr.host.announced[-1]
        == "Your writing on Community Radio is in archive: 1 saved, 1 pictures."
    )
    wpr.cmd_download_writing()
    assert "Carrying on saving" in wpr.host.said
    assert wpr.host.announced[-1] == (
        "Your writing on Community Radio is in archive: 0 saved, 1 already up to date."
    )
    assert len(wp_site.sent("GET", f"{API}/posts/12")) == 1


def test_download_my_writing_cancel(wpr, wp_site, monkeypatch) -> None:
    monkeypatch.setattr(rdlg, "pick_folder", lambda *_a, **_k: None)
    wpr.cmd_download_writing()
    assert wp_site.requests == []


def test_send_folder_confirms_the_count_then_sends(
    wpr, wp_site, wp_dialogs, monkeypatch, tmp_path
) -> None:
    (tmp_path / "one.md").write_text("# First\n\nHello.\n", encoding="utf-8")
    (tmp_path / "two.txt").write_text(
        "No heading here. [click here](https://x.org)\n", encoding="utf-8"
    )
    (tmp_path / "skip.png").write_bytes(b"x")
    monkeypatch.setattr(rdlg, "pick_folder", lambda *_a, **_k: tmp_path)
    site(wp_site).on("POST", f"{API}/posts", saved())
    wp_dialogs.answer("confirm", True)
    wpr.cmd_send_folder()
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert message.startswith("Send 2 files to Community Radio as drafts?")
    assert "found things to look at in 1 of them" in message
    titles = [wp_site.body(r)["title"] for r in wp_site.sent("POST", f"{API}/posts")]
    assert titles == ["First", "two"]
    assert wpr.host.announced[-1] == f"2 drafts from {tmp_path.name} are on Community Radio."


def test_send_folder_cancel_and_empty(wpr, wp_site, monkeypatch, tmp_path) -> None:
    (tmp_path / "one.md").write_text("Hi", encoding="utf-8")
    monkeypatch.setattr(rdlg, "pick_folder", lambda *_a, **_k: tmp_path)
    wpr.cmd_send_folder()
    assert wp_site.requests == []
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(rdlg, "pick_folder", lambda *_a, **_k: empty)
    wpr.cmd_send_folder()
    assert "has no Markdown, text or web-page files" in wpr.host.announced[-1]


# --------------------------------------------------------------------------- #
# Coming Up, What Changed on My Sites


def test_coming_up_lists_every_scheduled_item(wpr, wp_site, wp_dialogs) -> None:
    wp_site.on(
        "GET",
        f"{API}/posts",
        [
            {
                "id": 3,
                "type": "post",
                "title": {"rendered": "Gala"},
                "date_gmt": "2026-11-20T18:00:00",
            }
        ],
    ).on("GET", f"{API}/pages", [])
    wpr.cmd_coming_up()
    assert wpr.host.announced[-1].startswith("1 item is scheduled on your site. The next is Gala")
    assert wp_dialogs.window["rows"] == ["20 November 2026, 6:00 PM, Gala, post on Community Radio"]
    sent = wp_site.sent("GET", f"{API}/posts")[0]
    assert "status=future" in sent.full_url


def test_coming_up_with_nothing_scheduled(wpr, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/posts", []).on("GET", f"{API}/pages", [])
    wpr.cmd_coming_up()
    assert wpr.host.announced[-1] == "Nothing is scheduled on your site."
    assert wp_dialogs.list_windows == []


def test_what_changed_then_nothing_new(wpr, wp_site, wp_dialogs) -> None:
    from urllib.parse import parse_qs, urlparse

    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on(
        "GET",
        f"{API}/comments",
        [{"id": 1, "status": "hold"}, {"id": 2, "status": "approved"}],
    )
    wp_site.on(
        "GET",
        f"{API}/posts",
        [{"id": 4, "title": {"rendered": "Gig"}, "link": "https://radio.example/gig"}],
    )
    wp_site.on(
        "GET",
        "/wp-json/wp-site-health/v1/tests/https-status",
        {"status": "critical", "label": "No HTTPS"},
    )
    wpr.cmd_what_changed()
    rows = wp_dialogs.window["rows"]
    assert "Community Radio: 2 new comments, 1 waiting for you." in rows
    assert "Community Radio: Gig was published by someone else." in rows
    assert "Community Radio: Site Health warning: No HTTPS." in rows
    query = parse_qs(urlparse(wp_site.sent("GET", f"{API}/posts")[0].full_url).query)
    assert query["author_exclude"] == ["7"]
    wp_dialogs.press("Open in &Browser", 1)
    assert wpr.host.browsed == ["https://radio.example/gig"]
    first_since = query["after"][0]
    wpr.cmd_what_changed()
    later = parse_qs(urlparse(wp_site.sent("GET", f"{API}/posts")[-1].full_url).query)
    assert later["after"][0] >= first_since
