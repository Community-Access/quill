"""wordpress.md 9.18 packages 6, 7 and 14, wx-free: the Dashboard, Site Editor writing and
the map of wp-admin screens to Workbench places. Every request goes to a fake site."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import SiteInfo
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS
from quill.core.wordpress.workbench_admin_map import ADMIN_MAP, map_rows, screen_link, screens_for
from quill.core.wordpress.workbench_dashboard import (
    activity_rows,
    glance_rows,
    places,
    said_counts,
)
from quill.core.wordpress.workbench_dashboard_places import (
    CSS_ROWS,
    DASHBOARD_NODES,
    KEYLESS,
    MENU_ROWS,
    NODE_ROWS,
    SCREEN_ROWS,
    SITE_EDITOR_NODES,
    TEMPLATE_ROWS,
    WIDGET_ROWS,
)
from quill.core.wordpress.workbench_edit import EditConflict, EditRefused
from quill.core.wordpress.workbench_load import SiteContext
from quill.core.wordpress.workbench_node_help import node_help, row_help
from quill.core.wordpress.workbench_site_editor import (
    CssText,
    change_lines,
    css_problem,
    css_rows,
    load_template,
    reset_template,
    restore_template,
    save_css,
    save_template,
)
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

SITE = "Radio"
TEMPLATE = "wp/v2/templates/tt5//single"


class _Response:
    def __init__(self, total: int | None) -> None:
        self.total = total
        self.payload: list[Any] = []


class FakeSite:
    """Counts by route and status; templates, styles and themes; every write recorded."""

    def __init__(self) -> None:
        self.totals: dict[tuple[str, str], int] = {
            ("wp/v2/posts", "publish"): 12,
            ("wp/v2/posts", "draft"): 3,
            ("wp/v2/posts", "future"): 1,
            ("wp/v2/pages", "publish"): 4,
            ("wp/v2/comments", "hold"): 2,
            ("wp/v2/comments", "approve"): 30,
            ("wp/v2/users", ""): 5,
            ("wc/v3/orders", "processing"): 1,
            ("wc/v3/orders", "on-hold"): 0,
            ("wc/v3/products", "publish"): 40,
        }
        self.refuse: set[str] = set()
        self.template: dict[str, Any] = {
            "id": "tt5//single",
            "slug": "single",
            "type": "wp_template",
            "title": {"rendered": "Single Posts"},
            "content": {"raw": "<!-- wp:post-title /-->"},
            "source": "custom",
            "has_theme_file": True,
        }
        self.styles: dict[str, Any] = {"color": {"text": "#111"}, "css": "a { color: red; }"}
        self.block_theme = True
        self.writes: list[tuple[str, str, Any]] = []
        self.missing: set[str] = set()

    def request(self, method: str, route: str, *, params: Any = None, **_kw: Any) -> _Response:
        if route in self.refuse:
            raise WordPressApiError("Sorry, you are not allowed.", status=403)
        status = str((params or {}).get("status", ""))
        return _Response(self.totals.get((route, status), 0))

    def get(self, route: str, **params: Any) -> Any:
        if route in self.refuse:
            raise WordPressApiError("Sorry, you are not allowed.", status=403)
        if route == "wp/v2/themes":
            links = {"wp:user-global-styles": [{"href": "https://r.example/wp/v2/global-styles/9"}]}
            return [
                {
                    "name": {"raw": "Twenty Twenty-Five"},
                    "stylesheet": "tt5",
                    "version": "1.2",
                    "is_block_theme": self.block_theme,
                    "_links": links if self.block_theme else {},
                }
            ]
        if route == "tribe/events/v1/events":
            return {"events": [], "total": 3}
        if route == "yoast/v1/seo_scores":
            return {
                "scores": [
                    {"name": "good", "amount": 4},
                    {"name": "needs_improvement", "amount": 2},
                ]
            }
        if route == "yoast/v1/readability_scores":
            return {"scores": []}
        if route == "wp/v2/posts":
            if params.get("status") == "future":
                return [
                    {
                        "id": 5,
                        "title": {"rendered": "Next Show"},
                        "status": "future",
                        "date_gmt": "2026-12-01T10:00:00",
                    }
                ]
            return []
        if route == "wp/v2/comments":
            return []
        if route == TEMPLATE:
            if params.get("source") == "theme":
                return {**self.template, "content": {"raw": "<!-- wp:post-content /-->"}}
            return dict(self.template)
        if route == "wp/v2/global-styles/9":
            return {"id": 9, "styles": dict(self.styles)}
        return []

    def post(self, route: str, body: Any = None, **_params: Any) -> Any:
        if route in self.missing:
            raise WordPressApiError("No route was found.", status=404)
        self.writes.append(("POST", route, body))
        if route == TEMPLATE:
            self.template["content"] = {"raw": body["content"]}
            return dict(self.template)
        if route == "wp/v2/global-styles/9":
            self.styles = dict(body["styles"])
        return {**(body or {}), "id": "tt5//single"}

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        return {}


def _ctx(api: FakeSite, namespaces: tuple[str, ...] = ("wp/v2",)) -> SiteContext:
    info = SiteInfo(SITE, "", "https://r.example", "6.8", namespaces, "")
    return SiteContext(SITE, api, url="https://r.example", info=info)  # type: ignore[arg-type]


# -- package 6: the Dashboard ---------------------------------------------------------


def test_at_a_glance_says_counts_in_words_and_each_plugin_present() -> None:
    api = FakeSite()
    rows = glance_rows(_ctx(api, ("wp/v2", "wc/v3", "tribe/events/v1", "yoast/v1")))
    said = {r.cell("fact"): r.cell("value") for r in rows}
    assert said["Posts"] == "12 published, 3 drafts, 1 scheduled"
    assert said["Pages"] == "4 published"
    assert said["Comments"] == "2 waiting, 30 approved"
    assert said["People"] == "5 on the site"
    assert said["WordPress"] == "6.8"
    assert said["Theme"] == "Twenty Twenty-Five, version 1.2"
    assert said["WooCommerce"] == "1 order to fulfil, 0 on hold, 40 products published"
    assert said["The Events Calendar"] == "3 upcoming events"
    assert said["Yoast SEO"] == "SEO scores on posts: 4 good, 2 needs improvement"
    assert "Paid Memberships Pro" not in said  # its namespace is not offered


def test_a_refused_count_is_left_out_not_said_as_none() -> None:
    api = FakeSite()
    api.refuse = {"wp/v2/comments", "wp/v2/users"}
    said = {r.cell("fact"): r.cell("value") for r in glance_rows(_ctx(api))}
    assert said["Comments"] == "this account may not count them"
    assert "People" not in said
    assert said_counts({"publish": 0, "draft": 0}, (("publish", "a", "b"),)) == "none"


def test_activity_says_every_group_even_when_empty() -> None:
    rows = activity_rows(_ctx(FakeSite()))
    groups = [(r.cell("group"), r.kind, r.title) for r in rows]
    assert groups == [
        ("Publishing soon", "item", "Next Show"),
        ("Recently published", "fact", "nothing published yet"),
        ("Recent comments", "fact", "no comments yet"),
    ]
    assert rows[0].detail.startswith("Publishing soon: Next Show")


# -- package 14: wp-admin's screens --------------------------------------------------


def test_every_screen_maps_to_a_real_site_node_and_says_why() -> None:
    site_nodes = {n.key for n in WORDPRESS_TREE.template("site")}
    keys = [s.key for s in ADMIN_MAP]
    assert len(keys) == len(set(keys))
    for screen in ADMIN_MAP:
        assert screen.node in site_nodes, screen.key
        assert screen.says and screen.path.startswith("wp-admin/"), screen.key
    named = {s.name for s in ADMIN_MAP}
    for wanted in (
        "Dashboard > Updates",
        "Tools > Import",
        "Tools > Export",
        "Tools > Export Personal Data",
        "Tools > Erase Personal Data",
        "Tools > Site Health > Info",
        "Settings > Permalinks",
        "Settings > Discussion",
        "Settings > Media",
        "Settings > Privacy",
        "Appearance > Themes",
        "Appearance > Customize",
        "Tools > Theme File Editor",
        "WooCommerce > Status > Scheduled Actions",
        "Network Admin",
    ):
        assert wanted in named, wanted


def test_map_rows_keep_plugin_screens_to_sites_that_have_them() -> None:
    rows = map_rows(SITE, "https://r.example/", ("wp/v2",), places())
    keys = {r.key for r in rows}
    assert "permalinks" in keys and "wc_status" not in keys
    permalinks = next(r for r in rows if r.key == "permalinks")
    assert permalinks.link == "https://r.example/wp-admin/options-permalink.php"
    assert permalinks.cell("place") == "Settings"
    assert permalinks.cell("reach") == "Only in wp-admin"
    shop = map_rows(SITE, "https://r.example", ("wc/v3",), places())
    assert "wc_status" in {r.key for r in shop}


def test_screens_for_a_status_child_borrow_its_parents() -> None:
    assert [s.key for s in screens_for("posts_drafts")] == [s.key for s in screens_for("posts")]
    assert "permalinks" in {s.key for s in screens_for("settings")}
    assert screens_for("shop") == []  # WooCommerce not offered
    assert screen_link("", ADMIN_MAP[0]) == ""


# -- package 7: templates and Additional CSS -----------------------------------------


def test_save_template_checks_for_a_conflict_then_sends_the_markup() -> None:
    api = FakeSite()
    loaded = load_template(api, TEMPLATE)  # type: ignore[arg-type]
    assert loaded.title == "Single Posts" and loaded.customized and loaded.has_theme_file
    saved = save_template(api, loaded, "<!-- wp:post-content /-->")  # type: ignore[arg-type]
    assert api.writes == [("POST", TEMPLATE, {"content": "<!-- wp:post-content /-->"})]
    assert saved.content == "<!-- wp:post-content /-->"
    with pytest.raises(EditConflict):  # the site changed since `loaded` was read
        save_template(api, loaded, "<!-- wp:group /-->")  # type: ignore[arg-type]
    assert len(api.writes) == 1


def test_reset_deletes_the_custom_copy_and_restore_recreates_a_lost_one() -> None:
    api = FakeSite()
    loaded = load_template(api, TEMPLATE)  # type: ignore[arg-type]
    reset_template(api, loaded)  # type: ignore[arg-type]
    assert api.writes[-1] == ("DELETE", TEMPLATE, {"force": True})
    api.missing = {TEMPLATE}
    restore_template(api, loaded, loaded.content)  # type: ignore[arg-type]
    assert api.writes[-1] == (
        "POST",
        "wp/v2/templates",
        {"slug": "single", "title": "Single Posts", "content": "<!-- wp:post-title /-->"},
    )
    api.template["source"] = "theme"
    with pytest.raises(EditRefused):
        reset_template(api, load_template(api, TEMPLATE))  # type: ignore[arg-type]


def test_change_lines_read_a_change_in_words() -> None:
    assert change_lines("a\nb", "a\nc") == ["Line 2 removed: b", "Line 2 added: c"]
    assert change_lines("same", "same") == ["No line changes."]
    many = change_lines("", "\n".join(str(n) for n in range(50)), limit=3)
    assert many[-1] == "And 47 more line changes."


def test_css_is_checked_saved_with_every_other_style_and_conflicts_refused() -> None:
    assert css_problem("<style>a{}</style>").startswith("WordPress refuses markup")
    assert css_problem("a { color: red;") == "1 opening brace never closed."
    assert css_problem("/* } */ a { }") == ""
    api = FakeSite()
    loaded = CssText(9, "a { color: red; }", {})
    saved = save_css(api, loaded, "a { color: blue; }")  # type: ignore[arg-type]
    assert api.writes == [
        (
            "POST",
            "wp/v2/global-styles/9",
            {"styles": {"color": {"text": "#111"}, "css": "a { color: blue; }"}},
        )
    ]
    assert saved.css == "a { color: blue; }"
    with pytest.raises(EditConflict):
        save_css(api, loaded, "a { color: green; }")  # type: ignore[arg-type]
    with pytest.raises(EditRefused):
        save_css(api, saved, "a {")  # type: ignore[arg-type]


def test_css_row_edits_a_block_themes_css_and_opens_a_classic_ones_customizer() -> None:
    api = FakeSite()
    row = css_rows(SITE, "https://r.example", api)[0]  # type: ignore[arg-type]
    assert row.kind == "custom_css" and row.raw["styles_id"] == 9
    assert row.cell("reach") == "1 line of Additional CSS"
    api.block_theme = False
    classic = css_rows(SITE, "https://r.example", api)[0]  # type: ignore[arg-type]
    assert classic.kind == "admin_screen"
    assert classic.link.endswith("customize.php?autofocus%5Bsection%5D=custom_css")


# -- the places: nodes, help, rows, keys -----------------------------------------------


def test_every_new_node_has_help_and_every_command_a_reason_for_no_chord() -> None:
    for node in (*DASHBOARD_NODES, *SITE_EDITOR_NODES):
        assert node_help(node.key), node.key
    for kind in ("template", "custom_css", "admin_screen", "sidebar"):
        assert row_help(kind) != row_help("fact"), kind
        assert kind in WORDPRESS_ACTIONS.row_types
    for row in (*TEMPLATE_ROWS, *CSS_ROWS, *SCREEN_ROWS, *NODE_ROWS, *WIDGET_ROWS, *MENU_ROWS):
        assert row.help and KEYLESS.get(row.command_id), row.command_id
    assert NODE_ROWS[0] in WORDPRESS_ACTIONS.rows_for("node")


# -- route gap 13: wp-abilities/v1/categories -----------------------------------------


def test_abilities_name_their_category_from_the_categories_route() -> None:
    from quill.core.wordpress.workbench_load import load

    class Api(FakeSite):
        def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Any:
            if route == "wp-abilities/v1/abilities":
                yield {"name": "shop/stock", "label": "Stock", "category": "shop-tools"}
            elif route == "wp-abilities/v1/categories":
                yield {"slug": "shop-tools", "label": "Shop tools"}

    rows = load(_ctx(Api()), "abilities:all", {}, {})
    assert rows[0].cell("category") == "Shop tools"
