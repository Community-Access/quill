"""Quick-play favorites logic (quill.ui.radio.quick_play)."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.radio import quick_play


class _Fav:
    def __init__(self, name: str) -> None:
        self.station = f"station-{name}"
        self.display_label = name


class _Store:
    def __init__(self, favs: list[_Fav]) -> None:
        self._favs = favs

    def favorites_in_display_order(self, _sort: object, _folder_sorts: object) -> list[_Fav]:
        return self._favs


def _history() -> SimpleNamespace:
    return SimpleNamespace(favorites_sort=None, folder_sort_orders=None)


def test_plays_the_nth_favorite() -> None:
    played: list[str] = []
    announced: list[str] = []
    store = _Store([_Fav("A"), _Fav("B"), _Fav("C")])
    quick_play.play_favorite_slot(
        2,
        favorites=store,
        history=_history(),
        controller=SimpleNamespace(play_station=played.append),
        announce=announced.append,
    )
    assert played == ["station-B"]
    assert announced == ["Playing favorite 2: B."]


def test_empty_slot_announces_count_and_plays_nothing() -> None:
    played: list[str] = []
    announced: list[str] = []
    store = _Store([_Fav("A")])
    quick_play.play_favorite_slot(
        5,
        favorites=store,
        history=_history(),
        controller=SimpleNamespace(play_station=played.append),
        announce=announced.append,
    )
    assert played == []
    assert announced == ["No favorite in slot 5. You have 1 favorites."]
