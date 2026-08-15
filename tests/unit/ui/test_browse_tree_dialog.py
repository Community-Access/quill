"""Unified Browse Stations tree -- row rendering, play routing, favorites.

Drives the wx-heavy dialog against a fake tree (the real one needs a wx.App to
construct). What each *source* produces is tested in
``tests/unit/core/radio/test_browse_sources.py``; what is tested here is the
half that only the dialog can do -- turning BrowseNodes into rows, and routing
an activation to playback, resolution, or expansion.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.radio import browse_sources
from quill.core.radio.browse_nodes import folder, lazy_leaf, leaf
from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.core.radio.models import RadioStation
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

    def GetChildrenCount(self, node, recursive=True):  # noqa: N802
        return len(self.children.get(node, []))

    def GetFirstChild(self, node):  # noqa: N802
        kids = self.children.get(node, [])
        return (kids[0][0] if kids else _Node(False)), 0

    def GetNextChild(self, node, cookie):  # noqa: N802
        kids = self.children.get(node, [])
        index = cookie + 1
        return (kids[index][0] if index < len(kids) else _Node(False)), index

    def GetItemText(self, node):  # noqa: N802
        for kids in self.children.values():
            for child, label in kids:
                if child is node:
                    return label
        return ""

    def SelectItem(self, node):  # noqa: N802
        self._selection = node

    def SetFocus(self):  # noqa: N802
        return None

    def GetSelection(self):  # noqa: N802
        return self._selection


def _dialog(*, safe_mode: bool = False) -> Any:
    d = BrowseTreeDialog.__new__(BrowseTreeDialog)
    d._tree = _FakeTree()
    d._announced: list[str] = []
    d._announce = d._announced.append
    d._favorites = RadioFavoritesStore(favorites=[])
    d._safe_mode = safe_mode
    d._details = SimpleNamespace(SetValue=lambda _v: None)
    d._play_btn = SimpleNamespace(Enable=lambda _v: None, SetLabel=lambda _l: None)
    d._favorite_btn = SimpleNamespace(Enable=lambda _v: None, SetLabel=lambda _l: None)
    d._on_favorites_changed = lambda: None
    return d


def _child_data(d, node):
    return [d._tree.GetItemData(n) for n, _label in d._tree.children.get(node, [])]


def _labels(d, node):
    return [label for _n, label in d._tree.children.get(node, [])]


def _station(name: str = "Test FM", url: str = "https://a.example/s") -> RadioStation:
    return RadioStation(name=name, stream_url=url)


# --- rendering rows ------------------------------------------------------------


def test_a_leaf_becomes_a_playable_row() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "acb", "label": "ACB Media"})
    d._add_children(root, [leaf(_station("ACB 1"))])
    data = _child_data(d, root)[0]
    assert data["station"].name == "ACB 1"
    assert not data.get("resolve_lazily")


def test_a_folder_becomes_an_openable_row_with_a_loading_placeholder() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "xiph", "label": "Xiph"})
    d._add_children(root, [folder("xiph:jazz", "Jazz")])
    child_node = d._tree.children[root][0][0]
    assert _child_data(d, root)[0]["node_id"] == "xiph:jazz"
    assert _labels(d, child_node) == ["Loading..."], "a folder must look expandable"


def test_a_child_count_is_shown_before_the_folder_is_opened() -> None:
    # The whole point of child_count: decide whether to spend the wait.
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "iheart", "label": "iHeart"})
    d._add_children(root, [folder("iheart:1310", "Rock", child_count=214)])
    assert "214" in _labels(d, root)[0]


def test_a_note_is_shown_so_nothing_surprises_after_enter() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "tunein", "label": "TuneIn"})
    d._add_children(root, [lazy_leaf("tuneinstation:s1", "BBC", note="resolves when you play it")])
    assert "resolves when you play it" in _labels(d, root)[0]


# --- the empty-branch message --------------------------------------------------


def test_an_empty_internet_branch_says_it_might_be_unreachable() -> None:
    # Reading "could not reach the source" as "this folder is empty" is how a
    # listener concludes a working source is broken, or the reverse.
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "soma", "label": "SomaFM"})
    d._add_children(root, [])
    assert "could not be reached" in d._announced[-1]


def test_an_empty_local_branch_just_says_it_is_empty() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "networks", "label": "Networks"})
    d._add_children(root, [])
    assert "could not be reached" not in d._announced[-1]


def test_safe_mode_says_so_rather_than_showing_an_empty_folder() -> None:
    d = _dialog(safe_mode=True)
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "tunein", "label": "TuneIn"})
    d._add_children(root, [])
    assert "Safe Mode" in d._announced[-1]


def test_a_populated_branch_announces_its_count() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "acb", "label": "ACB Media"})
    d._add_children(root, [leaf(_station("A")), leaf(_station("B", "https://a/2"))])
    assert d._announced[-1] == "2 items."


# --- play routing --------------------------------------------------------------


class _Controller:
    def __init__(self) -> None:
        self.played: list[RadioStation] = []
        self.stopped = 0
        self.state = SimpleNamespace(station=None, state=None, volume_percent=100, muted=False)

    def play_station(self, station):
        self.played.append(station)

    def stop(self):
        self.stopped += 1


def test_activating_a_station_leaf_plays_it() -> None:
    d = _dialog()
    d._controller = _Controller()
    station = _station("Jazz FM")
    d._tree._selection = _Node()
    d._tree.SetItemData(
        d._tree._selection, {"node_id": "x", "label": "Jazz FM", "station": station}
    )
    d._play_selected()
    assert [s.name for s in d._controller.played] == ["Jazz FM"]


def test_activating_a_lazy_leaf_resolves_first_then_plays(monkeypatch) -> None:
    d = _dialog()
    d._controller = _Controller()
    submitted: list = []
    d._task_manager = SimpleNamespace(
        submit=lambda op, work, on_success=None, on_failure=None: submitted.append((
            work,
            on_success,
        ))
    )
    monkeypatch.setattr(
        browse_sources,
        "resolve",
        lambda node_id, **_kw: RadioStation(name="", stream_url="https://cdn/bbc.mp3"),
    )
    d._tree._selection = _Node()
    d._tree.SetItemData(
        d._tree._selection,
        {"node_id": "tuneinstation:s1", "label": "BBC", "station": None, "resolve_lazily": True},
    )
    d._play_selected()
    assert submitted, "a lazy leaf must resolve off the UI thread"
    work, on_success = submitted[0]
    on_success("op", work())
    assert [s.stream_url for s in d._controller.played] == ["https://cdn/bbc.mp3"]
    assert d._controller.played[0].name == "BBC", "the row's label names the resolved station"


def test_a_failed_resolve_says_so_and_plays_nothing(monkeypatch) -> None:
    d = _dialog()
    d._controller = _Controller()
    submitted: list = []
    d._task_manager = SimpleNamespace(
        submit=lambda op, work, on_success=None, on_failure=None: submitted.append((
            work,
            on_success,
        ))
    )
    monkeypatch.setattr(browse_sources, "resolve", lambda node_id, **_kw: None)
    d._tree._selection = _Node()
    d._tree.SetItemData(
        d._tree._selection,
        {"node_id": "tuneinstation:s1", "label": "BBC", "station": None, "resolve_lazily": True},
    )
    d._play_selected()
    work, on_success = submitted[0]
    on_success("op", work())
    assert d._controller.played == []
    assert "Could not play BBC." in d._announced


def test_activating_a_folder_plays_nothing() -> None:
    d = _dialog()
    d._controller = _Controller()
    d._tree._selection = _Node()
    d._tree.SetItemData(d._tree._selection, {"node_id": "xiph", "label": "Xiph", "loaded": False})
    d._play_selected()
    assert d._controller.played == []


# --- favorites -----------------------------------------------------------------


def test_toggle_favorite_adds_and_removes() -> None:
    d = _dialog()
    station = _station("Keeper")
    d._tree._selection = _Node()
    d._tree.SetItemData(d._tree._selection, {"node_id": "x", "label": "Keeper", "station": station})
    d._toggle_favorite()
    assert d._favorites.contains(station)
    d._toggle_favorite()
    assert not d._favorites.contains(station)


def test_favorites_branch_lists_unfiled_stations_then_folders() -> None:
    d = _dialog()
    d._favorites = RadioFavoritesStore(
        favorites=[
            FavoriteStation(station=_station("Unfiled", "https://a/1")),
            FavoriteStation(station=_station("Filed", "https://a/2"), folder="News"),
        ]
    )
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "favorites", "label": "Favorites"})
    d._add_favorites(root)
    labels = _labels(d, root)
    assert labels[0] == "Unfiled"
    assert "News" in labels[-1]


def test_an_empty_favorites_branch_explains_how_to_fill_it() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "favorites", "label": "Favorites"})
    d._add_favorites(root)
    assert "No favorites yet" in _labels(d, root)[0]


def test_favorite_folder_adds_all_loaded_stations() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "acb", "label": "ACB Media"})
    d._add_children(root, [leaf(_station("A")), leaf(_station("B", "https://a/2"))])
    d._favorite_folder(root)
    assert len(d._favorites.favorites) == 2
    assert "Added 2 stations to Favorites." in d._announced


def test_favorite_folder_on_an_unopened_folder_asks_you_to_open_it() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "xiph", "label": "Xiph"})
    d._add_children(root, [folder("xiph:jazz", "Jazz")])
    d._favorite_folder(root)
    assert "Open the folder first" in d._announced[-1]
