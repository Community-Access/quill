"""Play Queue operations: ordering, dedupe, accessible reordering,
stale-slot self-healing, and library persistence round-trip."""

from __future__ import annotations

from quill.core.podcasts import queue as q
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library_with(episodes: int = 3) -> PodcastLibrary:
    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Show")
    for i in range(1, episodes + 1):
        show.episodes.append(
            PodcastEpisode(guid=f"e{i}", title=f"Episode {i}", audio_url=f"https://x/{i}.mp3")
        )
    library.add_show(show)
    return library


def _guids(library: PodcastLibrary) -> list[str]:
    return [item.episode_guid for item in library.queue]


def test_add_appends_and_dedupes() -> None:
    library = _library_with()
    assert q.add_to_queue(library, "s1", "e1")
    assert q.add_to_queue(library, "s1", "e2")
    assert not q.add_to_queue(library, "s1", "e1")  # already queued
    assert _guids(library) == ["e1", "e2"]


def test_play_next_inserts_at_front_and_moves_existing() -> None:
    library = _library_with()
    q.add_to_queue(library, "s1", "e1")
    q.add_to_queue(library, "s1", "e2")
    q.play_next(library, "s1", "e3")
    assert _guids(library) == ["e3", "e1", "e2"]
    q.play_next(library, "s1", "e2")  # moves, never duplicates
    assert _guids(library) == ["e2", "e3", "e1"]


def test_move_nudges_within_bounds() -> None:
    library = _library_with()
    for guid in ("e1", "e2", "e3"):
        q.add_to_queue(library, "s1", guid)
    assert q.move(library, 0, 1) == 1
    assert _guids(library) == ["e2", "e1", "e3"]
    assert q.move(library, 0, -1) == 0  # off the top: unchanged
    assert _guids(library) == ["e2", "e1", "e3"]


def test_move_relative_to_places_above_and_below() -> None:
    library = _library_with()
    for guid in ("e1", "e2", "e3"):
        q.add_to_queue(library, "s1", guid)
    new_index = q.move_relative_to(library, 0, 2, above=False)  # e1 below e3
    assert new_index == 2
    assert _guids(library) == ["e2", "e3", "e1"]
    new_index = q.move_relative_to(library, 2, 0, above=True)  # e1 above e2
    assert new_index == 0
    assert _guids(library) == ["e1", "e2", "e3"]


def test_remove_and_clear() -> None:
    library = _library_with()
    for guid in ("e1", "e2"):
        q.add_to_queue(library, "s1", guid)
    assert q.remove_at(library, 0)
    assert _guids(library) == ["e2"]
    assert not q.remove_at(library, 5)
    assert q.clear_queue(library) == 1
    assert library.queue == []


def test_pop_next_playable_skips_stale_slots() -> None:
    library = _library_with()
    q.add_to_queue(library, "gone-show", "e9")  # stale: no such show
    q.add_to_queue(library, "s1", "gone-episode")  # stale: no such episode
    q.add_to_queue(library, "s1", "e2")
    resolved = q.pop_next_playable(library)
    assert resolved is not None
    show, episode = resolved
    assert (show.id, episode.guid) == ("s1", "e2")
    assert library.queue == []  # stale slots were consumed and dropped


def test_pop_next_playable_empty_queue() -> None:
    library = _library_with()
    assert q.pop_next_playable(library) is None


def test_queue_round_trips_through_save_and_load(tmp_path) -> None:
    from quill.core.podcasts.subscriptions import load_library, save_library

    library = _library_with()
    q.add_to_queue(library, "s1", "e2")
    q.add_to_queue(library, "s1", "e1")
    save_library(tmp_path, library)
    reloaded = load_library(tmp_path)
    assert [(i.show_id, i.episode_guid) for i in reloaded.queue] == [("s1", "e2"), ("s1", "e1")]
