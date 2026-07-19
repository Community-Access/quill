"""Unified Browse Stations tree -- node building, play routing, favorites.

Drives the wx-heavy dialog against a fake tree (the real one needs a wx.App to
construct); the source catalogs themselves are tested in their own core modules.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.tunein import TuneInResult
from quill.ui.radio.browse_tree_dialog import BrowseTreeDialog


class _Node:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok

    def IsOk(self) -> bool:  # noqa: N802
        return self._ok


class _FakeTree:
    def __init__(self) -> None:
        self._data: dict = {}
        self.children: dict = {}
        self._selection = _Node(False)

    def AppendItem(self, parent, label):  # noqa: N802
        node = _Node()
        self.children.setdefault(parent, []).append((node, label))
        return node

    def SetItemData(self, node, data):  # noqa: N802
        self._data[node] = data

    def GetItemData(self, node):  # noqa: N802
        return self._data.get(node)

    def DeleteChildren(self, node):  # noqa: N802
        self.children[node] = []

    def GetChildrenCount(self, node, _recursive):  # noqa: N802
        return len(self.children.get(node, []))

    def GetFirstChild(self, node):  # noqa: N802
        kids = self.children.get(node, [])
        return (kids[0][0] if kids else _Node(False), None)

    def SelectItem(self, node):  # noqa: N802
        self._selection = node

    def GetSelection(self):  # noqa: N802
        return self._selection


def _dialog() -> Any:
    d = BrowseTreeDialog.__new__(BrowseTreeDialog)
    d._tree = _FakeTree()
    d._announced: list[str] = []
    d._announce = d._announced.append
    d._favorites = RadioFavoritesStore(favorites=[])
    d._details = SimpleNamespace(SetValue=lambda _v: None)
    d._play_btn = SimpleNamespace(Enable=lambda _v: None)
    d._favorite_btn = SimpleNamespace(Enable=lambda _v: None, SetLabel=lambda _l: None)
    d._on_favorites_changed = lambda: None
    return d


def _child_data(d, node):
    return [d._tree.GetItemData(n) for n, _label in d._tree.children.get(node, [])]


def test_add_children_stations_makes_station_leaves() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "stations", "payload": "acb"})
    d._add_children(root, "stations", [RadioStation(name="ACB 1", stream_url="https://x/1")])
    data = _child_data(d, root)
    assert data[0]["kind"] == "station"
    assert data[0]["station"].name == "ACB 1"


def test_add_children_genres_makes_genre_folders() -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "genres", "payload": m3u_catalog})
    d._add_children(root, "genres", ["acid_jazz", "rock"])
    labels = [label for _n, label in d._tree.children[root]]
    assert labels == ["Acid Jazz", "Rock"]
    assert _child_data(d, root)[0]["kind"] == "genre"


def test_add_children_tunein_folders_and_stations() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "tunein", "payload": ""})
    d._add_children(
        root,
        "tunein",
        [
            TuneInResult(guide_id="", title="Music", is_station=False, browse_url="http://x?c=music"),
            TuneInResult(guide_id="s9", title="Jazz FM", is_station=True),
        ],
    )
    kinds = [dat["kind"] for dat in _child_data(d, root)]
    assert kinds == ["tunein", "tunein-station"]


def test_play_selected_routes_station_and_tunein() -> None:
    d = _dialog()
    played: list = []
    d._controller = SimpleNamespace(
        play_station=lambda s: played.append(s.name),
        state=SimpleNamespace(station=None, state=None),
        stop=lambda: None,
    )
    d._is_playing = lambda s: False
    # a resolved station plays directly
    node = _Node()
    d._tree._data[node] = {"kind": "station", "station": RadioStation(name="WJAZZ", stream_url="s")}
    d._tree._selection = node
    d._play_selected()
    assert played == ["WJAZZ"]
    # a TuneIn station goes through resolve
    resolved: list = []
    d._play_tunein = lambda gid, title: resolved.append((gid, title))
    tnode = _Node()
    d._tree._data[tnode] = {"kind": "tunein-station", "guide_id": "s7", "title": "WABC"}
    d._tree._selection = tnode
    d._play_selected()
    assert resolved == [("s7", "WABC")]


def test_toggle_favorite_adds_and_removes() -> None:
    d = _dialog()
    station = RadioStation(name="WJAZZ", stream_url="https://x/s", station_uuid="u1")
    node = _Node()
    d._tree._data[node] = {"kind": "station", "station": station}
    d._tree._selection = node
    d._toggle_favorite()
    assert d._favorites.contains(station)
    d._toggle_favorite()
    assert not d._favorites.contains(station)
