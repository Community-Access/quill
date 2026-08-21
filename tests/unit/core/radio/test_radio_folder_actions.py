"""A favorites folder as a place you listen from.

The cases worth pinning are the two that decide whether the feature is right
rather than merely present: a folder means its whole subtree, and a folder name
must not capture a sibling that happens to start with the same letters.
"""

from __future__ import annotations

import random
from typing import Any

from quill.core.radio import folder_actions
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation


def _store(*rows: tuple[str, str]) -> RadioFavoritesStore:
    store = RadioFavoritesStore()
    for name, folder in rows:
        station = RadioStation(name=name, stream_url=f"https://example.com/{name.lower()}")
        store.add(station, folder=folder)
    return store


def test_a_folder_means_its_whole_subtree() -> None:
    store = _store(("Alpha", "News"), ("Beta", "News/Local"), ("Gamma", "Music"))
    names = [row.display_label for row in folder_actions.stations_in_folder(store, "News")]
    assert names == ["Alpha", "Beta"]


def test_a_folder_name_does_not_capture_a_sibling_it_prefixes() -> None:
    """ "News" must not swallow "Newsroom" -- the separator has to be there."""
    store = _store(("Alpha", "News"), ("Beta", "Newsroom"))
    names = [row.display_label for row in folder_actions.stations_in_folder(store, "News")]
    assert names == ["Alpha"]


def test_subfolders_can_be_excluded_when_that_is_what_was_asked() -> None:
    store = _store(("Alpha", "News"), ("Beta", "News/Local"))
    names = [
        row.display_label
        for row in folder_actions.stations_in_folder(store, "News", include_subfolders=False)
    ]
    assert names == ["Alpha"]


def test_the_top_level_is_everything() -> None:
    store = _store(("Alpha", "News"), ("Beta", ""))
    assert len(folder_actions.stations_in_folder(store, "")) == 2


def test_shuffle_is_one_fixed_permutation() -> None:
    """A shuffle you can walk backwards through; not a re-roll on every step."""
    store = _store(*[(f"S{index}", "News") for index in range(8)])
    rows = folder_actions.stations_in_folder(store, "News")
    first = folder_actions.shuffled(rows, rng=random.Random(7))
    second = folder_actions.shuffled(rows, rng=random.Random(7))
    assert [row.display_label for row in first] == [row.display_label for row in second]
    assert sorted(row.display_label for row in first) == sorted(row.display_label for row in rows)


def test_a_folder_row_says_what_it_holds() -> None:
    store = _store(("Alpha", "News"), ("Beta", "News/Local"))
    assert folder_actions.describe_folder(store, "News") == "News, folder, 2 stations"
    assert folder_actions.describe_folder(store, "News/Local") == "Local, folder, 1 station"


# -- the queue ---------------------------------------------------------------


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


class _Controller:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play_station(self, station: Any) -> None:
        self.played.append(str(getattr(station, "name", "")))


def test_playing_a_folder_starts_it_and_remembers_the_rest() -> None:
    from quill.ui.radio import favorite_folder_actions

    store = _store(("Alpha", "News"), ("Beta", "News"), ("Gamma", "Music"))
    host, controller = _Host(), _Controller()
    assert favorite_folder_actions.play_folder(host, "News", store=store, controller=controller)
    assert controller.played == ["Alpha"]
    assert "2 stations" in host.said[0]
    assert favorite_folder_actions.queue_summary(host) == "1 of 2 in News"

    assert favorite_folder_actions.next_in_folder(host, controller)
    assert controller.played == ["Alpha", "Beta"]
    assert favorite_folder_actions.queue_summary(host) == "2 of 2 in News"


def test_the_end_of_a_folder_says_so_rather_than_wrapping() -> None:
    """Looping silently is how somebody hears a station twice and cannot say why."""
    from quill.ui.radio import favorite_folder_actions

    store = _store(("Alpha", "News"))
    host, controller = _Host(), _Controller()
    favorite_folder_actions.play_folder(host, "News", store=store, controller=controller)
    assert not favorite_folder_actions.next_in_folder(host, controller)
    assert "end of the folder" in host.said[-1]
    assert not favorite_folder_actions.previous_in_folder(host, controller)
    assert "start of the folder" in host.said[-1]
    assert controller.played == ["Alpha"]


def test_stepping_with_no_folder_playing_says_so() -> None:
    from quill.ui.radio import favorite_folder_actions

    host, controller = _Host(), _Controller()
    assert not favorite_folder_actions.next_in_folder(host, controller)
    assert "Play a folder first" in host.said[-1]


def test_a_folder_with_nothing_playable_is_refused_out_loud() -> None:
    from quill.ui.radio import favorite_folder_actions

    store = RadioFavoritesStore()
    store.add(RadioStation(name="A place", stream_url=""), folder="Places")
    host, controller = _Host(), _Controller()
    assert not favorite_folder_actions.play_folder(
        host, "Places", store=store, controller=controller
    )
    assert "nothing to play" in host.said[-1]
    assert controller.played == []
