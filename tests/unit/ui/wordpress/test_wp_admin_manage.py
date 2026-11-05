"""Running the Site: Site Check, Site Settings, Plugins, Themes, Fonts and Synced Patterns."""

from __future__ import annotations

import json

from quill.core.wordpress import local as lc

API = "/wp-json/wp/v2"
BATCH = "/wp-json/batch/v1"

ADMIN = {
    "id": 1,
    "name": "Jeff",
    "roles": ["administrator"],
    "capabilities": {
        "manage_options": True,
        "activate_plugins": True,
        "install_plugins": True,
        "delete_plugins": True,
        "switch_themes": True,
        "edit_theme_options": True,
        "edit_posts": True,
    },
}
AUTHOR = {"id": 9, "name": "Ann", "roles": ["author"], "capabilities": {"edit_posts": True}}


# --------------------------------------------------------------------------- #
# Site Check


def test_site_check_puts_critical_first(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on(
        "GET",
        "/wp-json/",
        {
            "home": "https://radio.example",
            "timezone_string": "Europe/London",
            "namespaces": ["wp/v2", "wp-site-health/v1"],
        },
    )
    wp_site.on("GET", f"{API}/posts", [{"link": "https://radio.example/?p=4"}])
    wp_site.on("GET", f"{API}/settings", {"default_comment_status": "open", "language": "en_GB"})
    wp_site.on(
        "GET",
        "/wp-json/wp-site-health/v1/tests/background-updates",
        {"label": "Background updates are not working", "status": "critical"},
    )
    wp_site.on(
        "GET",
        "/wp-json/wp-site-health/v1/tests/https-status",
        {"label": "Your website is using an active HTTPS connection", "status": "good"},
    )
    wp.cmd_site_check()
    text = wp_dialogs.reports[-1]["text"]
    lines = text.splitlines()
    assert lines[0] == "Site Check for Community Radio: 1 critical, 1 recommended."
    assert lines[2] == "Critical: Background updates are not working."
    assert lines[3].startswith("Recommended: Permalinks: plain")
    assert "Note: WordPress version: 6.8." in text
    assert "Note: Time zone: Europe/London." in text
    assert "Note: Comments: new posts take comments." in text
    assert "Search engine visibility" in text


def test_site_check_on_a_site_without_health_routes(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", AUTHOR)
    wp_site.on("GET", "/wp-json/", {"home": "http://radio.example", "gmt_offset": 1})
    wp.cmd_site_check()
    text = wp_dialogs.reports[-1]["text"]
    assert "Critical: HTTPS: the site's address does not use HTTPS." in text
    assert "does not offer its health checks" in text
    assert "fixed offset of 1 hours" in text


# --------------------------------------------------------------------------- #
# Site Settings


def _settings(wp_site, account=ADMIN):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on(
        "GET",
        f"{API}/settings",
        {
            "title": "Community Radio",
            "description": "Your town, on air",
            "language": "en_GB",
            "show_on_front": "page",
            "page_on_front": 40,
            "posts_per_page": 10,
            "use_smilies": True,
            "site_icon": 0,
        },
    )
    wp_site.on(
        "GET",
        f"{API}/pages",
        [{"id": 40, "title": {"rendered": "Home"}}, {"id": 41, "title": {"rendered": "Blog"}}],
    )
    wp_site.on("POST", f"{API}/settings", {})


def test_settings_list_reads_values_in_words(wp, wp_site, wp_dialogs):
    _settings(wp_site)
    wp.cmd_site_settings()
    assert wp_dialogs.window["rows"] == [
        "Site title: Community Radio",
        "Tagline: Your town, on air",
        "Site language: en_GB",
        "Front page shows: A page you choose",
        "Front page: Home",
        "Posts per page: 10",
        "Turn emoticons into pictures: yes",
        "Site icon: none",
    ]


def test_settings_need_an_administrator(wp, wp_site, wp_dialogs):
    _settings(wp_site, account=AUTHOR)
    wp.cmd_site_settings()
    assert wp.host.announced == [
        "Your account on Community Radio is an Author, which cannot change site settings."
    ]


def test_changing_a_text_setting_is_confirmed_by_name(wp, wp_site, wp_dialogs):
    _settings(wp_site)
    wp.cmd_site_settings()
    wp_dialogs.answer("ask_text", "Radio for everyone")
    wp_dialogs.press("Change...", 1)  # cancelled at the confirmation
    assert wp_site.sent("POST", f"{API}/settings") == []
    assert wp_dialogs.asked("confirm")[-1]["message"] == (
        "Change tagline on Community Radio from Your town, on air to Radio for everyone?"
    )
    wp_dialogs.answer("ask_text", "Radio for everyone").answer("confirm", True)
    rows = wp_dialogs.press("Change...", 1)
    assert wp_site.body(wp_site.sent("POST", f"{API}/settings")[0]) == {
        "description": "Radio for everyone"
    }
    assert rows[1] == "Tagline: Radio for everyone"
    assert wp.host.announced[-1] == "Tagline on Community Radio is now Radio for everyone."


def test_numbers_pages_and_yes_no_settings(wp, wp_site, wp_dialogs):
    _settings(wp_site)
    wp.cmd_site_settings()
    wp_dialogs.answer("ask_text", "lots")
    assert wp_dialogs.press("Change...", 5) is None
    assert "whole number" in wp.host.announced[-1]
    wp_dialogs.answer("ask_text", "5").answer("confirm", True)
    wp_dialogs.press("Change...", 5)
    wp_dialogs.answer("ask_choice", 2).answer("confirm", True)
    wp_dialogs.press("Change...", 4)  # Front page -> Blog
    wp_dialogs.answer("ask_choice", 1).answer("confirm", True)
    wp_dialogs.press("Change...", 6)  # emoticons -> No
    bodies = [wp_site.body(r) for r in wp_site.sent("POST", f"{API}/settings")]
    assert bodies == [{"posts_per_page": 5}, {"page_on_front": 41}, {"use_smilies": False}]


def test_site_icon_must_be_square(wp, wp_site, wp_dialogs):
    _settings(wp_site)
    wp_site.on(
        "GET",
        f"{API}/media",
        [
            {
                "id": 5,
                "title": {"raw": "Banner"},
                "mime_type": "image/png",
                "source_url": "https://radio.example/b.png",
                "media_details": {"width": 1200, "height": 300},
            },
            {
                "id": 6,
                "title": {"raw": "Logo"},
                "mime_type": "image/png",
                "source_url": "https://radio.example/l.png",
                "media_details": {"width": 512, "height": 512},
            },
        ],
    )
    wp.cmd_site_settings()
    wp_dialogs.answer("ask_choice", 0)
    wp_dialogs.press("Change...", 7)
    assert "not square" in wp.host.announced[-1]
    assert wp_dialogs.asked("ask_choice")[-1]["rows"][0].endswith("not square")
    wp_dialogs.answer("ask_choice", 1).answer("confirm", True)
    wp_dialogs.press("Change...", 7)
    assert wp_site.body(wp_site.sent("POST", f"{API}/settings")[0]) == {"site_icon": 6}


# --------------------------------------------------------------------------- #
# Plugins


def _plugins(wp_site, account=ADMIN):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on(
        "GET",
        f"{API}/plugins",
        [
            {
                "plugin": "wp-accessibility/wp-accessibility",
                "name": "WP Accessibility",
                "version": "2.1",
                "status": "inactive",
                "author": "Joe",
            },
            {
                "plugin": "akismet/akismet",
                "name": "Akismet",
                "version": "5.3",
                "status": "active",
                "author": "Automattic",
            },
        ],
    )


def test_plugins_list_explains_accessibility_plugins(wp, wp_site, wp_dialogs):
    _plugins(wp_site)
    wp.cmd_plugins()
    assert wp_dialogs.window["rows"] == [
        "Akismet, version 5.3, active, by Automattic",
        "WP Accessibility, version 2.1, inactive, by Joe",
    ]
    assert "Accessibility: fixes common theme problems" in wp_dialogs.window["details"](1)


def test_activate_deactivate_install_and_delete(wp, wp_site, wp_dialogs):
    _plugins(wp_site)
    wp_site.on(
        "POST",
        f"{API}/plugins/akismet/akismet",
        {"plugin": "akismet/akismet", "name": "Akismet", "status": "inactive"},
    )
    wp_site.on(
        "POST", f"{API}/plugins", {"plugin": "hello/hello", "name": "Hello", "status": "inactive"}
    )
    wp_site.on("DELETE", f"{API}/plugins/wp-accessibility/wp-accessibility", {"deleted": True})
    wp.cmd_plugins()
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("Activate or Deactivate...", 0)
    assert "stop working" in wp_dialogs.asked("confirm")[-1]["message"]
    assert wp_site.body(wp_site.sent("POST", f"{API}/plugins/akismet/akismet")[0]) == {
        "status": "inactive"
    }
    assert wp.host.announced[-1] == "Akismet is now inactive on Community Radio."
    wp_dialogs.answer("ask_text", "https://wordpress.org/plugins/hello/").answer("confirm", True)
    wp_dialogs.press("Add Plugin...", None)
    assert wp_site.body(wp_site.sent("POST", f"{API}/plugins")[0]) == {
        "slug": "hello",
        "status": "inactive",
    }
    assert "installed on Community Radio, inactive" in wp.host.announced[-1]
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("Delete...", 1)
    assert len(wp_site.sent("DELETE", f"{API}/plugins/wp-accessibility/wp-accessibility")) == 1
    wp_dialogs.press("Open in Dashboard", None)
    assert wp.host.browsed == ["https://radio.example/wp-admin/plugins.php"]


def test_an_active_plugin_cannot_be_deleted(wp, wp_site, wp_dialogs):
    _plugins(wp_site)
    wp.cmd_plugins()
    assert wp_dialogs.press("Delete...", 0) is None
    assert "Deactivate it before deleting it" in wp.host.announced[-1]


def test_plugins_buttons_follow_capabilities(wp, wp_site, wp_dialogs):
    only_activate = {**ADMIN, "capabilities": {"activate_plugins": True}}
    _plugins(wp_site, account=only_activate)
    wp.cmd_plugins()
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert labels == ["&Activate or Deactivate...", "Open in Das&hboard"]
    assert "cannot install plugins" in wp_dialogs.window["purpose"]
    _plugins(wp_site, account=AUTHOR)
    wp.cmd_plugins()
    assert wp.host.announced[-1].endswith("which cannot manage plugins.")


# --------------------------------------------------------------------------- #
# Themes


def test_themes_list_supports_and_dashboard(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on(
        "GET",
        f"{API}/themes",
        [
            {
                "stylesheet": "old",
                "name": {"rendered": "Old"},
                "version": "1",
                "status": "inactive",
            },
            {
                "stylesheet": "tt5",
                "name": {"rendered": "Twenty Twenty-Five"},
                "version": "1.2",
                "status": "active",
                "theme_supports": {
                    "custom-logo": True,
                    "align-wide": True,
                    "post-thumbnails": False,
                },
            },
        ],
    )
    wp.cmd_themes()
    assert wp_dialogs.window["rows"][0] == "Twenty Twenty-Five, version 1.2, active"
    assert "supports: align wide, custom logo." in wp_dialogs.window["details"](0)
    wp_dialogs.press("Open in Dashboard", None)
    assert wp.host.browsed == ["https://radio.example/wp-admin/themes.php"]


def test_an_author_sees_only_the_active_theme(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", AUTHOR)
    wp_site.on("GET", f"{API}/themes", [])
    wp.cmd_themes()
    assert "status=active" in wp_site.sent("GET", f"{API}/themes")[0].full_url
    assert "cannot see every theme" in wp_dialogs.window["purpose"]


# --------------------------------------------------------------------------- #
# Fonts


def test_fonts_list_install_and_delete(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on(
        "GET",
        f"{API}/font-families",
        [
            {
                "id": 3,
                "font_family_settings": {
                    "name": "Inter",
                    "slug": "inter",
                    "fontFamily": "Inter, sans-serif",
                },
                "font_faces": [1, 2],
            }
        ],
    )
    face = {"fontFamily": "Lora", "fontWeight": "400", "src": "https://fonts.example/lora.woff2"}
    wp_site.on(
        "GET",
        f"{API}/font-collections",
        [
            {
                "name": "Google Fonts",
                "font_families": [
                    {
                        "font_family_settings": {
                            "name": "Lora",
                            "slug": "lora",
                            "fontFamily": "Lora",
                            "fontFace": [face],
                        },
                        "categories": ["serif"],
                    }
                ],
            }
        ],
    )
    wp_site.on("POST", f"{API}/font-families", {"id": 8})
    wp_site.on("POST", f"{API}/font-families/8/font-faces", {"id": 1})
    wp_site.on("DELETE", f"{API}/font-families/3", {"deleted": True})
    wp.cmd_fonts()
    assert wp_dialogs.window["rows"] == ["Inter, sans serif, suits body text and headings, 2 faces"]
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp_dialogs.press("Install...", None)
    assert wp_dialogs.asked("ask_choice")[-1]["rows"] == [
        "Lora, serif, suits body text, from Google Fonts"
    ]
    family = wp_site.body(wp_site.sent("POST", f"{API}/font-families")[0])
    assert json.loads(family["font_family_settings"]) == {
        "name": "Lora",
        "slug": "lora",
        "fontFamily": "Lora",
    }
    faces = wp_site.body(wp_site.sent("POST", f"{API}/font-families/8/font-faces")[0])
    assert json.loads(faces["font_face_settings"]) == face
    assert wp.host.announced[-1] == "Lora installed on Community Radio."
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("Delete...", 0)
    assert len(wp_site.sent("DELETE", f"{API}/font-families/3")) == 1


def test_fonts_on_an_old_site(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp.cmd_fonts()
    assert "needs WordPress 6.5" in wp.host.announced[-1]


# --------------------------------------------------------------------------- #
# Synced patterns


def _patterns(wp_site):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on(
        "GET",
        f"{API}/blocks",
        [
            {
                "id": 50,
                "title": {"raw": "Donate box"},
                "content": {"raw": "<!-- wp:paragraph --><p>Give</p><!-- /wp:paragraph -->"},
                "wp_pattern_sync_status": "",
            },
            {
                "id": 51,
                "title": {"raw": "Spare"},
                "content": {"raw": ""},
                "wp_pattern_sync_status": "unsynced",
            },
        ],
    )
    wp_site.on(
        "GET",
        f"{API}/pages",
        [
            {
                "id": 40,
                "title": {"rendered": "Home"},
                "content": {"raw": 'Hi <!-- wp:block {"ref":50} /--> bye'},
            }
        ],
    )
    wp_site.on("GET", f"{API}/posts", [])


def test_patterns_list_where_each_is_used(wp, wp_site, wp_dialogs):
    _patterns(wp_site)
    wp.cmd_synced_patterns()
    assert wp_dialogs.window["rows"] == [
        "Donate box, synced, used in 1 place",
        "Spare, not synced, not used",
    ]
    assert wp_dialogs.window["details"](0) == "Used in:\nHome (page)"


def test_edit_a_used_synced_pattern_says_how_many_change(wp, wp_site, wp_dialogs):
    _patterns(wp_site)
    wp_site.on("POST", f"{API}/blocks/50", {"id": 50})
    wp.cmd_synced_patterns()
    wp_dialogs.answer("ask_text", "<p>Give more</p>")
    wp_dialogs.press("Edit...", 0)  # cancelled at the confirmation
    assert wp_site.sent("POST", f"{API}/blocks/50") == []
    assert "all 1 pages and posts" in wp_dialogs.asked("confirm")[-1]["message"]
    wp_dialogs.answer("ask_text", "<p>Give more</p>").answer("confirm", True)
    wp_dialogs.press("Edit...", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/blocks/50")[0]) == {
        "content": "<p>Give more</p>"
    }


def test_rename_unsync_and_delete_patterns(wp, wp_site, wp_dialogs):
    _patterns(wp_site)
    wp_site.on("POST", f"{API}/blocks/50", {"id": 50})
    wp_site.on("POST", BATCH, {"responses": [{}]})
    wp_site.on("DELETE", f"{API}/blocks/51", {"deleted": True})
    wp.cmd_synced_patterns()
    wp_dialogs.answer("ask_text", "Donate")
    rows = wp_dialogs.press("Rename...", 0)
    assert rows[0].startswith("Donate, synced")
    assert wp_dialogs.press("Delete...", 0) is None
    assert "Unsync it first" in wp.host.announced[-1]
    wp_dialogs.answer("confirm", True)
    rows = wp_dialogs.press("Unsync...", 0)
    batch = wp_site.body(wp_site.sent("POST", BATCH)[0])["requests"]
    assert batch[0]["body"]["content"] == (
        "Hi <!-- wp:paragraph --><p>Give</p><!-- /wp:paragraph --> bye"
    )
    assert rows[0] == "Donate, not synced, not used"
    assert wp_dialogs.press("Unsync...", 1) is None
    assert "already not synced" in wp.host.announced[-1]
    wp_dialogs.answer("confirm", True)
    assert wp_dialogs.press("Delete...", 1) == ["Donate, not synced, not used"]


def test_new_pattern_from_the_selection(wp, wp_site, wp_dialogs):
    _patterns(wp_site)
    wp_site.on("POST", f"{API}/blocks", {"id": 60})
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="post",
        local_id="p1",
        title="T",
        text="",
        text_format="html",
        properties={},
    )
    wp.host.path = wp.local.write_document(copy)
    wp.cmd_synced_patterns()
    wp_dialogs.press("New from Selection...", None)
    assert "Select the blocks" in wp.host.announced[-1]
    wp.host.text = "<!-- wp:paragraph --><p>Listen</p><!-- /wp:paragraph -->"
    wp.host.selection = (0, len(wp.host.text))
    wp_dialogs.answer("ask_text", "Listen box")
    wp_dialogs.press("New from Selection...", None)
    body = wp_site.body(wp_site.sent("POST", f"{API}/blocks")[0])
    assert body["title"] == "Listen box" and body["content"] == wp.host.text
    assert body["wp_pattern_sync_status"] == ""
    assert wp.host.announced[-1] == "Synced pattern Listen box made on Community Radio."


def test_patterns_need_edit_posts(wp, wp_site, wp_dialogs):
    _patterns(wp_site)
    wp_site.on("GET", f"{API}/users/me", {"id": 2, "roles": ["subscriber"], "capabilities": {}})
    wp.cmd_synced_patterns()
    assert wp.host.announced[-1] == (
        "Your account on Community Radio is a Subscriber, which cannot edit patterns."
    )
