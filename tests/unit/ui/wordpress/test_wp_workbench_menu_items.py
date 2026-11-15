"""Add Menu Item, Ctrl+N on a menu and Add New Pages Automatically in the real Workbench frame
(wordpress.md 9.9). Reuses the fake site of ``test_wp_workbench_widgets_menus``."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS  # noqa: E402
from quill.core.wordpress.workbench_dashboard_places import KEYLESS, MENU_ROWS  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_widgets_menus import WidgetApi  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    _Commands,
    _inline,
)


class MenuApi(WidgetApi):
    def __init__(self) -> None:
        super().__init__()
        self.menu = {"id": 3, "name": "Top", "auto_add": False, "locations": []}
        self.items = {int(i["id"]): i for i in self.menu_items}

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/types" and params.get("context") == "edit":
            return {
                "page": {"name": "Pages", "rest_base": "pages", "viewable": True},
                "post": {"name": "Posts", "rest_base": "posts", "viewable": True},
            }
        if route == "wp/v2/taxonomies" and params.get("context") == "edit":
            return {"category": {"name": "Categories", "rest_base": "categories"}}
        if route == "wp/v2/menus/3":
            return dict(self.menu)
        if route.startswith("wp/v2/menu-items/"):
            return dict(self.items.get(int(route.rsplit("/", 1)[1]), {}))
        return super().get(route, **params)

    def iter_collection(self, route: str, params: Any = None, **kw: Any) -> Any:
        if route == "wp/v2/menu-items":
            yield from (dict(i) for i in self.items.values())
        elif route == "wp/v2/pages":
            yield {"id": 7, "title": {"raw": "Contact"}}
        else:
            yield from super().iter_collection(route, params, **kw)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route == "wp/v2/menus/3":
            self.writes.append(("POST", route, body))
            self.menu.update(body)
            return dict(self.menu)
        if route == "wp/v2/menu-items":
            self.writes.append(("POST", route, body))
            self.items[40] = {"id": 40, **body, "title": {"raw": body["title"]}}
            return dict(self.items[40])
        if route.startswith("wp/v2/menu-items/"):
            self.writes.append(("POST", route, body))
            self.items[int(route.rsplit("/", 1)[1])].update(body)
            return {}
        return super().post(route, body, **params)

    def delete(self, route: str, **params: Any) -> Any:
        self.items.pop(int(route.rsplit("/", 1)[1]), None)
        return super().delete(route, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = MenuApi()
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _menu() -> WbRow:
    return WbRow("menu", SITE, "3", {"menu": "Top"}, "", route="wp/v2/menus/3")


def _answers(monkeypatch: Any, choices: list[int | None], texts: list[str | None]) -> list[Any]:
    asked: list[Any] = []

    def choose(*_a: Any, **k: Any) -> int | None:
        asked.append((k["prompt"], list(k["rows"])))
        return choices.pop(0)

    monkeypatch.setattr(dlg, "ask_choice", choose)
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: texts.pop(0))
    return asked


def _previews(monkeypatch: Any, answer: bool = True) -> list[Any]:
    seen: list[Any] = []
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: seen.append((k["summary"], k["lines"])) or answer
    )
    return seen


def test_add_a_page_first_in_the_menu_after_a_search_then_ctrl_z(bench, monkeypatch) -> None:
    previews = _previews(monkeypatch)
    # kind: Pages; search "cont"; Contact; under: top level; position: First
    asked = _answers(monkeypatch, [0, 0, 0, 0], ["cont"])
    bench.provider.do_add_menu_item(None, _menu())
    assert asked[0][1] == ["Pages", "Posts", "Custom Links", "Categories"]
    assert asked[3][1] == ["First", "After Home", "After Shows"]
    assert previews[0][1][:2] == ["Adds: Contact, page", "Where: at the top level, first, 1 of 3."]
    added = next(w for w in bench.api.writes if w[1] == "wp/v2/menu-items")
    assert added[2]["object_id"] == 7 and added[2]["menu_order"] == 1
    assert bench.api.items[31]["menu_order"] == 2 and bench.api.items[32]["menu_order"] == 3
    assert bench.said[-1] == "Added Contact to the menu."
    bench.provider.do_undo(None, None)
    assert 40 not in bench.api.items
    assert bench.api.items[31]["menu_order"] == 1 and bench.api.items[32]["menu_order"] == 2


def test_add_a_custom_link_under_an_item(bench, monkeypatch) -> None:
    previews = _previews(monkeypatch)
    _answers(monkeypatch, [2, 2], ["https://map.example", "Map"])  # Custom Links; under Shows
    bench.provider.do_add_menu_item(None, _menu())
    assert previews[0][1][0] == "Adds: Map, link, to https://map.example"
    assert bench.api.items[40]["parent"] == 32 and bench.api.items[40]["type"] == "custom"


def test_a_cancelled_preview_sends_nothing(bench, monkeypatch) -> None:
    _previews(monkeypatch, answer=False)
    _answers(monkeypatch, [0, 0, 0, 2], [""])  # View All
    bench.provider.do_add_menu_item(None, _menu())
    assert not [w for w in bench.api.writes if w[1].startswith("wp/v2/menu-items")]


def test_ctrl_n_with_a_menu_selected_offers_an_item_in_it_first(bench, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(bench.provider, "do_add_menu_item", lambda *_a: calls.append("item"))
    asked = _answers(monkeypatch, [0, None], [])
    ref = type("Ref", (), {"key": "menus", "instance": SITE})()
    monkeypatch.setattr(bench.provider, "site_of", lambda _ref: SITE)
    bench.provider.do_new_here(ref, _menu())
    assert asked[0][1] == ["A new item in Top", "A new menu"] and calls == ["item"]
    bench.provider.do_new_here(ref, _menu())  # cancelled: no new menu either
    assert calls == ["item"] and not bench.api.writes


def test_add_new_pages_automatically_toggles_after_a_preview_and_undoes(bench, monkeypatch) -> None:
    previews = _previews(monkeypatch)
    bench.provider.do_menu_auto_add(None, _menu())
    assert previews[0][1][0].startswith("Now: off.")
    assert bench.api.menu["auto_add"] is True
    assert bench.said[-1] == "Adding new pages automatically to Top is on."
    bench.provider.do_undo(None, None)
    assert bench.api.menu["auto_add"] is False


def test_both_commands_are_on_a_menus_context_menu_with_help_and_a_reason() -> None:
    verbs = {r.command_id for r in WORDPRESS_ACTIONS.rows_for("menu")}
    for row in MENU_ROWS[:2]:
        assert row.command_id in verbs and row.help and KEYLESS[row.command_id]
    assert [r.label for r in MENU_ROWS[:2]] == [
        "Add Menu Item...",
        "Add New Pages Automatically...",
    ]


def test_arrange_items_opens_the_menus_window_on_this_menu_and_site(bench) -> None:
    opened: list[dict[str, Any]] = []
    bench.provider.commands.cmd_menus = lambda **kw: opened.append(kw)
    bench.provider.do_arrange_menu_items(None, _menu())
    assert opened and opened[0]["menu_id"] == 3
    assert opened[0]["profile"] is bench.provider.profile(SITE)
    verbs = {r.command_id for r in WORDPRESS_ACTIONS.rows_for("menu")}
    assert "wordpress.workbench.arrange_menu_items" in verbs
    assert KEYLESS["wordpress.workbench.arrange_menu_items"]


def test_arrange_items_needs_a_menu(bench) -> None:
    bench.provider.do_arrange_menu_items(None, None)
    assert bench.said[-1] == "Choose a menu in Menus and Navigation first."
