"""9.16, behaviourally: large uploads, Regenerate Sizes, space, design, looks, menu history."""

from __future__ import annotations

import io
from urllib.error import HTTPError

import pytest

from quill.core.wordpress import media_pieces as mp
from quill.ui import wordpress_route_dialogs as rdlg
from quill.ui.wordpress_commands import WordPressCommands
from quill.ui.wordpress_route_commands import WordPressRouteCommands

API = "/wp-json/wp/v2"
ADMIN = {
    "id": 1,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["administrator"],
    "capabilities": {
        "manage_options": True,
        "upload_files": True,
        "edit_posts": True,
        "edit_theme_options": True,
    },
}
ROUTES = {
    "/wp/v2/media": {},
    "/wp/v2/media/(?P<id>[\\d]+)/sideload": {},
    "/wp/v2/media/(?P<id>[\\d]+)/post-process": {},
    "/wp/v2/global-styles/(?P<parent>[\\d]+)/revisions": {},
    "/wp/v2/navigation/(?P<parent>[\\d]+)/revisions": {},
    "/wp/v2/menus": {},
    "/wp/v2/navigation": {},
    "/wp-site-health/v1/directory-sizes": {},
    "/wp-block-editor/v1/export": {},
}


class Routes(WordPressCommands, WordPressRouteCommands):
    pass


@pytest.fixture
def wpr(wp):
    commands = Routes(wp.host, data_dir=wp._data_dir, opener=wp._opener)
    commands.profile = wp.profile
    return commands


def site(wp_site, routes=None, account=None):
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": routes or ROUTES})
    wp_site.on("GET", f"{API}/users/me", account or ADMIN)
    return wp_site


def media(item_id=9, **extra):
    return {
        "id": item_id,
        "title": {"raw": "Show"},
        "media_type": "file",
        "mime_type": "video/mp4",
        "source_url": "https://radio.example/wp-content/uploads/show.mp4",
        **extra,
    }


# --------------------------------------------------------------------------- #
# Upload a Large File


def test_cancelling_the_file_box_sends_nothing(wpr, wp_site, monkeypatch) -> None:
    monkeypatch.setattr(rdlg, "pick_file", lambda *_a, **_k: None)
    wpr.cmd_upload_large_file()
    assert wp_site.requests == []


def test_a_small_file_goes_in_one_upload(wpr, wp_site, monkeypatch, tmp_path) -> None:
    clip = tmp_path / "clip.mp3"
    clip.write_bytes(b"x" * 100)
    monkeypatch.setattr(rdlg, "pick_file", lambda *_a, **_k: clip)
    site(wp_site).on("POST", f"{API}/media", media())
    wpr.cmd_upload_large_file()
    assert len(wp_site.sent("POST", f"{API}/media")) == 1
    assert wpr.host.clipboard.endswith("show.mp4")
    assert "is in Community Radio's Media Library" in wpr.host.announced[-1]


def test_a_big_file_goes_whole_and_never_to_sideload(wpr, wp_site, monkeypatch, tmp_path) -> None:
    # WordPress 7.1's media/{id}/sideload takes a picture's sub-size, not a piece
    # of a file, so a big upload is one request to wp/v2/media (the live run found
    # the earlier piece upload, which no site could accept).
    monkeypatch.setattr(mp, "LARGE_FROM", 10)
    show = tmp_path / "show.mp4"
    show.write_bytes(b"0123456789abcdef")
    monkeypatch.setattr(rdlg, "pick_file", lambda *_a, **_k: show)
    site(wp_site).on("POST", f"{API}/media", media())
    wpr.cmd_upload_large_file()
    sent = wp_site.sent("POST", f"{API}/media")
    assert [p.data for p in sent] == [b"0123456789abcdef"]
    assert "Content-range" not in sent[0].headers
    assert wp_site.sent("POST", f"{API}/media/9/sideload") == []
    assert "can take a while" in wpr.host.said
    assert "Media Library" in wpr.host.announced[-1]


def test_a_file_too_big_for_the_host_says_so(wpr, wp_site, monkeypatch, tmp_path) -> None:
    show = tmp_path / "show.mp4"
    show.write_bytes(b"x" * 20)
    monkeypatch.setattr(rdlg, "pick_file", lambda *_a, **_k: show)
    refused = HTTPError(
        f"https://radio.example{API}/media",
        400,
        "Bad Request",
        {},
        io.BytesIO(
            b'{"code":"rest_upload_file_too_big","message":"Too big","data":{"status":400}}'
        ),
    )
    site(wp_site).on("POST", f"{API}/media", refused)
    wpr.cmd_upload_large_file()
    assert "bigger than" in wpr.host.said


# --------------------------------------------------------------------------- #
# Regenerate Sizes


def picture():
    return {
        "id": 4,
        "title": {"raw": "Studio"},
        "media_type": "image",
        "mime_type": "image/jpeg",
        "source_url": "https://radio.example/wp-content/uploads/studio.jpg",
        "media_details": {
            "sizes": {
                "thumbnail": {
                    "width": 150,
                    "height": 150,
                    "source_url": "https://radio.example/t.jpg",
                }
            }
        },
    }


def test_regenerate_sizes(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on("GET", f"{API}/media", [picture()])
    wp_site.on("POST", f"{API}/media/4/post-process", {"ok": True})
    wp_site.on("GET", f"{API}/media/4", picture())
    wp_dialogs.answer("ask_choice", 0)
    wpr.cmd_regenerate_sizes()
    body = wp_site.body(wp_site.sent("POST", f"{API}/media/4/post-process")[0])
    assert body == {"action": "create-image-subsizes"}
    assert wpr.host.announced[-1] == "Community Radio remade 1 sizes of Studio."


def test_regenerate_sizes_cancel_and_empty(wpr, wp_site) -> None:
    site(wp_site).on("GET", f"{API}/media", [picture()])
    wpr.cmd_regenerate_sizes()
    assert wp_site.sent("POST", f"{API}/media/4/post-process") == []
    wp_site.on("GET", f"{API}/media", [])
    wpr.cmd_regenerate_sizes()
    assert "has no pictures" in wpr.host.announced[-1]


def test_regenerate_sizes_needs_the_route(wpr, wp_site) -> None:
    site(wp_site, routes={"/wp/v2/media": {}})
    wpr.cmd_regenerate_sizes()
    assert "cannot remake a picture's sizes" in wpr.host.announced[-1]


# --------------------------------------------------------------------------- #
# Space Used, and the design


def test_space_used_in_words(wpr, wp_site, wp_dialogs) -> None:
    site(wp_site).on(
        "GET",
        "/wp-json/wp-site-health/v1/directory-sizes",
        {
            "uploads_size": {"size": "1.2 GB", "raw": 1288490189},
            "themes_size": {"size": "5 MB", "raw": 5242880},
            "plugins_size": {"size": "Unavailable", "raw": None},
            "total_size": {"size": "1.3 GB", "raw": 1293733069},
        },
    )
    wpr.cmd_site_space()
    assert wpr.host.announced[-1] == "Community Radio uses 1.2 GB altogether."
    text = wp_dialogs.reports[-1]["text"]
    assert "Uploads: 1.2 GB." in text
    assert "Themes: 5.0 MB." in text
    assert "Plugins: the site could not measure it (Unavailable)." in text


def test_space_used_needs_an_administrator(wpr, wp_site) -> None:
    site(wp_site, account=dict(ADMIN, roles=["editor"], capabilities={"edit_posts": True}))
    wpr.cmd_site_space()
    assert "is an Editor, which cannot see how much space" in wpr.host.announced[-1]


def test_download_design_saves_the_zip(wpr, wp_site, wp_response, monkeypatch, tmp_path) -> None:
    target = tmp_path / "theme.zip"
    asked = {}
    monkeypatch.setattr(rdlg, "save_as", lambda *_a, **k: asked.update(k) or target)
    site(wp_site).on(
        "GET",
        "/wp-json/wp-block-editor/v1/export",
        wp_response(
            b"PK\x03\x04zip",
            headers={"Content-Disposition": 'attachment; filename="radio-theme.zip"'},
        ),
    )
    wpr.cmd_download_design()
    assert target.read_bytes() == b"PK\x03\x04zip"
    assert asked["name"] == "radio-theme.zip"
    assert "saved as theme.zip" in wpr.host.announced[-1]
    sent = wp_site.sent("GET", "/wp-json/wp-block-editor/v1/export")[0]
    assert sent.headers["Authorization"].startswith("Basic ")


def test_download_design_cancel_and_not_a_zip(wpr, wp_site, wp_response, monkeypatch) -> None:
    monkeypatch.setattr(rdlg, "save_as", lambda *_a, **_k: None)
    site(wp_site).on("GET", "/wp-json/wp-block-editor/v1/export", wp_response(b"PKzip"))
    wpr.cmd_download_design()
    assert wpr.host.announced[-1] == "Nothing was saved."
    wp_site.on("GET", "/wp-json/wp-block-editor/v1/export", wp_response(b"<html>"))
    wpr.cmd_download_design()
    assert "did not send a zip" in wpr.host.announced[-1]


def test_download_design_without_the_route(wpr, wp_site) -> None:
    site(wp_site, routes={"/wp/v2/media": {}})
    wpr.cmd_download_design()
    assert "cannot export its design" in wpr.host.announced[-1]


# --------------------------------------------------------------------------- #
# Previous Looks

LOOK_OLD = {
    "id": 31,
    "modified_gmt": "2026-10-01T09:00:00",
    "styles": {"color": {"text": "#000"}},
    "settings": {
        "color": {"palette": {"custom": [{"name": "Ink", "slug": "ink", "color": "#111111"}]}}
    },
}


def looks_site(wp_site, revisions):
    site(wp_site).on(
        "GET",
        f"{API}/themes",
        [
            {
                "_links": {
                    "wp:user-global-styles": [
                        {"href": "https://radio.example/wp-json/wp/v2/global-styles/12"}
                    ]
                }
            }
        ],
    )
    wp_site.on("GET", f"{API}/global-styles/12/revisions", revisions)
    wp_site.on("POST", f"{API}/global-styles/12", {"id": 12})


def test_previous_looks_go_back(wpr, wp_site, wp_dialogs) -> None:
    looks_site(wp_site, [LOOK_OLD])
    wpr.cmd_previous_looks()
    assert wp_dialogs.window["rows"][0].endswith(", 1 colours")
    assert "Ink: #111111" in wp_dialogs.window["details"](0)
    wp_dialogs.press("&Palette Report...", 0)
    assert "Ink" in wp_dialogs.reports[-1]["text"]
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Go Back to This Look...", 0)
    body = wp_site.body(wp_site.sent("POST", f"{API}/global-styles/12")[0])
    assert body["styles"] == LOOK_OLD["styles"]
    assert (
        wpr.host.announced[-1] == "Community Radio has the look from 1 October 2026, 9:00 AM again."
    )


def test_previous_looks_cancel_sends_nothing(wpr, wp_site, wp_dialogs) -> None:
    looks_site(wp_site, [LOOK_OLD])
    wpr.cmd_previous_looks()
    wp_dialogs.press("&Go Back to This Look...", 0)
    assert wp_site.sent("POST", f"{API}/global-styles/12") == []


def test_previous_looks_with_none_yet(wpr, wp_site) -> None:
    looks_site(wp_site, [])
    wpr.cmd_previous_looks()
    assert wpr.host.announced[-1] == "Community Radio's styles have not been changed yet."


def test_previous_looks_with_a_classic_theme(wpr, wp_site) -> None:
    site(wp_site).on("GET", f"{API}/themes", [{"_links": {}}])
    wpr.cmd_previous_looks()
    assert "has no site styles of its own" in wpr.host.announced[-1]


# --------------------------------------------------------------------------- #
# Menu History


def nav_site(wp_site, revisions):
    site(wp_site).on("GET", f"{API}/menu-locations", {})
    wp_site.on("GET", f"{API}/menus", [])
    content = '<!-- wp:navigation-link {"label":"Home","type":"custom","url":"/"} /-->'
    wp_site.on(
        "GET",
        f"{API}/navigation",
        [{"id": 70, "title": {"raw": "Main"}, "content": {"raw": content}}],
    )
    wp_site.on("GET", f"{API}/navigation/70/revisions", revisions)
    wp_site.on("POST", f"{API}/navigation/70", {"id": 70})


OLD_NAV = (
    '<!-- wp:navigation-link {"label":"Home","type":"custom","url":"/"} /-->'
    '<!-- wp:navigation-link {"label":"Shows","type":"custom","url":"/shows"} /-->'
)


def test_menu_history_restores_a_navigation_revision(wpr, wp_site, wp_dialogs) -> None:
    nav_site(
        wp_site, [{"id": 5, "modified_gmt": "2026-10-02T10:00:00", "content": {"raw": OLD_NAV}}]
    )
    wpr.cmd_menu_history()
    assert "1 items since removed" in wp_dialogs.window["rows"][0]
    assert "Shows" in wp_dialogs.window["details"](0)
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Restore This Version...", 0)
    body = wp_site.body(wp_site.sent("POST", f"{API}/navigation/70")[0])
    assert body == {"content": OLD_NAV}
    assert "is as it was on" in wpr.host.announced[-1]


def test_menu_history_brings_back_a_removed_item(wpr, wp_site, wp_dialogs) -> None:
    nav_site(
        wp_site, [{"id": 5, "modified_gmt": "2026-10-02T10:00:00", "content": {"raw": OLD_NAV}}]
    )
    wpr.cmd_menu_history()
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Bring Back Removed Items...", 0)
    content = wp_site.body(wp_site.sent("POST", f"{API}/navigation/70")[0])["content"]
    assert '"label":"Shows"' in content
    assert wpr.host.announced[-1] == "1 items back in Main, at the end."


def test_menu_history_with_no_revisions(wpr, wp_site) -> None:
    nav_site(wp_site, [])
    wpr.cmd_menu_history()
    assert wpr.host.announced[-1] == "Main has no earlier versions on Community Radio."


def classic_site(wp_site, items):
    site(wp_site).on("GET", f"{API}/menu-locations", {})
    wp_site.on("GET", f"{API}/menus", [{"id": 3, "name": "Top"}])
    wp_site.on("GET", f"{API}/navigation", [])
    wp_site.on("GET", f"{API}/menu-items", items)


def item(item_id, title, order):
    return {
        "id": item_id,
        "title": {"raw": title},
        "type": "custom",
        "url": f"/{title.lower()}",
        "parent": 0,
        "menu_order": order,
    }


def test_classic_menu_history_from_snapshots(wpr, wp_site, wp_dialogs) -> None:
    classic_site(wp_site, [item(1, "Home", 1), item(2, "Shows", 2)])
    wpr.cmd_menu_history()  # the first look keeps a snapshot; nothing earlier yet
    assert "has no earlier versions yet" in wpr.host.announced[-1]
    classic_site(wp_site, [item(1, "Home", 1)])  # Shows was removed on the site
    wp_site.on("POST", f"{API}/menu-items", {"id": 9})
    wpr.cmd_menu_history()
    assert "1 items since removed" in wp_dialogs.window["rows"][0]
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert labels == ["&Bring Back Removed Items..."]
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Bring Back Removed Items...", 0)
    body = wp_site.body(wp_site.sent("POST", f"{API}/menu-items")[0])
    assert body["title"] == "Shows" and body["url"] == "/shows"


def test_the_menus_window_keeps_a_snapshot(wpr, wp_site, wp_dialogs) -> None:
    from quill.core.wordpress import looks_history as lh

    classic_site(wp_site, [item(1, "Home", 1)])
    wp_site.on("GET", f"{API}/pages", []).on("GET", f"{API}/posts", []).on(
        "GET", f"{API}/categories", []
    )
    wpr.cmd_menus()
    menu = type("M", (), {"id": 3})()
    assert lh.MenuSnapshots(wpr._data_dir).versions("radio", menu)[0].nodes[0][0] == "Home"


def test_menu_history_without_menus_route(wpr, wp_site) -> None:
    site(wp_site, routes={"/wp/v2/media": {}})
    wpr.cmd_menu_history()
    assert "does not offer its menus" in wpr.host.announced[-1]
