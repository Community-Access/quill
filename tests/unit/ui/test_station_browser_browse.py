"""Browse-a-source-without-searching in the station browser (Kelly's request).

Drives the new category/genre logic against fakes (the dialog needs a live
wx.App to fully construct), verifying the routing and genre-picker population
headlessly. The source catalogs themselves (SomaFM, NFB, Community M3U) are
unit-tested in their own core modules.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.ui.radio.station_browser_dialog import (
    _CATEGORIES,
    _M3U_GENRES,
    _POPULAR,
    _SOMAFM,
    StationBrowserDialog,
)


class _FakeChoice:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.enabled = False
        self.selection = -1

    def Set(self, items: list[str]) -> None:  # noqa: N802 - wx shape
        self.items = list(items)

    def Enable(self, value: bool) -> None:  # noqa: N802
        self.enabled = value

    def GetSelection(self) -> int:  # noqa: N802
        return self.selection

    def GetCount(self) -> int:  # noqa: N802
        return len(self.items)


class _FakeStatus:
    def __init__(self) -> None:
        self.label = ""

    def SetLabel(self, text: str) -> None:  # noqa: N802
        self.label = text


def _dialog() -> Any:
    d = StationBrowserDialog.__new__(StationBrowserDialog)
    d._safe_mode = False
    d._genre_ctrl = _FakeChoice()
    d._genre_slugs = []
    d._status = _FakeStatus()
    d._announced: list[str] = []
    d._announce = d._announced.append
    d._filled: list[tuple[list, str]] = []
    d._fill_results = lambda stations, *, status: d._filled.append((stations, status))
    d._category_list = SimpleNamespace(
        GetSelection=lambda: _CATEGORIES.index(_M3U_GENRES),
        SetSelection=lambda i: None,
    )
    d._wx = SimpleNamespace(NOT_FOUND=-1)
    d._set_tunein_view = lambda show: None  # tree/list swap tested separately
    return d
    assert d._genre_ctrl.enabled is False  # genre picker only for Music Genres


def test_popular_and_somafm_categories_browse_async() -> None:
    # Both fetch off-thread via _browse_async (no query); stub it to capture.
    for category, needle in ((_POPULAR, "popular"), (_SOMAFM, "SomaFM")):
        d = _dialog()
        captured: dict = {}
        d._browse_async = lambda fetch, *, loading, done, error, _c=captured: _c.update(
            loading=loading, error=error
        )
        d._show_category(category)
        assert needle.lower() in (captured["loading"] + captured["error"]).lower(), category
        assert d._genre_ctrl.enabled is False  # genre picker only for Music Genres


def test_apply_genres_m3u_populates_and_credits_junguler() -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._apply_genres(["acid_jazz", "rock"])
    assert d._genre_slugs == ["acid_jazz", "rock"]
    assert d._genre_ctrl.items == ["Acid Jazz", "Rock"]  # humanized labels
    assert d._genre_ctrl.enabled is True
    assert "junguler" in d._status.label  # attribution to the catalog author


def test_apply_genres_xiph_credits_the_directory() -> None:
    from quill.core.radio import xiph

    d = _dialog()
    d._genre_source = xiph
    d._apply_genres(["Jazz"])
    assert d._genre_ctrl.items == ["Jazz"]
    assert "Xiph" in d._status.label or "Icecast" in d._status.label


def test_apply_genres_empty_reports_and_disables() -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._apply_genres([])
    assert d._genre_ctrl.enabled is False
    assert "Refresh" in d._status.label


def test_on_genre_selected_browses_that_genre(monkeypatch) -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._genre_slugs = ["jazz", "rock"]
    d._genre_ctrl.selection = 1  # "rock"
    captured: dict = {}
    d._browse_async = lambda fetch, *, loading, done, error: captured.update(
        loading=loading, done1=done(1), error=error
    )
    d._on_genre_selected(None)
    assert "Rock" in captured["loading"]
    assert "Rock station" in captured["done1"]
    assert "Rock" in captured["error"]


def test_on_genre_selected_ignores_no_selection() -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._genre_slugs = ["jazz"]
    d._genre_ctrl.selection = -1
    d._browse_async = lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not browse"))
    d._on_genre_selected(None)  # no-op, no exception


# --- TuneIn tree (folders lazily expand; a station resolves and plays) -------


class _TNode:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok

    def IsOk(self) -> bool:  # noqa: N802 - wx shape
        return self._ok


class _FakeTree:
    def __init__(self) -> None:
        self._data: dict = {}
        self.children: dict = {}
        self._shown = True
        self._selection = _TNode(False)

    def IsShown(self):  # noqa: N802
        return self._shown

    def AddRoot(self, _label):  # noqa: N802
        return _TNode()

    def AppendItem(self, parent, label):  # noqa: N802
        node = _TNode()
        self.children.setdefault(parent, []).append((node, label))
        return node

    def SetItemData(self, node, data):  # noqa: N802
        self._data[node] = data

    def GetItemData(self, node):  # noqa: N802
        return self._data.get(node)

    def DeleteChildren(self, node):  # noqa: N802
        self.children[node] = []

    def GetSelection(self):  # noqa: N802
        return self._selection

    def GetFirstChild(self, node):  # noqa: N802
        kids = self.children.get(node, [])
        return (kids[0][0] if kids else _TNode(False), None)

    def SelectItem(self, node):  # noqa: N802
        self._selection = node

    def SetFocus(self):  # noqa: N802
        pass


def _tree_dialog() -> Any:
    d = StationBrowserDialog.__new__(StationBrowserDialog)
    d._tunein_tree = _FakeTree()
    d._status = _FakeStatus()
    d._announced = []
    d._announce = d._announced.append
    d._details = SimpleNamespace(SetValue=lambda _v: None)
    d._play_btn = SimpleNamespace(Enable=lambda _v: None)
    d._favorite_btn = SimpleNamespace(Enable=lambda _v: None)
    return d


def test_add_tunein_children_builds_folders_and_station_leaves() -> None:
    from quill.core.radio.tunein import TuneInResult

    d = _tree_dialog()
    root = d._tunein_tree.AddRoot("TuneIn")
    d._tunein_root = root
    d._add_tunein_children(
        root,
        [
            TuneInResult(guide_id="c2", title="Jazz", is_station=False),
            TuneInResult(guide_id="s9", title="Jazz FM", is_station=True),
        ],
    )
    labels = [label for _node, label in d._tunein_tree.children[root]]
    assert any("[folder]" in label for label in labels)  # folder marked
    assert "Jazz FM" in labels  # station leaf
    assert "1 folder" in d._status.label and "1 station" in d._status.label


def test_tunein_activate_station_plays_folder_expands() -> None:
    d = _tree_dialog()
    played: list = []
    d._play_tunein_station = lambda gid, title: played.append((gid, title))
    skipped: list = []

    station_node = _TNode()
    d._tunein_tree._data[station_node] = {"kind": "station", "guide_id": "s1", "title": "Jazz FM"}
    d._on_tunein_activated(SimpleNamespace(GetItem=lambda: station_node, Skip=lambda: None))
    assert played == [("s1", "Jazz FM")]

    folder_node = _TNode()
    d._tunein_tree._data[folder_node] = {"kind": "category", "guide_id": "c1", "title": "Music"}
    d._on_tunein_activated(
        SimpleNamespace(GetItem=lambda: folder_node, Skip=lambda: skipped.append(True))
    )
    assert skipped == [True]  # a folder toggles open via the default handler


def test_tunein_folder_lazy_loads_once() -> None:
    d = _tree_dialog()
    fetched: list = []
    d._fetch_tunein_children = lambda node, gid: fetched.append(gid)
    node = _TNode()
    data = {"kind": "category", "guide_id": "c5", "loaded": False, "title": "Music"}
    d._tunein_tree._data[node] = data

    d._on_tunein_expanding(SimpleNamespace(GetItem=lambda: node))
    assert fetched == ["c5"] and data["loaded"] is True
    d._on_tunein_expanding(SimpleNamespace(GetItem=lambda: node))  # again -> no refetch
    assert fetched == ["c5"]


def test_play_button_on_tree_plays_selected_station() -> None:
    d = _tree_dialog()
    played: list = []
    d._play_tunein_station = lambda gid, title: played.append((gid, title))
    node = _TNode()
    d._tunein_tree._data[node] = {"kind": "station", "guide_id": "s7", "title": "WJAZZ"}
    d._tunein_tree._selection = node
    d._on_play(None)
    assert played == [("s7", "WJAZZ")]


def test_play_button_on_tree_folder_does_nothing() -> None:
    d = _tree_dialog()
    played: list = []
    d._play_tunein_station = lambda gid, title: played.append((gid, title))
    node = _TNode()
    d._tunein_tree._data[node] = {"kind": "category", "guide_id": "c1", "title": "Music"}
    d._tunein_tree._selection = node
    d._on_play(None)
    assert played == []


def test_on_refresh_routes_to_genres_when_music_genres_active() -> None:
    d = _dialog()  # category_list reports Music Genres
    calls: list[str] = []
    d._load_genres = lambda: calls.append("genres")
    d._on_refresh_directory = lambda _e: calls.append("iheart")
    d._on_refresh(None)
    assert calls == ["genres"]
    assert d._genre_source.CATEGORY_LABEL == "Community M3U"  # source set for the refresh


def test_on_refresh_routes_to_iheart_for_other_categories() -> None:
    d = _dialog()
    d._category_list = SimpleNamespace(GetSelection=lambda: _CATEGORIES.index("Search Results"))
    calls: list[str] = []
    d._load_genres = lambda: calls.append("genres")
    d._on_refresh_directory = lambda _e: calls.append("iheart")
    d._on_refresh(None)
    assert calls == ["iheart"]
