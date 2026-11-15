"""WP-A and WP-B, wx-free: keymap, Updates, Membership Orders, type nodes, Content Model."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import SiteInfo
from quill.core.wordpress.workbench_load import SiteContext
from quill.core.wordpress.workbench_rows import WbRow

# -- WP-A: the window's own keymap ---------------------------------------------------


def test_the_window_has_its_own_rebindable_app_keymap() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.wordpress.workbench_actions import (
        LIST_KEYS,
        WINDOW_MENU,
        WORDPRESS_KEYMAP_ID,
        WORDPRESS_KEYS,
    )
    from quill.core.workbench.menus import rows

    assert WORDPRESS_KEYMAP_ID == "wordpress_workbench"
    assert APP_KEYMAPS[WORDPRESS_KEYMAP_ID] == WORDPRESS_KEYS
    for _menu, row in rows(WINDOW_MENU):
        assert WORDPRESS_KEYS[row.command_id] == row.key  # the menu and the keymap agree
    assert LIST_KEYS <= set(WORDPRESS_KEYS.values())
    # The GitHub Workbench keeps its own entry beside it.
    assert "github_workbench" in APP_KEYMAPS


def test_the_go_row_avoids_the_ai_chords_it_does_not_reconcile() -> None:
    """Ctrl+3 is Calendar (no AI menu here); Ctrl+4 and Ctrl+8 stay unclaimed."""
    from quill.core.wordpress.workbench_actions import WORDPRESS_KEYS, command

    owners = {key: cid for cid, key in WORDPRESS_KEYS.items()}
    assert owners["Ctrl+3"] == command("go_calendar")
    assert "Ctrl+4" not in owners and "Ctrl+8" not in owners


# -- WP-A: Updates ---------------------------------------------------------------------


class _UpdatesApi:
    def __init__(self, *, plugins: Any = None, deny: tuple[str, ...] = ()) -> None:
        self.plugins = plugins
        self.deny = deny
        self.asked: list[str] = []

    def get(self, route: str, **_params: Any) -> Any:
        self.asked.append(route)
        if route in self.deny:
            raise WordPressApiError("Sorry, you are not allowed to do that.", status=403)
        if route == "wp/v2/plugins":
            return self.plugins or [
                {
                    "plugin": "akismet/akismet",
                    "name": "Akismet",
                    "version": "5.3",
                    "status": "active",
                    "auto_update": True,
                },
                {"plugin": "hello/hello", "name": "Hello Dolly", "version": "1.7.2"},
                {"plugin": "seo/seo", "name": "SEO", "version": "2.0", "new_version": "2.1"},
            ]
        if route == "wp/v2/themes":
            return [{"stylesheet": "twentyfive", "name": {"raw": "Twenty Five"}, "version": "1.2"}]
        if route == "wp-site-health/v1/tests/background-updates":
            return {"status": "good", "label": "Background updates are working"}
        return {}


def _ctx(api: Any, *, routes: tuple[str, ...] = (), namespaces: tuple[str, ...] = ()) -> Any:
    info = SiteInfo("Radio", "", "https://radio.example", "6.9", namespaces, "", routes)
    return SiteContext("Radio", api, url="https://radio.example/", info=info)


def test_updates_say_what_rest_knows_and_never_claim_an_update() -> None:
    from quill.core.wordpress.workbench_updates import NOT_REPORTED, update_rows

    api = _UpdatesApi()
    rows = update_rows(_ctx(api, routes=("/wp-site-health/v1/tests/background-updates",)))
    by_name = {row.title: row for row in rows}
    assert [row.title for row in rows][:2] == ["WordPress", "Automatic updates"]
    core = by_name["WordPress"]
    assert core.cell("installed") == "6.9" and core.cell("update") == NOT_REPORTED
    assert "does not say whether a newer" in core.detail
    assert by_name["Automatic updates"].cell("update") == "Good"
    assert by_name["Akismet"].cell("installed") == "5.3"
    assert by_name["Akismet"].cell("update") == NOT_REPORTED
    assert "updates itself automatically" in by_name["Akismet"].detail
    assert "does not update itself" not in by_name["Hello Dolly"].detail  # not reported: unsaid
    # A version only when the site's own payload says so.
    assert by_name["SEO"].cell("update") == "Version 2.1 reported by the site"
    assert by_name["Twenty Five"].cell("installed") == "1.2"
    for row in rows:
        assert row.kind == "update"
        assert row.link == "https://radio.example/wp-admin/update-core.php"
        assert "Dashboard > Updates" in row.detail
        assert "updated" not in row.detail.lower()
    # Read only: nothing was written, only read.
    assert all(not route.endswith("/update") for route in api.asked)


def test_updates_say_why_a_role_cannot_list_plugins_and_skip_an_absent_health_test() -> None:
    from quill.core.wordpress.workbench_updates import update_rows

    api = _UpdatesApi(deny=("wp/v2/plugins",))
    rows = update_rows(_ctx(api))  # no background-updates route in the index
    titles = [row.title for row in rows]
    assert "Automatic updates" not in titles
    plugins = next(row for row in rows if row.title == "Plugins")
    assert plugins.cell("update") == "Not known"
    assert "cannot list its plugins" in plugins.detail


def test_updates_has_a_node_an_action_and_help() -> None:
    from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command
    from quill.core.wordpress.workbench_attention import ATTENTION
    from quill.core.wordpress.workbench_node_help import ROW_HELP
    from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

    node = WORDPRESS_TREE.node("updates")
    assert node.loader == "attention:updates" and "updates" in ATTENTION
    first = WORDPRESS_ACTIONS.rows_for("update")[0]
    assert first.command_id == command("open_on_site") and first.default
    assert "Dashboard" in first.label
    assert "update" in ROW_HELP


# -- WP-A: Membership Orders, Shop and Podcast ---------------------------------------


def _order(code: str, status: str) -> WbRow:
    return WbRow(
        "pmpro",
        "Radio",
        code,
        {"code": code, "status": status.title(), "total": "10"},
        f"Order {code}.",
        status=status,
        subkind="order",
    )


def test_membership_orders_list_only_the_ones_waiting_on_a_person(monkeypatch) -> None:
    from quill.core.wordpress import workbench_pmpro
    from quill.core.wordpress.workbench_updates import membership_orders

    asked: list[str] = []

    def fake_load(_ctx: Any, view: str) -> list[WbRow]:
        asked.append(view)
        return [_order("A1", "success"), _order("B2", "pending"), _order("C3", "error")]

    monkeypatch.setattr(workbench_pmpro, "load_pmpro", fake_load)
    rows = membership_orders(_ctx(object(), namespaces=("wp/v2", "wp-abilities/v1")))
    assert asked == ["orders"]
    assert [row.key for row in rows] == ["B2", "C3"]
    assert rows[0].cell("site") == "Radio"
    assert rows[0].cell("what") == "Membership order B2"


def test_a_site_without_pmpro_abilities_adds_no_membership_orders(monkeypatch) -> None:
    from quill.core.wordpress import workbench_pmpro
    from quill.core.wordpress.workbench_updates import membership_orders

    monkeypatch.setattr(workbench_pmpro, "load_pmpro", lambda *_a: pytest.fail("asked"))
    assert membership_orders(_ctx(object(), namespaces=("wp/v2",))) == []


def test_membership_and_shop_orders_stay_distinct() -> None:
    from quill.core.wordpress.workbench_node_help import NODE_HELP
    from quill.core.wordpress.workbench_tree import PLANNED_WORDS, WORDPRESS_TREE

    orders = WORDPRESS_TREE.node("orders")
    assert orders.label == "Membership Orders" and orders.loader == "attention:orders"
    assert "Shop orders are not membership orders" in NODE_HELP["orders"]
    shop_orders = WORDPRESS_TREE.template_node("site", "shop_orders")
    assert (shop_orders.label, shop_orders.loader) == ("Shop Orders", "shop:orders")
    assert "not membership orders" in NODE_HELP["shop_orders"]
    assert "Membership Orders" in NODE_HELP["shop_orders"]
    assert WORDPRESS_TREE.template_node("site", "podcast").loader == "podcast:episodes"
    assert PLANNED_WORDS == {}  # nothing is a placeholder now


# -- WP-B: each custom type's status nodes --------------------------------------------


def test_each_custom_type_gets_its_discovered_statuses_after_it() -> None:
    from quill.core.wordpress.workbench_type_nodes import STATUS_SEP, type_children

    found = type_children(
        "Radio",
        "|",
        [("events", "Events"), ("library/v1/books", "Books")],
        [("publish", "Published"), ("draft", "Drafts"), ("archived", "Archived")],
    )
    assert found[:4] == (
        ("Radio|events", "Events"),
        (f"Radio|events{STATUS_SEP}publish", "Events, Published"),
        (f"Radio|events{STATUS_SEP}draft", "Events, Drafts"),
        (f"Radio|events{STATUS_SEP}archived", "Events, Archived"),
    )
    assert found[4] == ("Radio|library/v1/books", "Books")


def test_a_status_node_loads_its_type_at_the_discovered_rest_base_and_status() -> None:
    from quill.core.wordpress.workbench_load import load
    from quill.core.wordpress.workbench_type_nodes import STATUS_SEP

    class _Api:
        def __init__(self) -> None:
            self.reads: list[tuple[str, dict[str, Any]]] = []

        def iter_collection(self, route: str, params: Any = None, **_kw: Any):
            self.reads.append((route, dict(params or {})))
            return iter(())

    api = _Api()
    ctx = SiteContext("Radio", api)  # type: ignore[arg-type]
    load(ctx, "items:custom", {"status": "any"}, {}, dynamic=f"events{STATUS_SEP}draft")
    load(ctx, "items:custom", {"status": "any"}, {}, dynamic="library/v1/books")
    load(ctx, "items:custom", {"status": "any"}, {"status": "trash"}, dynamic="events")
    assert [(route, p["status"]) for route, p in api.reads] == [
        ("wp/v2/events", "draft"),
        ("library/v1/books", "any"),
        ("wp/v2/events", "trash"),  # the filter's status wins over the node's
    ]


# -- WP-B: Content Model definitions ---------------------------------------------------


class _ModelApi:
    def get(self, route: str, **_p: Any) -> Any:
        if route == "wp/v2/types":
            return {
                "post": {"name": "Posts", "rest_base": "posts"},
                "tribe_events": {"name": "Events", "rest_base": "tribe_events"},
            }
        return {"genre": {"name": "Genres", "rest_base": "genres"}}


def test_the_content_model_says_every_definition_is_read_only_and_why() -> None:
    from quill.core.wordpress.workbench_discovered import READ_ONLY, model_rows
    from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

    rows = model_rows(_ModelApi(), "S")  # type: ignore[arg-type]
    assert {row.cell("definition") for row in rows} == {READ_ONLY}
    post, events, genre = rows
    assert "Read only definition, part of WordPress" in post.detail
    assert "defined in The Events Calendar's code" in events.detail
    assert "Its items are edited in their own lists" in genre.detail
    assert all(row.raw["editable_definition"] is False for row in rows)
    assert all("Editable" not in row.cell("definition") for row in rows)
    columns = WORDPRESS_TREE.template_node("site", "content_model").columns
    assert columns.index("registered_by") < columns.index("definition")


def test_the_content_model_keeps_code_defined_types_read_only_beside_site_types() -> None:
    from quill.core.wordpress.workbench_discovered import SITE_TYPES_NAMESPACE, model_rows

    # QUILL Site Types is on the site but defines none of these: each stays read only,
    # and says that what is defined with the plugin is the editable kind.
    rows = model_rows(_ModelApi(), "S", namespaces=("wp/v2", SITE_TYPES_NAMESPACE))  # type: ignore[arg-type]
    assert "what you define with it (Ctrl+N here) is editable" in rows[0].detail
    assert rows[0].cell("definition") == "Read only"
