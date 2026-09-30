"""Stepping the Play Queue without consuming it (ear.md R2, R3, R4).

The queue used to pop on start, so it only showed what was coming next. It now
keeps the playing episode in place -- which is what gives Previous in Queue
something to go back to -- and the slot leaves when the episode finishes.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.queue_steps import (
    RESTART_WITHIN_MS,
    finish_slot,
    index_of,
    queue_position,
    step_after_finishing,
    step_next,
    step_previous,
)
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library(*guids: str, show_id: str = "s1") -> PodcastLibrary:
    show = PodcastShow(
        id=show_id,
        title="Main Menu",
        feed_url="https://e/f.xml",
        episodes=[
            PodcastEpisode(
                guid=guid,
                title=f"Episode {guid}",
                audio_url=f"https://e/{guid}.mp3",
                published="2026-07-01T00:00:00",
            )
            for guid in guids
        ],
    )
    library = PodcastLibrary(shows=[show])
    library.queue = [QueueItem(show_id=show_id, episode_guid=guid) for guid in guids]
    return library


def _guids(library: PodcastLibrary) -> list[str]:
    return [item.episode_guid for item in library.queue]


# -- R4: nothing is consumed by stepping ----------------------------------- #


def test_stepping_next_removes_nothing() -> None:
    """The whole point of R4: the run stays intact while you move through it."""
    library = _library("a", "b", "c")
    step = step_next(library, "s1", "a")
    assert step.kind == "play"
    assert step.episode.guid == "b"
    assert _guids(library) == ["a", "b", "c"]


def test_stepping_previous_removes_nothing() -> None:
    library = _library("a", "b", "c")
    step = step_previous(library, "s1", "c", position_ms=0)
    assert step.episode.guid == "b"
    assert _guids(library) == ["a", "b", "c"]


def test_a_queued_episode_knows_its_position() -> None:
    library = _library("a", "b", "c")
    assert queue_position(library, "s1", "b") == "2 of 3"
    assert queue_position(library, "s1", "missing") == ""


def test_index_of_says_minus_one_for_an_episode_that_is_not_queued() -> None:
    assert index_of(_library("a"), "s1", "z") == -1


# -- R2: the ends of the run ----------------------------------------------- #


def test_next_at_the_end_is_an_edge_that_says_so() -> None:
    """Not None. A command that did nothing has to be able to say why."""
    step = step_next(_library("a", "b"), "s1", "b")
    assert step.is_edge
    assert step.message == "End of queue"


def test_previous_at_the_start_is_an_edge_that_says_so() -> None:
    step = step_previous(_library("a", "b"), "s1", "a", position_ms=0)
    assert step.is_edge
    assert step.message == "Start of queue"


def test_an_empty_queue_is_an_edge_in_both_directions() -> None:
    library = _library()
    assert step_next(library, "s1", "x").is_edge
    assert step_previous(library, "s1", "x", position_ms=0).is_edge


# -- R2: the five-second rule ---------------------------------------------- #


def test_previous_restarts_when_you_are_into_the_episode() -> None:
    library = _library("a", "b", "c")
    step = step_previous(library, "s1", "b", position_ms=RESTART_WITHIN_MS)
    assert step.kind == "restart"
    assert step.show is None  # nothing to play; the caller seeks to zero


def test_previous_steps_back_when_you_have_only_just_started() -> None:
    library = _library("a", "b", "c")
    step = step_previous(library, "s1", "b", position_ms=RESTART_WITHIN_MS - 1)
    assert step.kind == "play"
    assert step.episode.guid == "a"


def test_the_restart_rule_applies_even_to_an_episode_that_is_not_queued() -> None:
    """Started from a show's own list, 40 minutes in: Previous still restarts.

    That is what the key means everywhere else, so the rule is checked before
    the queue is consulted at all.
    """
    library = _library("a")
    step = step_previous(library, "s1", "not-queued", position_ms=2_400_000)
    assert step.kind == "restart"


def test_an_unqueued_episode_early_on_has_nowhere_to_go_back_to() -> None:
    library = _library("a")
    step = step_previous(library, "s1", "not-queued", position_ms=0)
    assert step.is_edge


# -- playing something that is not in the queue ---------------------------- #


def test_next_from_an_unqueued_episode_plays_the_front_of_the_queue() -> None:
    """The only reading that does not require inventing a position."""
    library = _library("a", "b")
    step = step_next(library, "s1", "not-queued")
    assert step.episode.guid == "a"


# -- stale slots self-heal ------------------------------------------------- #


def test_a_stale_slot_is_dropped_on_the_way_past() -> None:
    library = _library("a", "b")
    library.queue.insert(1, QueueItem(show_id="s1", episode_guid="gone"))
    step = step_next(library, "s1", "a")
    assert step.episode.guid == "b"
    assert _guids(library) == ["a", "b"]  # the stale slot is gone


def test_a_slot_for_an_unsubscribed_show_is_dropped_too() -> None:
    library = _library("a", "b")
    library.queue.insert(1, QueueItem(show_id="vanished", episode_guid="x"))
    assert step_next(library, "s1", "a").episode.guid == "b"
    assert _guids(library) == ["a", "b"]


def test_stepping_back_past_a_stale_slot_also_heals() -> None:
    library = _library("a", "c")
    library.queue.insert(1, QueueItem(show_id="s1", episode_guid="gone"))
    step = step_previous(library, "s1", "c", position_ms=0)
    assert step.episode.guid == "a"
    assert _guids(library) == ["a", "c"]


def test_a_queue_of_nothing_but_stale_slots_is_an_edge() -> None:
    library = _library("a")
    library.queue = [QueueItem(show_id="s1", episode_guid="gone")]
    step = step_next(library, "s1", "a")
    assert step.is_edge
    assert library.queue == []


# -- R3: Mark as Played and Next ------------------------------------------- #


def test_finishing_removes_only_that_slot_and_says_where_it_was() -> None:
    library = _library("a", "b", "c")
    assert finish_slot(library, "s1", "b") == 1
    assert _guids(library) == ["a", "c"]


def test_finishing_something_that_is_not_queued_removes_nothing() -> None:
    library = _library("a")
    assert finish_slot(library, "s1", "z") == -1
    assert _guids(library) == ["a"]


def test_mark_played_and_next_frees_the_slot_and_plays_what_took_its_place() -> None:
    library = _library("a", "b", "c")
    step, freed = step_after_finishing(library, "s1", "b")
    assert freed == 1
    assert step.episode.guid == "c"
    assert _guids(library) == ["a", "c"]


def test_mark_played_and_next_at_the_end_stops_and_says_so() -> None:
    """No wrap by default: the run is over, and it says the run is over."""
    library = _library("a", "b")
    step, freed = step_after_finishing(library, "s1", "b")
    assert freed == 1
    assert step.is_edge
    assert step.message == "End of queue"
    assert _guids(library) == ["a"]


def test_mark_played_and_next_on_an_unqueued_episode_advances_from_the_front() -> None:
    library = _library("a", "b")
    step, freed = step_after_finishing(library, "s1", "not-queued")
    assert freed == -1
    assert step.episode.guid == "a"
    assert _guids(library) == ["a", "b"]  # nothing was consumed
