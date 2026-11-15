"""wordpress.md 9.17's route gaps, in the editor: Install a Missing Block (1), Navigation
autosaves in Menu History (10) and pattern categories in Insert Block (13)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui.wordpress_commands import WordPressCommands
from quill.ui.wordpress_pattern_commands import WordPressPatternCommands
from quill.ui.wordpress_route_commands import WordPressRouteCommands

API = "/wp-json/wp/v2"
ADMIN = {
    "id": 1,
    "name": "Jeff",
    "roles": ["administrator"],
    "capabilities": {
        "edit_theme_options": True,
        "edit_posts": True,
        "manage_options": True,
        "install_plugins": True,
        "activate_plugins": True,
    },
}


@pytest.fixture
def site(wp: Any) -> Any:
    if not issubclass(type(wp), WordPressPatternCommands):
        wp.__class__ = type("Wired", (type(wp), WordPressPatternCommands), {})
    return wp


@pytest.fixture(autouse=True)
def _no_block_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bdlg, "ask_fields", lambda *a, **k: None)


def _index(wp_site: Any, routes: dict[str, Any]) -> None:
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": routes})
    wp_site.on("GET", f"{API}/users/me", ADMIN)


def _page(site: Any) -> None:
    copy = lc.WorkingCopy(
        site_id="radio", kind="page", local_id=lc.new_local_id(), title="Home", text="Hello\n"
    )
    site.host.open_path(site.local.write_document(copy))


# -- gap 1: Install a Missing Block ---------------------------------------------------


def test_install_a_missing_block_previews_then_installs_and_activates(
    site: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _page(site)
    _index(wp_site, {"/wp/v2/block-directory/search": {}})
    wp_site.on(
        "GET",
        f"{API}/block-directory/search",
        [
            {
                "name": "acme/map",
                "title": "Map",
                "description": "A map of a place.",
                "id": "acme-map",
                "author": "Acme",
                "rating": 4.5,
                "active_installs": 2000,
            }
        ],
    )
    wp_site.on("POST", f"{API}/plugins", {"plugin": "acme-map/acme-map", "status": "active"})
    wp_dialogs.answer("ask_text", "map").answer("ask_choice", 0).answer("confirm", True)
    site.cmd_insert_block()
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert labels == ["&Insert", "Install a Missing B&lock..."]
    wp_dialogs.press("Install a Missing B&lock...")
    query = wp_site.sent("GET", f"{API}/block-directory/search")[0].full_url
    assert "term=map" in query
    assert wp_dialogs.asked("ask_choice")[0]["rows"] == ["Map: A map of a place."]
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert "Map (acme/map) comes in the plugin acme-map, by Acme" in message
    assert "rated 4.5 out of 5, active on 2,000 sites" in message
    assert "no rollback" in message
    body = wp_site.body(wp_site.sent("POST", f"{API}/plugins")[0])
    assert body == {"slug": "acme-map", "status": "active"}
    assert "Map is installed and active" in site.host.said


def test_declining_a_block_installs_nothing(site: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _page(site)
    _index(wp_site, {"/wp/v2/block-directory/search": {}})
    wp_site.on("GET", f"{API}/block-directory/search", [{"title": "Map", "id": "acme-map"}])
    wp_dialogs.answer("ask_text", "map").answer("ask_choice", 0)  # the confirm is cancelled
    site.cmd_insert_block()
    wp_dialogs.press("Install a Missing B&lock...")
    assert wp_site.sent("POST", f"{API}/plugins") == []


# -- gap 13: pattern categories ------------------------------------------------------


def test_insert_block_says_each_patterns_category_by_name(
    site: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _page(site)
    _index(wp_site, {})
    wp_site.on(
        "GET",
        f"{API}/block-patterns/patterns",
        [
            {
                "name": "tt5/hero",
                "title": "Hero",
                "description": "A welcome.",
                "categories": ["banner"],
                "content": "<!-- wp:paragraph --><p>Hi</p><!-- /wp:paragraph -->",
            }
        ],
    )
    wp_site.on("GET", f"{API}/block-patterns/categories", [{"name": "banner", "label": "Banners"}])
    site.cmd_insert_block()
    assert any(r.startswith("Hero") and "In Banners." in r for r in wp_dialogs.window["rows"])


# -- gap 10: Navigation autosaves ----------------------------------------------------


class Routes(WordPressCommands, WordPressRouteCommands):
    pass


@pytest.fixture
def wpr(wp: Any) -> Any:
    commands = Routes(wp.host, data_dir=wp._data_dir, opener=wp._opener)
    commands.profile = wp.profile
    return commands


def test_menu_history_lists_a_navigation_autosave_beside_its_revisions(
    wpr: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _index(wp_site, {"/wp/v2/navigation/(?P<parent>[\\d]+)/revisions": {}, "/wp/v2/navigation": {}})
    wp_site.on("GET", f"{API}/menu-locations", {})
    wp_site.on("GET", f"{API}/menus", [])
    home = '<!-- wp:navigation-link {"label":"Home","type":"custom","url":"/"} /-->'
    shows = '<!-- wp:navigation-link {"label":"Shows","type":"custom","url":"/shows"} /-->'
    wp_site.on(
        "GET", f"{API}/navigation", [{"id": 70, "title": {"raw": "Main"}, "content": {"raw": home}}]
    )
    wp_site.on("GET", f"{API}/navigation/70/revisions", [])
    wp_site.on(
        "GET",
        f"{API}/navigation/70/autosaves",
        [{"id": 8, "modified_gmt": "2026-11-01T10:00:00", "content": {"raw": home + shows}}],
    )
    wpr.cmd_menu_history()
    assert "1 items since removed" in wp_dialogs.window["rows"][0]
