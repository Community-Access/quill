"""11.6: adding something you already have says so, and goes to it.

The bug this closes was quiet: ``RadioFavoritesStore.add`` returned ``None``
whether or not it had added anything, so every caller announced "Added WQXR
to Favorites" over a station that was already there.
"""

from __future__ import annotations

from quill.core import duplicate_add
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation


def _station(name: str = "WQXR", url: str = "https://example.com/wqxr") -> RadioStation:
    return RadioStation(name=name, stream_url=url)


def test_the_store_now_answers_whether_it_added_anything() -> None:
    store = RadioFavoritesStore()
    assert store.add(_station()) is True
    assert store.add(_station()) is False, "the second add is the bug 11.6 is about"
    assert len(store.favorites) == 1


def test_a_different_station_is_still_added() -> None:
    store = RadioFavoritesStore()
    assert store.add(_station()) is True
    assert store.add(_station("KUSC", "https://example.com/kusc")) is True
    assert len(store.favorites) == 2


def test_the_sentence_names_the_thing_and_says_where_it_went() -> None:
    assert duplicate_add.already_have("station", "WQXR", moved=True) == (
        "WQXR is already in your favorites. Moving to it."
    )
    assert duplicate_add.already_have("podcast", "The Daily", moved=True) == (
        "You already follow The Daily. Moving to it."
    )


def test_not_moving_is_said_rather_than_implied() -> None:
    """ "Nothing was added" is the honest tail when the cursor did not move."""
    assert duplicate_add.already_have("station", "WQXR") == (
        "WQXR is already in your favorites. Nothing was added."
    )


def test_each_kind_names_the_list_to_go_and_look_in() -> None:
    assert "follow" in duplicate_add.already_have("podcast", "X")
    assert "favorites" in duplicate_add.already_have("station", "X")
    assert "places" in duplicate_add.already_have("place", "X")
    assert "folder" in duplicate_add.already_have("folder", "X")


def test_an_unknown_kind_still_says_something_true() -> None:
    assert duplicate_add.already_have("gizmo", "X") == "You already have X. Nothing was added."


def test_a_nameless_thing_does_not_produce_an_empty_sentence() -> None:
    assert duplicate_add.already_have("station", "   ") == (
        "that is already in your favorites. Nothing was added."
    )


def test_the_success_half_reads_as_the_same_voice() -> None:
    assert duplicate_add.added("podcast", "The Daily") == "Now following The Daily."
    assert duplicate_add.added("station", "WQXR") == "Added WQXR to your favorites."
    assert duplicate_add.added("place", "LibriVox") == "Saved LibriVox to your places."
