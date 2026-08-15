"""Browse Stations -- "Find in this folder": recursive, bounded subtree search.

Characterizes the collector (``browse_find.find_matches``, extracted from the
dialog under GATE-11) against a stubbed ``_fetch_children``, so the scoped
search is covered without a wx.App.

The refactor changed what this can be: the collector used to need a parallel
mapping (``_subtree_children``) that had to be kept in step with the renderer by
hand, and silently skipped any source nobody remembered to add to it. Now it
recurses whatever ``browse()`` returns, so a new source is searchable the moment
it exists -- which is what the last test here pins down.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.radio.browse_nodes import folder, lazy_leaf, leaf
from quill.core.radio.models import RadioStation
from quill.ui.radio import browse_find
from quill.ui.radio.browse_tree_dialog import BrowseTreeDialog


def _st(name: str) -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://s/{name}")


def _dialog(tree: dict[str, list]) -> Any:
    """A dialog whose only source of truth is *tree*: node_id -> BrowseNodes."""
    d = BrowseTreeDialog.__new__(BrowseTreeDialog)
    d._safe_mode = False
    d._fetch_children = lambda node_id: tree.get(node_id, [])  # type: ignore[method-assign]
    return d


def test_find_filters_a_flat_station_folder() -> None:
    d = _dialog({"acb": [leaf(_st("ACB Media 1")), leaf(_st("Jazz Hour"))]})
    matches, capped = browse_find.find_matches(d, "acb", "jazz")
    assert [m["label"] for m in matches] == ["Jazz Hour"]
    assert not capped


def test_find_is_case_insensitive() -> None:
    d = _dialog({"acb": [leaf(_st("Jazz Hour"))]})
    assert len(browse_find.find_matches(d, "acb", "JAZZ")[0]) == 1


def test_find_recurses_folders_from_the_root() -> None:
    d = _dialog({
        "iheart": [folder("iheart:1", "Rock"), folder("iheart:2", "Jazz")],
        "iheart:1": [folder("iheartletter:1\tA", "A")],
        "iheartletter:1\tA": [leaf(_st("Alpha Jazz"))],
        "iheart:2": [folder("iheartletter:2\tB", "B")],
        "iheartletter:2\tB": [leaf(_st("Beta Rock"))],
    })
    matches, _capped = browse_find.find_matches(d, "iheart", "jazz")
    assert [m["label"] for m in matches] == ["Alpha Jazz"]


def test_find_scopes_to_one_branch_only() -> None:
    d = _dialog({
        "iheart": [folder("iheart:1", "Rock"), folder("iheart:2", "Jazz")],
        "iheart:1": [leaf(_st("Rocking Jazz"))],
        "iheart:2": [leaf(_st("Other Jazz"))],
    })
    matches, _capped = browse_find.find_matches(d, "iheart:1", "jazz")
    assert [m["label"] for m in matches] == ["Rocking Jazz"]


def test_find_matches_a_lazy_leaf_by_its_label() -> None:
    # A TuneIn station has no RadioStation until it is played, but it is still
    # findable -- searching must not require having resolved the whole folder.
    d = _dialog({"tunein": [lazy_leaf("tuneinstation:s1", "BBC Radio Jazz")]})
    matches, _capped = browse_find.find_matches(d, "tunein", "jazz")
    assert [m["label"] for m in matches] == ["BBC Radio Jazz"]
    assert matches[0]["resolve_lazily"] is True


def test_find_skips_action_rows() -> None:
    from quill.core.radio.browse_nodes import action

    d = _dialog({"servers": [action("addserver", "Add a Jazz Server..."), leaf(_st("Jazz FM"))]})
    matches, _capped = browse_find.find_matches(d, "servers", "jazz")
    assert [m["label"] for m in matches] == ["Jazz FM"]


def test_find_no_match_returns_empty() -> None:
    d = _dialog({"acb": [leaf(_st("ACB Media 1"))]})
    matches, capped = browse_find.find_matches(d, "acb", "nothing here")
    assert matches == [] and not capped


def test_find_reports_when_a_depth_bound_cut_it_short() -> None:
    # A bound that is hit silently reads as "there is nothing deeper".
    deep = {f"n{i}": [folder(f"n{i + 1}", f"level {i + 1}")] for i in range(20)}
    d = _dialog(deep)
    _matches, capped = browse_find.find_matches(d, "n0", "anything")
    assert capped


def test_find_reports_when_a_fetch_budget_cut_it_short() -> None:
    wide = {"root": [folder(f"f{i}", f"folder {i}") for i in range(200)]}
    wide.update({f"f{i}": [leaf(_st(f"Station {i}"))] for i in range(200)})
    d = _dialog(wide)
    _matches, capped = browse_find.find_matches(d, "root", "zzz")
    assert capped


def test_a_new_source_is_searchable_without_touching_the_collector() -> None:
    # The regression this refactor removes: the old collector needed a parallel
    # per-kind mapping, so a source added to the renderer and forgotten here was
    # silently unsearchable.
    d = _dialog({
        "brandnew": [folder("brandnew:sub", "Sub")],
        "brandnew:sub": [leaf(_st("Findable Jazz"))],
    })
    matches, _capped = browse_find.find_matches(d, "brandnew", "jazz")
    assert [m["label"] for m in matches] == ["Findable Jazz"]


def test_find_anchor_falls_back_to_the_folder_a_station_is_in() -> None:
    class _N:
        def __init__(self, ok=True):
            self._ok = ok

        def IsOk(self):  # noqa: N802
            return self._ok

    station_node, folder_node = _N(), _N()
    data = {
        station_node: {"node_id": "x", "label": "A Station", "station": _st("A")},
        folder_node: {"node_id": "acb", "label": "ACB Media", "loaded": True},
    }
    parents = {station_node: folder_node}
    d = BrowseTreeDialog.__new__(BrowseTreeDialog)
    d._tree = SimpleNamespace(
        GetSelection=lambda: station_node,
        GetItemData=lambda n: data.get(n),
        GetItemParent=lambda n: parents.get(n, _N(False)),
    )
    assert browse_find.find_anchor_node(d) is folder_node
