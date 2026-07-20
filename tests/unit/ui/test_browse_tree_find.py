"""Browse Stations -- "Find in this folder": recursive, bounded subtree search.

Characterizes the pure collector (``_find_matches`` / ``_collect_matches``)
against a fake ``_fetch_children``, so the scoped search logic is covered
without a wx.App.
"""

from __future__ import annotations

from quill.core.radio.iheart import IHeartGenre
from quill.core.radio.models import RadioStation
from tests.unit.ui.test_browse_tree_dialog import _dialog


def _st(name: str) -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://s/{name}", source="iHeart")


def test_find_filters_a_flat_station_folder() -> None:
    d = _dialog()
    d._fetch_children = lambda kind, payload: {  # type: ignore[method-assign]
        "stations": [_st("Smooth Jazz"), _st("Rock 101"), _st("Jazz24")],
    }[kind]
    matches, capped = d._find_matches("stations", "soma", "jazz")
    assert not capped
    assert sorted(m["station"].name for m in matches) == ["Jazz24", "Smooth Jazz"]
    assert all(m["kind"] == "station" for m in matches)


def test_find_recurses_iheart_genres_from_the_root() -> None:
    d = _dialog()
    genre_stations = {
        5: [_st("Country Jazz Mix"), _st("Pure Country")],
        16: [_st("Jazz FM"), _st("Top 40")],
    }

    def fake_fetch(kind, payload):
        if kind == "iheart":
            return [IHeartGenre(5, "Country"), IHeartGenre(16, "Pop")]
        if kind == "iheart-genre":
            return genre_stations[payload]
        return []

    d._fetch_children = fake_fetch  # type: ignore[method-assign]
    matches, capped = d._find_matches("iheart", None, "jazz")
    assert not capped
    # Matches gathered from every genre under the iHeart root.
    assert sorted(m["station"].name for m in matches) == ["Country Jazz Mix", "Jazz FM"]


def test_find_scopes_to_one_genre_only() -> None:
    d = _dialog()
    # Searching one genre fetches just that genre's stations (no iHeart root walk).
    calls: list[tuple] = []

    def fake_fetch(kind, payload):
        calls.append((kind, payload))
        return [_st("Jazz FM"), _st("Blues Hour")]

    d._fetch_children = fake_fetch  # type: ignore[method-assign]
    matches, _capped = d._find_matches("iheart-genre", 5, "jazz")
    assert [m["station"].name for m in matches] == ["Jazz FM"]
    assert calls == [("iheart-genre", 5)]  # only the one genre was fetched


def test_find_in_favorites_uses_local_data() -> None:
    d = _dialog()
    d._favorites.add(_st("Jazz Favorite"))
    d._favorites.add(_st("Rock Favorite"))
    matches, capped = d._find_matches("favorites", None, "jazz")
    assert not capped
    assert [m["station"].name for m in matches] == ["Jazz Favorite"]


def test_find_no_match_returns_empty() -> None:
    d = _dialog()
    d._fetch_children = lambda kind, payload: [_st("Rock 101")]  # type: ignore[method-assign]
    matches, capped = d._find_matches("stations", "soma", "jazz")
    assert matches == []
    assert not capped
