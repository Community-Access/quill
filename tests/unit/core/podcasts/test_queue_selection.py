"""Group actions on a queue selection (ear.md R5).

Two invariants run through every test: a selection keeps its own order, and
everything outside it keeps its order too. A group action touches the block and
leaves the run around it alone.
"""

from __future__ import annotations

import random

from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.queue_selection import (
    move_selection,
    shuffle_selection,
    sort_selection_by_date,
)
from quill.core.podcasts.subscriptions import PodcastLibrary

#: guid -> published date, deliberately not in guid order so a date sort and an
#: alphabetical sort cannot be confused for each other.
DATES = {
    "a": "2026-03-01T00:00:00",
    "b": "2026-01-01T00:00:00",
    "c": "2026-05-01T00:00:00",
    "d": "2026-02-01T00:00:00",
    "e": "2026-04-01T00:00:00",
}


def _library(*guids: str) -> PodcastLibrary:
    show = PodcastShow(
        id="s1",
        title="Main Menu",
        feed_url="https://e/f.xml",
        episodes=[
            PodcastEpisode(
                guid=guid,
                title=f"Episode {guid}",
                audio_url=f"https://e/{guid}.mp3",
                published=DATES.get(guid, "2026-06-01T00:00:00"),
            )
            for guid in guids
        ],
    )
    library = PodcastLibrary(shows=[show])
    library.queue = [QueueItem(show_id="s1", episode_guid=guid) for guid in guids]
    return library


def _guids(library: PodcastLibrary) -> list[str]:
    return [item.episode_guid for item in library.queue]


# -- moving ---------------------------------------------------------------- #


def test_move_to_top_keeps_the_selection_in_its_own_order() -> None:
    library = _library("a", "b", "c", "d", "e")
    moved = move_selection(library, [1, 3], where="top")
    assert _guids(library) == ["b", "d", "a", "c", "e"]
    assert moved == [0, 1]


def test_move_to_bottom_keeps_the_selection_in_its_own_order() -> None:
    library = _library("a", "b", "c", "d", "e")
    moved = move_selection(library, [0, 2], where="bottom")
    assert _guids(library) == ["b", "d", "e", "a", "c"]
    assert moved == [3, 4]


def test_the_new_indexes_are_returned_so_the_selection_can_be_restored() -> None:
    """Without this, a second press moves one item while you believe it is three."""
    library = _library("a", "b", "c", "d")
    moved = move_selection(library, [2, 3], where="top")
    assert moved == [0, 1]
    assert [_guids(library)[index] for index in moved] == ["c", "d"]


def test_moving_a_block_that_is_already_there_changes_nothing() -> None:
    library = _library("a", "b", "c")
    assert move_selection(library, [0, 1], where="top") == [0, 1]
    assert _guids(library) == ["a", "b", "c"]


def test_moving_everything_is_a_no_op_in_order() -> None:
    library = _library("a", "b", "c")
    assert move_selection(library, [0, 1, 2], where="bottom") == [0, 1, 2]
    assert _guids(library) == ["a", "b", "c"]


def test_an_empty_selection_moves_nothing() -> None:
    library = _library("a", "b")
    assert move_selection(library, [], where="top") == []
    assert _guids(library) == ["a", "b"]


def test_a_stale_index_is_ignored_rather_than_raising() -> None:
    """Half-working because one row had gone is worse than working on what is there."""
    library = _library("a", "b")
    assert move_selection(library, [1, 99, -4], where="top") == [0]
    assert _guids(library) == ["b", "a"]


def test_a_repeated_index_counts_once() -> None:
    library = _library("a", "b", "c")
    assert move_selection(library, [2, 2, 2], where="top") == [0]
    assert _guids(library) == ["c", "a", "b"]


# -- sorting --------------------------------------------------------------- #


def test_sort_oldest_first_rearranges_only_the_selected_positions() -> None:
    """Rows 0, 2 and 4 hold a, c, e; sorted oldest first they hold a, e, c."""
    library = _library("a", "b", "c", "d", "e")
    touched = sort_selection_by_date(library, [0, 2, 4], newest_first=False)
    assert _guids(library) == ["a", "b", "e", "d", "c"]
    assert touched == [0, 2, 4]  # the positions, which is what stays selected


def test_sort_newest_first_is_the_other_direction() -> None:
    library = _library("a", "b", "c", "d", "e")
    sort_selection_by_date(library, [0, 2, 4], newest_first=True)
    assert _guids(library) == ["c", "b", "e", "d", "a"]


def test_sorting_leaves_every_unselected_row_exactly_where_it_was() -> None:
    library = _library("a", "b", "c", "d", "e")
    sort_selection_by_date(library, [0, 2, 4], newest_first=False)
    assert _guids(library)[1] == "b"
    assert _guids(library)[3] == "d"


def test_sorting_one_row_or_none_does_nothing() -> None:
    library = _library("a", "b", "c")
    assert sort_selection_by_date(library, [1], newest_first=False) == [1]
    assert sort_selection_by_date(library, [], newest_first=False) == []
    assert _guids(library) == ["a", "b", "c"]


def test_a_stale_slot_sorts_to_the_front_of_an_oldest_first_sort() -> None:
    """Predictable rather than arbitrary; it is dropped on the next step anyway."""
    library = _library("a", "c")
    library.queue.append(QueueItem(show_id="s1", episode_guid="gone"))
    sort_selection_by_date(library, [0, 1, 2], newest_first=False)
    assert _guids(library)[0] == "gone"


# -- shuffling ------------------------------------------------------------- #


def test_shuffle_permutes_the_selected_positions_and_nothing_else() -> None:
    library = _library("a", "b", "c", "d", "e")
    touched = shuffle_selection(library, [0, 2, 4], rng=random.Random(7))
    assert touched == [0, 2, 4]
    # b and d never move, whatever the shuffle did.
    assert _guids(library)[1] == "b"
    assert _guids(library)[3] == "d"
    # The same three episodes are still in those three places.
    assert sorted(_guids(library)[i] for i in (0, 2, 4)) == ["a", "c", "e"]


def test_shuffle_actually_reorders_given_a_seed_that_does() -> None:
    before = None
    for seed in range(20):
        library = _library("a", "b", "c", "d", "e")
        shuffle_selection(library, [0, 1, 2, 3, 4], rng=random.Random(seed))
        if _guids(library) != ["a", "b", "c", "d", "e"]:
            before = _guids(library)
            break
    assert before is not None, "no seed in 20 produced a permutation"


def test_shuffling_one_row_or_none_does_nothing() -> None:
    library = _library("a", "b")
    assert shuffle_selection(library, [0]) == [0]
    assert shuffle_selection(library, []) == []
    assert _guids(library) == ["a", "b"]
