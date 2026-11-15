"""wordpress.md 9.17 gaps 8, 10 and 13 in the real Workbench frame: every kind of widget (Add,
Change, Move, Remove, Preview), a classic menu's Earlier Versions, and the default Navigation
menu (``navigation-fallback``). Reuses the fake site of ``test_wp_workbench_window``."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress import widget_types as wt  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_block_dialogs as bdlg  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _inline,
)

SEARCH_FORM = (
    '<p><label for="w-title">Title:</label>'
    '<input id="w-title" name="widget-search[2][title]" type="text" value="Find"></p>'
    '<p><input id="w-c" name="widget-search[2][count]" type="checkbox" checked>'
    '<label for="w-c">Show count</label></p>'
    '<select name="widget-search[2][style]"><option value="a">Plain</option>'
    '<option value="b" selected>Boxed</option></select>'
    '<input type="hidden" name="widget-id" value="search-2">'
)


class WidgetApi(FakeApi):
    def __init__(self) -> None:
        super().__init__()
        self.role = "administrator"
        self.widgets: dict[str, dict[str, Any]] = {
            "block-3": {
                "id": "block-3",
                "id_base": "block",
                "sidebar": "footer",
                "instance": {
                    "raw": {"content": "<!-- wp:paragraph --><p>Hi</p><!-- /wp:paragraph -->"}
                },
                "rendered": "<p>Hi</p>",
            },
            "search-2": {
                "id": "search-2",
                "id_base": "search",
                "sidebar": "footer",
                "instance": {"encoded": "abc", "hash": "h1"},
                "rendered": "<form>Find</form>",
            },
        }
        self.menu_items = [
            {
                "id": 31,
                "title": {"raw": "Home"},
                "type": "custom",
                "url": "/",
                "parent": 0,
                "menu_order": 1,
                "menus": 3,
            },
            {
                "id": 32,
                "title": {"raw": "Shows"},
                "type": "custom",
                "url": "/shows",
                "parent": 0,
                "menu_order": 2,
                "menus": 3,
            },
        ]

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            me = super().get(route, **params)
            me["capabilities"]["edit_theme_options"] = True
            return me
        if route == "wp/v2/widget-types":
            return [
                {"id": "search", "name": "Search", "description": "A search form."},
                {"id": "block", "name": "Block", "description": "Any block."},
            ]
        if route == "wp/v2/widgets":
            return [dict(w) for w in self.widgets.values() if w["sidebar"] == params.get("sidebar")]
        if route.startswith("wp/v2/widgets/"):
            return dict(self.widgets[route.rsplit("/", 1)[1]])
        if route == "wp/v2/sidebars":
            return [
                {"id": "footer", "name": "Footer", "widgets": ["block-3", "search-2"]},
                {"id": "side", "name": "Sidebar", "widgets": []},
            ]
        if route == "wp/v2/menu-locations":
            return {}
        if route == "wp-block-editor/v1/navigation-fallback":
            return {"id": 88, "title": {"raw": "Main navigation"}}
        return super().get(route, **params)

    def iter_collection(self, route: str, params: Any = None, **kw: Any) -> Any:
        if route == "wp/v2/menus":
            yield {"id": 3, "name": "Top", "locations": []}
        elif route == "wp/v2/menu-items":
            yield from (dict(i) for i in self.menu_items)
        elif route == "wp/v2/navigation":
            return
        else:
            yield from super().iter_collection(route, params, **kw)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route.endswith("/encode"):
            if "form_data" in body:
                return {
                    "form": SEARCH_FORM,
                    "instance": {"encoded": "new", "hash": "h2"},
                    "preview": "<form>Look</form>",
                }
            return {
                "form": SEARCH_FORM,
                "instance": body.get("instance", {}),
                "preview": "<form>Find</form>",
            }
        if route.endswith("/render"):
            return {"preview": "<form>Find things</form>"}
        if route == "wp/v2/widgets":
            return {"id": "search-9", **body}
        if route.startswith("wp/v2/widgets/"):
            widget = self.widgets[route.rsplit("/", 1)[1]]
            widget.update(body)
            return dict(widget)
        if route == "wp/v2/menu-items":
            return {"id": 40, **body}
        return dict(body or {})

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        if route.startswith("wp/v2/widgets/"):
            self.widgets[route.rsplit("/", 1)[1]]["sidebar"] = wt.INACTIVE
        return {}


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = WidgetApi()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _footer() -> WbRow:
    return WbRow("sidebar", SITE, "footer", {"sidebar": "Footer"}, "")


def _menu() -> WbRow:
    return WbRow("menu", SITE, "3", {"menu": "Top"}, "")


def _previews(monkeypatch: Any, answer: bool = True) -> list[Any]:
    seen: list[Any] = []
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: seen.append((k["summary"], k["lines"])) or answer
    )
    return seen


def test_a_legacy_widgets_own_form_is_read_and_sent_back_by_its_names() -> None:
    controls = wt.form_fields(SEARCH_FORM)
    assert [(c.key, c.label, c.kind) for c in controls] == [
        ("title", "Title", "text"),
        ("count", "Show count", "check"),
        ("style", "Style", "choice"),
    ]
    assert controls[2].value == "b" and controls[2].choices == [("a", "Plain"), ("b", "Boxed")]
    data = wt.encode_answers(controls, {"widget-search[2][title]": "Look"})
    assert data == (
        "widget-search%5B2%5D%5Btitle%5D=Look&widget-search%5B2%5D%5Bcount%5D=on"
        "&widget-search%5B2%5D%5Bstyle%5D=b"
    )


def test_add_a_legacy_widget_on_its_own_form_then_ctrl_z_removes_it(bench, monkeypatch) -> None:
    previews = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 1)  # Search (Block sorts first)
    forms: list[list[str]] = []

    def fill(*_a: Any, **k: Any) -> dict[str, Any]:
        forms.append([f.label for f in k["fields"]])
        return {"widget-search[2][title]": "Look", "widget-search[2][count]": False}

    monkeypatch.setattr(bdlg, "ask_fields", fill)
    bench.provider.do_add_widget(None, _footer())
    assert forms == [["&Title:", "&Show count", "St&yle:"]]
    assert previews[0][1] == ["Visitors see: Look"]
    assert (
        "POST",
        "wp/v2/widgets",
        {"id_base": "search", "sidebar": "footer", "instance": {"encoded": "new", "hash": "h2"}},
    ) in bench.api.writes
    bench.provider.do_undo(None, None)
    assert bench.api.writes[-1] == ("DELETE", "wp/v2/widgets/search-9", {"force": True})


def test_change_a_block_widget_as_text_and_undo(bench, monkeypatch) -> None:
    _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    new = "<!-- wp:paragraph --><p>Bye</p><!-- /wp:paragraph -->"
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: new)
    bench.provider.do_change_widget(None, _footer())
    assert bench.api.widgets["block-3"]["instance"] == {"raw": {"content": new}}
    bench.provider.do_undo(None, None)
    assert "Hi" in bench.api.widgets["block-3"]["instance"]["raw"]["content"]


def test_change_a_legacy_widget_previews_what_visitors_see(bench, monkeypatch) -> None:
    previews = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 1)
    monkeypatch.setattr(bdlg, "ask_fields", lambda *_a, **_k: {"widget-search[2][title]": "Look"})
    bench.provider.do_change_widget(None, _footer())
    assert previews[0][1] == ["Visitors saw: Find", "Visitors will see: Look"]
    assert bench.api.widgets["search-2"]["instance"] == {"encoded": "new", "hash": "h2"}


def test_a_widget_changed_meanwhile_is_not_overwritten(bench, monkeypatch) -> None:
    _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 1)

    def fill(*_a: Any, **_k: Any) -> dict[str, Any]:
        bench.api.widgets["search-2"]["instance"] = {"encoded": "theirs", "hash": "h9"}
        return {"widget-search[2][title]": "Look"}

    monkeypatch.setattr(bdlg, "ask_fields", fill)
    bench.provider.do_change_widget(None, _footer())
    assert bench.api.widgets["search-2"]["instance"]["encoded"] == "theirs"
    assert "changed on the site" in bench.said[-1]


def test_move_and_remove_a_widget_each_undone(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    bench.provider.do_move_widget(None, _footer())
    assert bench.api.widgets["block-3"]["sidebar"] == "side"
    bench.provider.do_undo(None, None)
    assert bench.api.widgets["block-3"]["sidebar"] == "footer"
    bench.provider.do_remove_widget(None, _footer())
    assert bench.api.widgets["block-3"]["sidebar"] == wt.INACTIVE
    assert "Inactive Widgets" in bench.said[-1]
    bench.provider.do_undo(None, None)
    assert bench.api.widgets["block-3"]["sidebar"] == "footer"


def test_preview_widgets_reads_the_area_as_a_visitor_sees_it(bench, monkeypatch) -> None:
    reports: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: reports.append(k["text"]))
    bench.provider.do_preview_widgets(None, _footer())
    assert reports == ["Paragraph block: Hi: Hi\nSearch widget: Find: Find things"]


def test_earlier_versions_of_a_classic_menu_bring_back_a_removed_item(bench, monkeypatch) -> None:
    bench.provider.do_menu_versions(None, _menu())  # the first read: kept, nothing earlier
    assert "no earlier versions yet" in bench.said[-1]
    bench.api.menu_items.pop()  # Shows is removed on the site
    _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    bench.provider.do_menu_versions(None, _menu())
    added = [w for w in bench.api.writes if w[1] == "wp/v2/menu-items"]
    assert added and added[0][2]["title"] == "Shows" and added[0][2]["url"] == "/shows"
    bench.provider.do_undo(None, None)
    assert bench.api.writes[-1] == ("DELETE", "wp/v2/menu-items/40", {"force": True})


def test_default_navigation_menu_asks_first_because_it_can_make_one(bench, monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **k: asked.append(k["message"]) or False)
    bench.provider.do_default_navigation(None, _menu())
    assert "WordPress makes one" in asked[0]
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    bench.provider.do_default_navigation(None, _menu())
    assert bench.said[-1] == (
        f"Where a block theme has no menu chosen, {SITE} shows Main navigation, Navigation menu 88."
    )
