"""Saving a Play Queue order and putting it back (list.md 2.3).

The load-bearing property is that **apply moves rather than replaces**. A
lineup that emptied the queue and refilled it from its own list would be the
app deciding that whatever else somebody had queued did not matter -- and would
lose the added-at stamps Queue Expiration measures against on the way.

So: the lineup's available unplayed episodes go to the front in the lineup's
order; everything else stays behind them in the order it already had; anything
played or gone is skipped and counted. The counting is the difference between a
lineup that worked and one that quietly half-worked, which is otherwise
indistinguishable without sight of the list.

And a lineup **is a manual playlist** -- the same record, not a parallel one --
so it renames, deletes, lists and exports with everything else. These tests pin
that too, because a future "Lineup" dataclass would look like tidying.
"""

from __future__ import annotations

from quill.core.podcasts import queue_lineups
from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(guid: str, *, played: bool = False) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://e/{guid}.mp3",
        published="2026-07-01T00:00:00",
        played=played,
    )


def _library(*, played: tuple[str, ...] = ()) -> PodcastLibrary:
    show = PodcastShow(
        id="show-1",
        title="Main Menu",
        feed_url="https://e/f.xml",
        episodes=[_episode(guid, played=guid in played) for guid in ("a", "b", "c", "d")],
    )
    return PodcastLibrary(shows=[show])


def _queue(library: PodcastLibrary, *guids: str) -> None:
    library.queue = [QueueItem("show-1", guid, added_at="2026-07-01T00:00:00") for guid in guids]


def _order(library: PodcastLibrary) -> list[str]:
    return [item.episode_guid for item in library.queue]


# -- saving ----------------------------------------------------------------------


def test_saving_keeps_the_order_the_queue_is_in() -> None:
    library = _library()
    _queue(library, "c", "a", "b")

    saved = queue_lineups.save_lineup(library, "Tuesday")

    assert saved is not None
    assert [item.episode_guid for item in saved.items] == ["c", "a", "b"]


def test_a_lineup_is_a_manual_playlist_not_a_second_kind_of_thing() -> None:
    """Rename, delete, list and export all come free because of this."""
    library = _library()
    _queue(library, "a")

    saved = queue_lineups.save_lineup(library, "Tuesday")

    assert saved is not None
    assert saved.kind == "manual"
    assert saved in library.playlists
    assert library.find_playlist(saved.id) is saved


def test_an_empty_queue_saves_nothing() -> None:
    """A name in the list that does nothing is worse than no name."""
    library = _library()

    assert queue_lineups.save_lineup(library, "Tuesday") is None
    assert library.playlists == []


def test_a_lineup_with_no_name_is_refused() -> None:
    library = _library()
    _queue(library, "a")

    assert queue_lineups.save_lineup(library, "   ") is None
    assert library.playlists == []


def test_re_saving_replaces_rather_than_making_a_second_tuesday() -> None:
    library = _library()
    _queue(library, "a", "b")
    queue_lineups.save_lineup(library, "Tuesday")

    _queue(library, "d")
    again = queue_lineups.save_lineup(library, "Tuesday")

    assert len(library.playlists) == 1
    assert again is not None
    assert [item.episode_guid for item in again.items] == ["d"]


def test_a_name_is_matched_however_it_was_typed() -> None:
    library = _library()
    _queue(library, "a")
    queue_lineups.save_lineup(library, "Tuesday")
    _queue(library, "b")

    queue_lineups.save_lineup(library, "TUESDAY")

    assert len(library.playlists) == 1


# -- applying --------------------------------------------------------------------


def test_the_lineup_goes_to_the_front_in_its_own_order() -> None:
    library = _library()
    _queue(library, "a", "b", "c")
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    _queue(library, "d", "c", "b", "a")

    counted = queue_lineups.apply_lineup(library, lineup)

    assert _order(library) == ["a", "b", "c", "d"]
    assert counted.done == 3


def test_everything_the_lineup_does_not_mention_stays_where_it_was() -> None:
    """A lineup rearranges the front. It is not an instruction about the rest."""
    library = _library()
    _queue(library, "a")
    lineup = queue_lineups.save_lineup(library, "One")
    assert lineup is not None
    _queue(library, "d", "c", "b", "a")

    queue_lineups.apply_lineup(library, lineup)

    assert _order(library) == ["a", "d", "c", "b"]


def test_an_episode_not_in_the_queue_is_brought_in() -> None:
    library = _library()
    _queue(library, "a", "b")
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    _queue(library, "d")

    counted = queue_lineups.apply_lineup(library, lineup)

    assert _order(library) == ["a", "b", "d"]
    assert counted.done == 2


def test_a_played_episode_is_skipped_and_counted() -> None:
    """Putting something somebody finished back at the front is the app
    disagreeing with them about what they have done."""
    library = _library()
    _queue(library, "a", "b", "c")
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    library.shows[0].episodes[1].played = True
    _queue(library)

    counted = queue_lineups.apply_lineup(library, lineup)

    assert _order(library) == ["a", "c"]
    assert (counted.done, counted.skipped) == (2, 1)
    assert "already played" in counted.sentence("Applied", "Tuesday", noun="episode")


def test_an_episode_that_left_the_library_is_skipped_not_a_crash() -> None:
    library = _library()
    _queue(library, "a", "b")
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    library.shows[0].episodes = [e for e in library.shows[0].episodes if e.guid != "b"]
    _queue(library)

    counted = queue_lineups.apply_lineup(library, lineup)

    assert _order(library) == ["a"]
    assert counted.skipped == 1


def test_a_whole_lineup_of_played_episodes_says_so_rather_than_nothing() -> None:
    library = _library()
    _queue(library, "a", "b")
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    for episode in library.shows[0].episodes:
        episode.played = True
    _queue(library, "d")

    counted = queue_lineups.apply_lineup(library, lineup)

    assert _order(library) == ["d"], "the queue is untouched"
    assert counted.done == 0
    said = counted.sentence("Applied", "Tuesday", noun="episode")
    assert "already played" in said


def test_the_added_at_stamp_survives_a_reorder() -> None:
    """Queue Expiration measures how long something has waited, and being
    moved up the list is not waiting less."""
    library = _library()
    library.queue = [
        QueueItem("show-1", "a", added_at="2026-01-01T00:00:00"),
        QueueItem("show-1", "b", added_at="2026-02-02T00:00:00"),
    ]
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    library.queue = list(reversed(library.queue))

    queue_lineups.apply_lineup(library, lineup)

    assert library.queue[0].added_at == "2026-01-01T00:00:00"
    assert library.queue[1].added_at == "2026-02-02T00:00:00"


def test_an_episode_listed_twice_is_queued_once() -> None:
    library = _library()
    _queue(library, "a")
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    lineup.items = [QueueItem("show-1", "a"), QueueItem("show-1", "a")]

    counted = queue_lineups.apply_lineup(library, lineup)

    assert _order(library) == ["a"]
    assert counted.done == 1


def test_an_empty_lineup_says_why_nothing_happened() -> None:
    library = _library()
    _queue(library, "a")
    lineup = queue_lineups.save_lineup(library, "Tuesday")
    assert lineup is not None
    lineup.items = []

    counted = queue_lineups.apply_lineup(library, lineup)

    assert counted.done == 0
    assert "no episodes yet" in counted.sentence("Applied", "Tuesday", noun="episode")


# -- finding ---------------------------------------------------------------------


def test_the_names_read_back_in_the_order_they_were_saved() -> None:
    library = _library()
    _queue(library, "a")
    queue_lineups.save_lineup(library, "Tuesday")
    queue_lineups.save_lineup(library, "Commute")

    assert queue_lineups.lineup_names(library) == ["Tuesday", "Commute"]


def test_a_lineup_can_be_found_by_name() -> None:
    library = _library()
    _queue(library, "a")
    saved = queue_lineups.save_lineup(library, "Tuesday")

    assert queue_lineups.find_lineup(library, "tuesday") is saved
    assert queue_lineups.find_lineup(library, "Wednesday") is None


def test_a_lineup_survives_a_save_and_load(tmp_path) -> None:
    """It rides in the library file the playlists already ride in."""
    from quill.core.podcasts.subscriptions import load_library, save_library

    library = _library()
    _queue(library, "c", "a")
    queue_lineups.save_lineup(library, "Tuesday")
    save_library(tmp_path, library)

    back = load_library(tmp_path)
    found = queue_lineups.find_lineup(back, "Tuesday")

    assert found is not None
    assert [item.episode_guid for item in found.items] == ["c", "a"]
