"""Browse Stations -- iHeart source: Genre -> A-Z -> Station tree.

Characterizes the module-level grouping helper and drives ``_add_children``
against the fake tree (no wx.App), proving the "iheart" genre folders,
"iheart-genre" A-Z letter folders, and "iheart-letter" station leaves match
the dialog's node-shape conventions.
"""

from __future__ import annotations

from quill.core.radio import iheart
from quill.core.radio.iheart import IHeartGenre
from quill.core.radio.models import RadioStation
from quill.ui.radio.browse_tree_dialog import _iheart_letter_groups
from tests.unit.ui.test_browse_tree_dialog import _child_data, _dialog, _Node


def _st(name: str) -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://s/{name}", source="iHeart")


def test_iheart_letter_groups_buckets_and_orders() -> None:
    groups = _iheart_letter_groups([
        _st("Alt 92.3"),
        _st("WABC"),
        _st("acid jazz"),
        _st("933 FLZ"),
        _st("!Weird"),
    ])
    labels = [label for label, _stations in groups]
    # Letters A-Z first (case-insensitive), then a digits bucket, then other.
    assert labels == ["A", "W", "0-9", "#"]
    a_bucket = dict(groups)["A"]
    assert {s.name for s in a_bucket} == {"Alt 92.3", "acid jazz"}


def test_fetch_children_iheart_loads_genres(monkeypatch) -> None:
    monkeypatch.setattr(
        iheart, "fetch_genres", lambda **_k: [IHeartGenre(5, "Country"), IHeartGenre(16, "Pop")]
    )
    d = _dialog()
    d._safe_mode = False
    genres = d._fetch_children("iheart", None)
    assert [g.name for g in genres] == ["Country", "Pop"]


def test_fetch_children_iheart_genre_loads_stations(monkeypatch) -> None:
    monkeypatch.setattr(
        iheart, "fetch_genre_stations", lambda gid, **_k: [_st("WABC"), _st("KBCO")]
    )
    d = _dialog()
    d._safe_mode = False
    stations = d._fetch_children("iheart-genre", 5)
    assert {s.name for s in stations} == {"WABC", "KBCO"}


def test_fetch_children_iheart_letter_is_pure_payload() -> None:
    d = _dialog()
    d._safe_mode = False
    payload = [_st("WABC")]
    # A letter node just re-emits its already-fetched stations (no network).
    assert d._fetch_children("iheart-letter", payload) == payload


def test_add_children_iheart_makes_genre_folders() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "iheart", "payload": None})
    d._add_children(root, "iheart", [IHeartGenre(5, "Country"), IHeartGenre(16, "Pop")])
    labels = [label for _n, label in d._tree.children[root]]
    assert labels == ["Country", "Pop"]
    data = _child_data(d, root)
    assert data[0]["kind"] == "iheart-genre"
    assert data[0]["payload"] == 5


def test_add_children_iheart_genre_makes_letter_folders() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "iheart-genre", "payload": 5})
    d._add_children(root, "iheart-genre", [_st("WABC"), _st("acid jazz")])
    labels = [label for _n, label in d._tree.children[root]]
    assert labels == ["A", "W"]
    data = _child_data(d, root)
    assert data[0]["kind"] == "iheart-letter"
    assert {s.name for s in data[0]["payload"]} == {"acid jazz"}


def test_add_children_iheart_letter_makes_station_leaves() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"kind": "iheart-letter", "payload": [_st("WABC")]})
    d._add_children(root, "iheart-letter", [_st("WABC")])
    data = _child_data(d, root)
    assert data[0]["kind"] == "station"
    assert data[0]["station"].source == "iHeart"
