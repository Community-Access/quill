"""WP-A and WP-B in the real frame: keymap, Updates, list-only keys, custom-type status nodes.

Reuses the fake site of ``test_wp_workbench_window``; work runs inline, so a
load or a write is finished when the call returns.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_KEYMAP_ID, command  # noqa: E402
from quill.core.wordpress.workbench_type_nodes import STATUS_SEP  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui.wordpress_workbench_window import SEP, WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _go,
    _inline,
    _labels,
    _select,
)


class SiteApi(FakeApi):
    """The fake site, with events in two statuses, a site status, plugins and themes."""

    def __init__(self) -> None:
        super().__init__()
        self.reads: list[tuple[str, dict[str, Any]]] = []
        self.events = [
            {"id": 31, "title": {"raw": "Gala"}, "status": "draft", "type": "event"},
            {"id": 32, "title": {"raw": "Fair"}, "status": "publish", "type": "event"},
        ]

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/statuses":
            return {"archived": {"name": "Archived", "slug": "archived"}}
        if route == "wp/v2/plugins":
            return [{"plugin": "akismet/akismet", "name": "Akismet", "version": "5.3"}]
        if route == "wp/v2/themes":
            return []
        return super().get(route, **params)

    def iter_collection(self, route: str, params: Any = None, **kw: Any):
        self.reads.append((route, dict(params or {})))
        if route == "wp/v2/events":
            status = (params or {}).get("status", "any")
            for event in self.events:
                if status in ("any", event["status"]):
                    yield dict(event)
            return
        yield from super().iter_collection(route, params, **kw)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = SiteApi()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.commands = commands  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _key(code: int, *, ctrl: bool = False, shift: bool = False) -> Any:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(code)
    event.SetControlDown(ctrl)
    event.SetShiftDown(shift)
    return event


def _focus(monkeypatch, window: Any) -> None:
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: window))


# -- WP-A: the keymap ------------------------------------------------------------------


def test_the_provider_names_its_own_keymap(bench) -> None:
    assert bench.provider.keymap_id == WORDPRESS_KEYMAP_ID
    assert bench._keys[command("go_calendar")] == "Ctrl+3"


def test_a_rebound_key_follows_the_menu_row(wx_session_app, tmp_path, monkeypatch) -> None:
    import quill.core.keymap as keymap

    monkeypatch.setattr(keymap, "load_keymap", lambda: {command("refresh"): "Ctrl+Alt+F5"})
    provider = WordPressWorkbenchProvider(
        _Commands([]), announce=lambda _t: None, data_dir=tmp_path, api_for=lambda _p: SiteApi()
    )
    frame = WorkbenchFrame(provider, announce=lambda _t: None, run_background=_inline)
    try:
        assert frame._keys[command("refresh")] == "Ctrl+Alt+F5"
        assert frame._menu_items[command("refresh")].GetItemLabel().endswith("Ctrl+Alt+F5")
    finally:
        frame.frame.Destroy()


# -- WP-A: Updates -----------------------------------------------------------------------


def test_updates_list_versions_and_enter_opens_dashboard_updates(bench) -> None:
    _go(bench, NodeRef("", "updates"))
    titles = [row.title for row in bench.rows]
    assert titles[:2] == ["WordPress", "Akismet"]
    _select(bench, 1)
    assert bench.rows[1].cell("installed") == "5.3"
    bench.default_action()
    assert bench.commands.host.opened == ["https://radio.example/wp-admin/update-core.php"]
    assert not bench.api.writes  # never claims, never runs, an update


# -- WP-A: Delete, Shift+Delete and Ctrl+Z act on list objects only ----------------------


def test_delete_in_the_filter_box_edits_the_text_and_trashes_nothing(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    bench.filter.ChangeValue("draft")
    bench.filter.SetSelection(0, 1)
    _focus(monkeypatch, bench.filter)
    bench._on_char_hook(_key(wx.WXK_DELETE))
    assert bench.filter.GetValue() == "raft"
    cut: list[bool] = []
    monkeypatch.setattr(bench.filter, "Cut", lambda: cut.append(True))  # no real clipboard
    bench._on_char_hook(_key(wx.WXK_DELETE, shift=True))
    assert cut == [True]
    undone: list[bool] = []
    monkeypatch.setattr(bench.filter, "Undo", lambda: undone.append(True))
    bench._on_char_hook(_key(ord("Z"), ctrl=True))
    assert undone == [True]
    assert not bench.api.writes and not bench.provider.history.entries


def test_delete_in_the_details_pane_and_the_tree_does_nothing(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    for window in (bench.details, bench.tree):
        _focus(monkeypatch, window)
        event = _key(wx.WXK_DELETE)
        bench._on_char_hook(event)
        assert not event.GetSkipped()  # kept from the menu's Delete
    assert not bench.api.writes


def test_delete_in_the_list_goes_on_to_move_to_trash(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    _focus(monkeypatch, bench.list)
    event = _key(wx.WXK_DELETE)
    bench._on_char_hook(event)
    assert event.GetSkipped()  # on to the menu accelerator, Move to Trash


def test_list_keys_from_the_status_bar_never_reach_the_rows(bench, monkeypatch) -> None:
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 0)
    monkeypatch.setattr(bench.status, "has_focus", lambda: True)
    for verb in ("trash", "delete_permanently", "undo"):
        bench.run(command(verb))
        assert "act on the list" in bench.said[-1]
    assert not bench.api.writes
    monkeypatch.setattr(bench.status, "has_focus", lambda: False)
    bench.run(command("trash"))
    assert ("DELETE", "wp/v2/posts/1", {}) in bench.api.writes


# -- WP-B: each custom type's status nodes ---------------------------------------------


def test_discovery_adds_each_types_status_nodes_from_the_site(bench) -> None:
    bench.provider.start()
    parent = bench._items[NodeRef("site", "content_types", SITE)]
    labels = _labels(bench.tree, parent)
    assert labels[:3] == ["Events", "Events, Published", "Events, Drafts"]
    assert "Events, Archived" in labels  # the site's own status, discovered


def test_a_status_node_lists_that_status_and_new_here_makes_that_type(bench, monkeypatch) -> None:
    bench.provider.start()
    ref = NodeRef("site", "custom_type", f"{SITE}{SEP}events{STATUS_SEP}draft")
    _go(bench, ref)
    assert [row.title for row in bench.rows] == ["Gala"]
    assert bench.api.reads[-1][0] == "wp/v2/events"
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "Picnic")
    bench.run(command("new_here"))
    assert bench.api.writes[-1] == ("POST", "wp/v2/events", {"title": "Picnic", "status": "draft"})


def test_a_status_node_takes_filters_to_the_site_and_batches(bench) -> None:
    bench.provider.start()
    _go(bench, NodeRef("site", "custom_type", f"{SITE}{SEP}events{STATUS_SEP}publish"))
    assert [row.title for row in bench.rows] == ["Fair"]
    bench.filter.ChangeValue("Fair")
    bench.apply_filter()
    assert bench.api.reads[-1][1].get("search") == "Fair"
    _select(bench, 0)
    bench.run(command("trash"))
    assert any(w[1] == "wp/v2/events/32" for w in bench.api.writes)
