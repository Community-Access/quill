"""Running the Site: Site Map, Template Outline, Page Order and Bulk Edit."""

from __future__ import annotations

from quill.core.wordpress import local as lc

API = "/wp-json/wp/v2"
BATCH = "/wp-json/batch/v1"

ADMIN = {
    "id": 1,
    "name": "Jeff",
    "roles": ["administrator"],
    "capabilities": {
        "edit_theme_options": True,
        "edit_others_posts": True,
        "edit_others_pages": True,
    },
}
AUTHOR = {"id": 9, "name": "Ann", "roles": ["author"], "capabilities": {"edit_posts": True}}

PAGES = [
    {
        "id": 40,
        "title": {"rendered": "About"},
        "parent": 0,
        "menu_order": 0,
        "status": "publish",
        "link": "https://radio.example/about",
    },
    {
        "id": 41,
        "title": {"rendered": "Team"},
        "parent": 40,
        "menu_order": 0,
        "status": "draft",
        "link": "",
    },
    {
        "id": 42,
        "title": {"rendered": "Contact"},
        "parent": 0,
        "menu_order": 1,
        "status": "publish",
        "link": "https://radio.example/contact",
    },
]


def _site(wp_site, account=ADMIN):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on("GET", f"{API}/pages", PAGES)
    wp_site.on(
        "GET",
        f"{API}/posts",
        [
            {
                "id": 70,
                "title": {"rendered": "Hello"},
                "categories": [1],
                "link": "https://radio.example/hello",
            }
        ],
    )
    wp_site.on("GET", f"{API}/categories", [{"id": 1, "name": "News", "slug": "news"}])
    wp_site.on("GET", f"{API}/menu-locations", {})
    wp_site.on("GET", f"{API}/menus", [{"id": 3, "name": "Main"}])
    wp_site.on(
        "GET",
        f"{API}/menu-items",
        [
            {
                "id": 11,
                "title": {"raw": "About"},
                "type": "post_type",
                "object": "page",
                "object_id": 40,
                "parent": 0,
                "menu_order": 1,
            }
        ],
    )
    wp_site.on("GET", f"{API}/navigation", [])


# --------------------------------------------------------------------------- #
# Site Map


def test_site_map_is_pages_by_parent_then_posts_by_category(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp.cmd_site_map()
    assert wp_dialogs.window["rows"] == [
        "Pages, 3",
        "About, in Main, level 1",
        "Team, draft, level 2",
        "Contact, level 1",
        "Posts, 1",
        "News, 1 posts",
        "Hello, level 2",
    ]


def test_site_map_without_menu_rights_skips_menus(wp, wp_site, wp_dialogs):
    _site(wp_site, account=AUTHOR)
    wp.cmd_site_map()
    assert wp_dialogs.window["rows"][1] == "About, level 1"
    assert wp_site.sent("GET", f"{API}/menus") == []


def test_site_map_opens_items_and_refuses_headings(wp, wp_site, wp_dialogs, monkeypatch):
    _site(wp_site)
    opened = []
    monkeypatch.setattr(
        wp, "open_item", lambda profile, kind, item_id: opened.append((kind, item_id))
    )
    wp.cmd_site_map()
    assert wp_dialogs.press("Open", 0) is None
    assert "heading" in wp.host.announced[-1]
    wp_dialogs.press("Open", 6)
    assert opened == [("post", 70)]
    wp_dialogs.press("Open on Site", 3)
    assert wp.host.browsed == ["https://radio.example/contact"]


# --------------------------------------------------------------------------- #
# Template Outline


def test_template_outline_puts_the_documents_template_first(wp, wp_site, wp_dialogs, tmp_path):
    copy = lc.WorkingCopy(
        site_id="radio", kind="page", local_id="x1", title="T", text="", properties={}
    )
    wp.host.path = wp.local.write_document(copy)
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp_site.on(
        "GET",
        f"{API}/templates",
        [
            {"id": "t//index", "slug": "index", "title": {"raw": "Index"}, "content": {"raw": ""}},
            {
                "id": "t//page",
                "slug": "page",
                "title": {"raw": "Pages"},
                "content": {
                    "raw": '<!-- wp:template-part {"slug":"header"} /--><!-- wp:post-content /-->'
                },
            },
        ],
    )
    wp_site.on(
        "GET",
        f"{API}/template-parts",
        [
            {
                "id": "t//header",
                "slug": "header",
                "area": "header",
                "title": {"raw": "Header"},
                "content": {"raw": "<!-- wp:site-title /-->"},
            }
        ],
    )
    wp.cmd_template_outline()
    text = wp_dialogs.reports[-1]["text"]
    assert text.startswith("Template: Pages\n    Template part: header\n")
    assert "Template part (header): Header" in text


def test_a_classic_theme_has_no_templates(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN)
    wp.cmd_template_outline()
    assert "uses a classic theme" in wp.host.announced[-1]
    assert wp_dialogs.reports == []


# --------------------------------------------------------------------------- #
# Page Order


def test_page_order_moves_and_saves_in_one_batch(wp, wp_site, wp_dialogs, monkeypatch):
    _site(wp_site)
    wp_site.on("POST", BATCH, {"responses": [{}]})
    wp.cmd_page_order()
    assert wp_dialogs.window["rows"] == [
        "About, level 1, 1 of 2",
        "Team, draft, level 2, 1 of 1",
        "Contact, level 1, 2 of 2",
    ]
    rows = wp_dialogs.press("Move Up", 2)
    assert rows[0] == "Contact, level 1, 1 of 2"
    batch = wp_site.body(wp_site.sent("POST", BATCH)[0])["requests"]
    assert {r["path"]: r["body"] for r in batch} == {
        "/wp/v2/pages/42": {"parent": 0, "menu_order": 0},
        "/wp/v2/pages/40": {"parent": 0, "menu_order": 1},
    }
    assert wp.host.announced[-1] == "Contact moved up, 1 of 2."
    wp_dialogs.press("Move In", 1)
    assert wp.host.announced[-1] == "About is now under Contact."
    wp_dialogs.press("Move Out", 1)
    assert wp.host.announced[-1] == "About moved out, after Contact."
    wp_dialogs.press("Move Down", 0)
    assert wp.host.announced[-1] == "Contact moved down, 2 of 2."
    assert wp_dialogs.press("Move Out", 0) is None
    assert "cannot move that way" in wp.host.announced[-1]
    opened = []
    monkeypatch.setattr(wp, "open_item", lambda profile, kind, item_id: opened.append(item_id))
    wp_dialogs.press("Open", 0)
    assert opened == [40]


def test_page_order_needs_edit_others_pages(wp, wp_site, wp_dialogs):
    _site(wp_site, account=AUTHOR)
    wp.cmd_page_order()
    assert wp.host.announced == [
        "Your account on Community Radio is an Author, which cannot arrange pages."
    ]


def test_page_order_with_no_pages(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/users/me", ADMIN).on("GET", f"{API}/pages", [])
    wp.cmd_page_order()
    assert wp.host.announced == ["Community Radio has no pages yet."]


# --------------------------------------------------------------------------- #
# Bulk Edit


def _bulk_site(wp_site):
    wp_site.on("GET", f"{API}/users/me", ADMIN)

    def posts(_request, query):
        if "include" in query:
            return [{"id": 70, "status": "publish"}, {"id": 71, "status": "draft"}]
        return [
            {
                "id": 70,
                "type": "post",
                "title": {"rendered": "Hello"},
                "status": "publish",
                "modified_gmt": "2026-11-01T10:00:00",
            },
            {
                "id": 71,
                "type": "post",
                "title": {"rendered": "Again"},
                "status": "draft",
                "modified_gmt": "2026-11-02T10:00:00",
            },
        ]

    wp_site.on("GET", f"{API}/posts", posts)
    wp_site.on("GET", f"{API}/users", [{"id": 1, "name": "Jeff"}, {"id": 9, "name": "Ann"}])
    wp_site.on("GET", f"{API}/categories", [{"id": 1, "name": "News"}])
    wp_site.on("GET", f"{API}/tags", [{"id": 5, "name": "Jazz"}])
    wp_site.on("POST", BATCH, {"responses": [{}, {}]})


def test_bulk_edit_changes_selected_posts_then_undoes(wp, wp_site, wp_dialogs):
    _bulk_site(wp_site)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_bulk_edit()
    assert wp_dialogs.press("Change...", None) is None
    assert "Select the posts" in wp.host.announced[-1]
    rows = wp_dialogs.press("Select", 0)
    assert rows[0].startswith("Selected, Hello")
    rows = wp_dialogs.press("Select All", None)
    assert all(r.startswith("Selected, ") for r in rows)
    wp_dialogs.answer("ask_choice", 0, 1).answer("confirm", True)  # Status -> Draft
    wp_dialogs.press("Change...", None)
    confirm = wp_dialogs.asked("confirm")[-1]
    assert confirm["message"].startswith("Status: Draft, for 2 posts on Community Radio?")
    batch = wp_site.body(wp_site.sent("POST", BATCH)[0])["requests"]
    assert [r["body"] for r in batch] == [{"status": "draft"}, {"status": "draft"}]
    assert wp.host.announced[-1] == "2 posts changed on Community Radio."
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("Undo Bulk Edit...", None)
    undo = wp_site.body(wp_site.sent("POST", BATCH)[1])["requests"]
    assert {r["path"]: r["body"] for r in undo} == {
        "/wp/v2/posts/70": {"status": "publish"},
        "/wp/v2/posts/71": {"status": "draft"},
    }
    assert wp.host.announced[-1] == "2 items put back on Community Radio."
    wp_dialogs.press("Undo Bulk Edit...", None)
    assert wp.host.announced[-1] == "There is no bulk edit on Community Radio to undo."


def test_bulk_add_a_tag_keeps_existing_ones(wp, wp_site, wp_dialogs):
    _bulk_site(wp_site)

    def posts(_request, query):
        if "include" in query:
            return [{"id": 70, "tags": [2]}]
        return [{"id": 70, "type": "post", "title": {"rendered": "Hello"}, "status": "publish"}]

    wp_site.on("GET", f"{API}/posts", posts)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_bulk_edit()
    wp_dialogs.press("Select", 0)
    wp_dialogs.answer("ask_choice", 3, 0).answer("confirm", True)  # Add a tag -> Jazz
    wp_dialogs.press("Change...", None)
    batch = wp_site.body(wp_site.sent("POST", BATCH)[0])["requests"]
    assert batch[0]["body"] == {"tags": [2, 5]}


def test_bulk_edit_cancelled_confirmation_sends_nothing(wp, wp_site, wp_dialogs):
    _bulk_site(wp_site)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_bulk_edit()
    wp_dialogs.press("Select", 0)
    wp_dialogs.answer("ask_choice", 4, 1)  # Comments -> Closed, then cancel
    wp_dialogs.press("Change...", None)
    assert wp_site.sent("POST", BATCH) == []


def test_bulk_edit_pages_offers_parent_and_needs_rights(wp, wp_site, wp_dialogs):
    _bulk_site(wp_site)
    wp_site.on("GET", f"{API}/pages", [])
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_bulk_edit()
    assert wp_dialogs.window["title"] == "Bulk Edit Pages, Community Radio"
    wp_site.on("GET", f"{API}/users/me", AUTHOR)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_bulk_edit()
    assert "cannot edit other people's posts" in wp.host.announced[-1]


def test_bulk_edit_cancelled_kind_reads_nothing(wp, wp_site, wp_dialogs):
    wp.cmd_bulk_edit()
    assert wp_site.requests == []
