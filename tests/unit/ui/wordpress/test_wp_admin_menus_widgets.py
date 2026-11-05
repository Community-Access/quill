"""Running the Site: Menus, Navigation blocks and Widgets."""

from __future__ import annotations

API = "/wp-json/wp/v2"

ADMIN = {
    "id": 1,
    "name": "Jeff",
    "roles": ["administrator"],
    "capabilities": {"edit_theme_options": True, "manage_options": True},
}
AUTHOR = {"id": 9, "name": "Ann", "roles": ["author"], "capabilities": {"edit_posts": True}}


def _item(iid, title, obj="page", object_id=0, parent=0, order=1, kind="post_type", url=""):
    return {
        "id": iid,
        "title": {"raw": title},
        "type": kind,
        "object": obj,
        "object_id": object_id,
        "url": url,
        "parent": parent,
        "menu_order": order,
    }


def _classic(wp_site, account=ADMIN, items=None, menus=None):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on(
        "GET",
        f"{API}/menu-locations",
        {
            "primary": {"name": "primary", "description": "Header", "menu": 3},
            "footer": {"name": "footer", "description": "Footer", "menu": 0},
        },
    )
    wp_site.on(
        "GET",
        f"{API}/menus",
        menus if menus is not None else [{"id": 3, "name": "Main", "locations": ["primary"]}],
    )
    wp_site.on(
        "GET",
        f"{API}/menu-items",
        items
        if items is not None
        else [
            _item(11, "Home", object_id=40, order=1),
            _item(12, "Sessions", object_id=41, order=2),
            _item(13, "Spring", object_id=42, parent=12, order=3),
        ],
    )
    wp_site.on("GET", f"{API}/navigation", [])
    wp_site.on(
        "GET",
        f"{API}/pages",
        [
            {"id": 40, "title": {"rendered": "Home"}},
            {"id": 41, "title": {"rendered": "Sessions"}},
            {"id": 44, "title": {"rendered": "Contact"}},
        ],
    )
    wp_site.on("GET", f"{API}/posts", [{"id": 70, "title": {"rendered": "Hello"}}])
    wp_site.on("GET", f"{API}/categories", [{"id": 1, "name": "News", "slug": "news"}])


def test_menus_window_reads_the_tree(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    wp.cmd_menus()
    window = wp_dialogs.window
    assert window["title"] == "Main, Community Radio"
    assert window["rows"] == [
        "Home, page, level 1, 1 of 2",
        "Sessions, page, level 1, 2 of 2",
        "Spring, page, level 2, 1 of 1",
    ]
    assert "Goes to: page 40" in window["details"](0)
    assert "Locatio&ns..." in [a.label for a in window["actions"]]


def test_menus_need_edit_theme_options(wp, wp_site, wp_dialogs):
    _classic(wp_site, account=AUTHOR)
    wp.cmd_menus()
    assert wp_dialogs.list_windows == []
    assert wp.host.announced == [
        "Your account on Community Radio is an Author, which cannot change menus."
    ]


def test_a_site_with_no_menus_says_so(wp, wp_site, wp_dialogs):
    _classic(wp_site, menus=[])
    wp.cmd_menus()
    assert "has no menus or Navigation blocks yet" in wp.host.announced[-1]


def test_add_page_from_the_publish_flow_picks_the_menu_then_adds(wp, wp_site, wp_dialogs):
    _classic(wp_site, menus=[{"id": 3, "name": "Main"}, {"id": 4, "name": "Footer"}])
    wp_site.on("POST", f"{API}/menu-items", {"id": 99})
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_menus(page_id=44)
    assert wp_dialogs.asked("ask_choice")[0]["title"] == "Add to Menu"
    body = wp_site.body(wp_site.sent("POST", f"{API}/menu-items")[0])
    assert body["menus"] == 4 and body["object_id"] == 44 and body["title"] == "Contact"
    assert body["type"] == "post_type" and body["object"] == "page"
    assert "Contact added to Footer on Community Radio, at the end." in wp.host.said
    assert wp_dialogs.window["title"] == "Footer, Community Radio"


def test_cancelling_the_menu_choice_adds_nothing(wp, wp_site, wp_dialogs):
    _classic(wp_site, menus=[{"id": 3, "name": "Main"}, {"id": 4, "name": "Footer"}])
    wp.cmd_menus(page_id=44)
    assert wp_site.sent("POST", f"{API}/menu-items") == []
    assert wp_dialogs.list_windows == []


def test_add_page_post_category_and_link(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    wp_site.on("POST", f"{API}/menu-items", {"id": 99})
    wp.cmd_menus()
    wp_dialogs.answer("ask_choice", 2)
    rows = wp_dialogs.press("Add Page...", None)
    assert rows[-1] == "Contact, page, level 1, 3 of 3"
    wp_dialogs.answer("ask_choice", 0)
    wp_dialogs.press("Add Post...", None)
    wp_dialogs.answer("ask_choice", 0)
    wp_dialogs.press("Add Category...", None)
    bodies = [wp_site.body(r) for r in wp_site.sent("POST", f"{API}/menu-items")]
    assert bodies[1]["object"] == "post"
    assert bodies[2]["type"] == "taxonomy" and bodies[2]["object"] == "category"
    wp_dialogs.answer("ask_text", "https://example.org/donate", "Donate")
    wp_dialogs.press("Add Link...", None)
    link = wp_site.body(wp_site.sent("POST", f"{API}/menu-items")[-1])
    assert link["type"] == "custom" and link["url"] == "https://example.org/donate"
    assert wp.host.announced[-1] == "Donate added to Main, at the end."


def test_a_link_with_no_name_is_refused(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    wp.cmd_menus()
    wp_dialogs.answer("ask_text", "https://example.org", "  ")
    assert wp_dialogs.press("Add Link...", None) is None
    assert "needs a name" in wp.host.announced[-1]


def test_rename_sends_the_title(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    wp_site.on("POST", f"{API}/menu-items/12", {"id": 12})
    wp.cmd_menus()
    wp_dialogs.answer("ask_text", "Our Sessions")
    rows = wp_dialogs.press("Rename...", 1)
    assert wp_site.body(wp_site.sent("POST", f"{API}/menu-items/12")[0]) == {
        "title": "Our Sessions"
    }
    assert rows[1].startswith("Our Sessions")


def test_move_in_and_out_renumber_only_what_changed(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    for iid in (11, 12, 13):
        wp_site.on("POST", f"{API}/menu-items/{iid}", {"id": iid})
    wp.cmd_menus()
    rows = wp_dialogs.press("Move In", 1)  # Sessions under Home
    assert rows[1] == "Sessions, page, level 2, 1 of 1"
    sent = [
        (r.full_url.rsplit("/", 1)[-1], wp_site.body(r))
        for r in wp_site.requests
        if r.get_method() == "POST"
    ]
    assert sent == [("12", {"parent": 11, "menu_order": 2})]
    assert wp.host.announced[-1] == "Sessions is now under Home."
    wp_dialogs.press("Move Out", 1)
    assert wp.host.announced[-1] == "Sessions moved out, after Home."


def test_a_move_that_cannot_happen_says_so(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    wp.cmd_menus()
    assert wp_dialogs.press("Move Up", 0) is None
    assert wp.host.announced[-1] == "Home cannot move that way."


def test_move_down_and_up(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    for iid in (11, 12, 13):
        wp_site.on("POST", f"{API}/menu-items/{iid}", {"id": iid})
    wp.cmd_menus()
    rows = wp_dialogs.press("Move Down", 0)
    assert rows[0].startswith("Sessions") and rows[2].startswith("Home")
    rows = wp_dialogs.press("Move Up", 2)
    assert rows[0].startswith("Home")


def test_remove_confirms_and_lifts_children(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    wp_site.on("DELETE", f"{API}/menu-items/12", {"deleted": True})
    wp_site.on("POST", f"{API}/menu-items/13", {"id": 13})
    wp.cmd_menus()
    assert wp_dialogs.press("Remove...", 1) is None
    assert wp_site.sent("DELETE", f"{API}/menu-items/12") == []
    wp_dialogs.answer("confirm", True)
    rows = wp_dialogs.press("Remove...", 1)
    assert "Its 1 items move up into its place." in wp_dialogs.asked("confirm")[-1]["message"]
    assert rows == ["Home, page, level 1, 1 of 2", "Spring, page, level 1, 2 of 2"]
    assert wp_site.body(wp_site.sent("POST", f"{API}/menu-items/13")[0]) == {
        "parent": 0,
        "menu_order": 2,
    }


def test_locations_toggle(wp, wp_site, wp_dialogs):
    _classic(wp_site)
    wp_site.on("POST", f"{API}/menus/3", {"id": 3})
    wp.cmd_menus()
    wp_dialogs.answer("ask_choice", 1)
    wp_dialogs.press("Locations...", None)
    assert wp_site.body(wp_site.sent("POST", f"{API}/menus/3")[0]) == {
        "locations": ["primary", "footer"]
    }
    assert wp.host.announced[-1] == "Main now shows in Footer."
    wp_dialogs.answer("ask_choice", 0)
    wp_dialogs.press("Locations...", None)
    assert wp_site.body(wp_site.sent("POST", f"{API}/menus/3")[1]) == {"locations": ["footer"]}


def test_check_menu_finds_dead_links_and_missing_names(wp, wp_site, wp_dialogs):
    _classic(
        wp_site,
        items=[_item(11, "Home", object_id=40), _item(12, "", object_id=41, order=2)],
    )
    wp.cmd_menus()
    wp_site.on(
        "GET", f"{API}/pages", [{"id": 40, "status": "publish"}, {"id": 41, "status": "draft"}]
    )
    wp_dialogs.press("Check Menu", None)
    text = wp_dialogs.reports[-1]["text"]
    assert "An item at level 1 has no name." in text
    assert "points to a draft page: a dead link." in text


def test_check_menu_with_no_problems_says_so(wp, wp_site, wp_dialogs):
    _classic(wp_site, items=[_item(11, "Home", object_id=40)])
    wp.cmd_menus()
    wp_site.on("GET", f"{API}/pages", [{"id": 40, "status": "publish"}])
    wp_dialogs.press("Check Menu", None)
    assert wp.host.announced[-1] == "Main: every item has a name and goes somewhere."


def test_navigation_block_is_edited_as_content(wp, wp_site, wp_dialogs):
    _classic(wp_site, menus=[])
    content = (
        '<!-- wp:navigation-link {"label":"Home","type":"page","id":40,"url":"/",'
        '"kind":"post-type"} /--><!-- wp:page-list /-->'
    )
    wp_site.on(
        "GET",
        f"{API}/navigation",
        [{"id": 77, "title": {"raw": "Header navigation"}, "content": {"raw": content}}],
    )
    wp_site.on("POST", f"{API}/navigation/77", {"id": 77})
    wp.cmd_menus()
    assert wp_dialogs.window["rows"][1].startswith("Page list block, level 1")
    assert "Locatio&ns..." not in [a.label for a in wp_dialogs.window["actions"]]
    wp_dialogs.answer("ask_text", "Start")
    wp_dialogs.press("Rename...", 0)
    saved = wp_site.body(wp_site.sent("POST", f"{API}/navigation/77")[0])["content"]
    assert '"label":"Start"' in saved and "<!-- wp:page-list /-->" in saved


def test_other_menu_switches_windows(wp, wp_site, wp_dialogs):
    _classic(wp_site, menus=[{"id": 3, "name": "Main"}, {"id": 4, "name": "Footer"}])
    wp_dialogs.answer("ask_choice", 0, 0)
    wp.cmd_menus()
    assert wp_dialogs.press("Other Menu...", None) is not None
    assert wp_dialogs.window["title"] == "Footer, Community Radio"


# --------------------------------------------------------------------------- #
# Widgets


def _widgets(wp_site, account=ADMIN, sidebars=None):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on(
        "GET",
        f"{API}/sidebars",
        sidebars
        if sidebars is not None
        else [
            {"id": "sidebar-1", "name": "Sidebar", "description": "", "widgets": ["block-2"]},
            {"id": "footer-1", "name": "Footer", "description": "Bottom", "widgets": ["search-1"]},
            {"id": "wp_inactive_widgets", "name": "Inactive", "widgets": []},
        ],
    )

    def widgets(_request, query):
        if query.get("sidebar") == ["sidebar-1"]:
            return [
                {
                    "id": "block-2",
                    "id_base": "block",
                    "sidebar": "sidebar-1",
                    "instance": {
                        "raw": {"content": "<!-- wp:paragraph --><p>Hi</p><!-- /wp:paragraph -->"}
                    },
                    "rendered": "<p>Hi</p>",
                }
            ]
        return [
            {
                "id": "search-1",
                "id_base": "search",
                "sidebar": "footer-1",
                "rendered": "<form>Search</form>",
            }
        ]

    wp_site.on("GET", f"{API}/widgets", widgets)


def test_widgets_list_by_area(wp, wp_site, wp_dialogs):
    _widgets(wp_site)
    wp.cmd_widgets()
    assert wp_dialogs.window["rows"] == [
        "Sidebar: Paragraph block: Hi, 1 of 1",
        "Footer: Search widget: Search, 1 of 1",
    ]


def test_a_block_theme_has_no_widget_areas(wp, wp_site, wp_dialogs):
    _widgets(wp_site, sidebars=[])
    wp.cmd_widgets()
    assert "has no widget areas" in wp.host.announced[-1]


def test_widgets_need_edit_theme_options(wp, wp_site, wp_dialogs):
    _widgets(wp_site, account=AUTHOR)
    wp.cmd_widgets()
    assert wp.host.announced == [
        "Your account on Community Radio is an Author, which cannot change widgets."
    ]


def test_add_edit_move_and_remove_widgets(wp, wp_site, wp_dialogs):
    _widgets(wp_site)
    wp_site.on(
        "POST", f"{API}/widgets", {"id": "block-9", "id_base": "block", "sidebar": "footer-1"}
    )
    wp_site.on("POST", f"{API}/widgets/block-2", {"id": "block-2", "id_base": "block"})
    wp_site.on("DELETE", f"{API}/widgets/search-1", {"deleted": True})
    wp.cmd_widgets()
    wp_dialogs.answer("ask_choice", 1).answer("ask_text", "Listen live")
    wp_dialogs.press("Add Text...", None)
    added = wp_site.body(wp_site.sent("POST", f"{API}/widgets")[0])
    assert added["sidebar"] == "footer-1" and "Listen live" in added["instance"]["raw"]["content"]
    assert wp.host.announced[-1] == "Text widget added to Footer on Community Radio."
    # a classic widget's settings stay in the dashboard
    assert wp_dialogs.press("Edit...", 1) is None
    assert "classic widget" in wp.host.announced[-1]
    wp_dialogs.answer("ask_text", "<!-- wp:paragraph --><p>Hello</p><!-- /wp:paragraph -->")
    wp_dialogs.press("Edit...", 0)
    edited = wp_site.body(wp_site.sent("POST", f"{API}/widgets/block-2")[0])
    assert "Hello" in edited["instance"]["raw"]["content"]
    rows = wp_dialogs.press("Move to Area...", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/widgets/block-2")[1]) == {
        "sidebar": "footer-1"
    }
    assert rows[0].startswith("Footer: ")
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("Remove...", 1)
    assert len(wp_site.sent("DELETE", f"{API}/widgets/search-1")) == 1
    wp_dialogs.press("Open in Dashboard", None)
    assert wp.host.browsed == ["https://radio.example/wp-admin/widgets.php"]
