"""Play Random commands: favorites, the open list, and the fallback."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.radio.favorites import FavoriteStation
from quill.core.radio.models import RadioStation
from quill.ui.radio import play_random_ui as ui


def _fav(name: str) -> FavoriteStation:
    return FavoriteStation(RadioStation(name=name, stream_url=f"http://x/{name}"))


class _Favorites:
    def __init__(self, favs: list[FavoriteStation]) -> None:
        self._favs = favs

    def favorites_in_display_order(self, *_a: object) -> list[FavoriteStation]:
        return list(self._favs)


class _Host:
    def __init__(self, favs: list[FavoriteStation]) -> None:
        self._radio_favorites = _Favorites(favs)
        self._radio_history = SimpleNamespace(favorites_sort="manual", folder_sort_orders={})
        self.played: list[str] = []
        self.said: list[str] = []
        self._radio_controller = SimpleNamespace(play_station=lambda s: self.played.append(s.name))

    def _announce(self, text: str, **_k: object) -> None:
        self.said.append(text)


@pytest.fixture(autouse=True)
def _clean_sources() -> None:
    ui._sources.clear()


def test_favorite_never_repeats_and_says_where_from() -> None:
    host = _Host([_fav("A"), _fav("B"), _fav("C")])
    for _ in range(12):
        ui.play_random_favorite(host)
    assert all(a != b for a, b in zip(host.played, host.played[1:], strict=False))
    assert host.said[0].endswith("picked at random from 3 favorites.")


def test_no_favorites_says_so_and_plays_nothing() -> None:
    host = _Host([])
    assert ui.play_random_favorite(host) is False
    assert host.played == [] and "no favorites" in host.said[0]


def test_places_are_never_picked() -> None:
    from quill.core.radio.favorites import place_station

    host = _Host([FavoriteStation(place_station("browse:x", "Show")), _fav("Real")])
    for _ in range(5):
        ui.play_random_favorite(host)
    assert set(host.played) == {"Real"}


def test_station_uses_the_open_list_else_favorites() -> None:
    host = _Host([_fav("Fav")])
    ui.play_random_station(host)
    assert host.played == ["Fav"]

    class _Window:
        def random_pool(self) -> tuple[str, list[RadioStation]]:
            return "stations", [RadioStation(name="Listed", stream_url="http://l/1")]

    window = _Window()
    ui.register_source(window)
    ui.play_random_station(host)
    assert host.played[-1] == "Listed"
    assert "in the list" in host.said[-1]


def test_streams_pool_follows_shown_order() -> None:
    from quill.core.radio.page_links import PageStreamCandidate

    cands = [PageStreamCandidate(url=f"http://s/{i}", reason="x") for i in range(3)]
    pool, stations = ui.streams_pool(cands, [2, 0], "Page")
    assert pool == "streams"
    assert [s.stream_url for s in stations] == ["http://s/2", "http://s/0"]
