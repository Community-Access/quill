"""Cast's library and transcript search index (F-09): correct, incremental, cancellable.

The timing half -- a 1,500-podcast library against ceilings -- is
``test_cast_search_budget.py``. This file proves the *shape* without a clock:
what is found and in what order, that a sync after one change rebuilds one
record, that a narrow search reads no episode it did not match, that a cancel
stops the work, and that the memory caps are counted rather than silent.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.podcasts import search_index as si
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.search_index import LibrarySearchIndex, find_everything
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.podcasts.transcript_index import TranscriptMatch, TranscriptSearchIndex
from quill.stability.task_manager import CancelledError


def _episode(guid: str, title: str, published: str = "", description: str = "") -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid, title=title, audio_url="", published=published, description=description
    )


@pytest.fixture
def shows() -> list[PodcastShow]:
    harbour = PodcastShow(id="h", title="Harbour Tales", feed_url="https://example.invalid/h")
    harbour.episodes = [
        _episode("h1", "The pilot", "2026-01-01", "<p>We meet the <b>harbour</b> master.</p>"),
        _episode("h2", "Harbour lights", "2026-02-01"),
    ]
    daily = PodcastShow(id="d", title="The Daily", feed_url="https://example.invalid/d")
    daily.episodes = [
        _episode("d1", "Monday", "2026-03-01", "News &amp; the harbour strike"),
        _episode("d2", "Tuesday", "2026-04-01"),
        _episode("d3", "Wednesday", "2026-05-01"),
    ]
    return [harbour, daily]


def _kinds(outcome: si.SearchOutcome) -> list[tuple[str, str]]:
    return [(hit.kind, hit.episode_guid or hit.show_id) for hit in outcome.hits]


# -- what is found ------------------------------------------------------------------ #


def test_ranked_podcast_then_titles_then_show_notes_each_episode_once(shows) -> None:
    outcome = find_everything(LibrarySearchIndex(), shows, "HARBOUR")
    assert _kinds(outcome) == [
        ("show", "h"),
        ("episode", "h2"),  # its title matches, so its notes are not listed again
        ("show_notes", "d1"),  # newest first within a kind
        ("show_notes", "h1"),
    ]
    assert outcome.total == 4
    assert outcome.query == "HARBOUR"


def test_notes_and_transcripts_rank_after_titles_and_name_their_episode(shows) -> None:
    note = SimpleNamespace(show_id="d", episode_guid="d2", text="the ferry was late\nmore")
    index = LibrarySearchIndex()
    index.sync(shows)
    hits, total = index.search(
        "ferry",
        notes=[note],
        transcripts=[TranscriptMatch("d", "d3", "and then the ferry left")],
    )
    assert [(h.kind, h.episode_guid, h.snippet) for h in hits] == [
        ("note", "d2", "the ferry was late"),
        ("transcript", "d3", "and then the ferry left"),
    ]
    assert hits[1].episode_title == "Wednesday" and hits[1].show_title == "The Daily"
    assert total == 2


def test_a_transcript_hit_for_an_episode_already_found_is_not_repeated(shows) -> None:
    index = LibrarySearchIndex()
    index.sync(shows)
    hits, total = index.search(
        "lights", transcripts=[TranscriptMatch("h", "h2", "the lights came on")]
    )
    assert [(h.kind, h.episode_guid) for h in hits] == [("episode", "h2")]
    assert total == 1


def test_episode_filters_with_the_search_scope_still_hide(shows, monkeypatch) -> None:
    library = PodcastLibrary(shows=shows)
    monkeypatch.setattr(
        "quill.core.podcasts.episode_filter_maintenance.hide_predicate",
        lambda _lib, show, _scope: (lambda e: e.guid == "h2") if show.id == "h" else None,
    )
    outcome = find_everything(LibrarySearchIndex(), shows, "harbour", library=library)
    assert ("episode", "h2") not in _kinds(outcome)
    assert outcome.total == 3


def test_the_cap_keeps_the_newest_and_the_total_counts_everything() -> None:
    show = PodcastShow(id="x", title="X", feed_url="https://example.invalid/x")
    show.episodes = [_episode(f"x{i}", f"Part {i}", f"2026-{i:04d}") for i in range(500)]
    hits, total = LibrarySearchIndex().search("part")  # never synced: nothing
    assert (hits, total) == ([], 0)
    index = LibrarySearchIndex()
    index.sync([show])
    hits, total = index.search("part", cap=10)
    assert total == 500
    assert [h.episode_guid for h in hits] == [f"x{i}" for i in range(499, 489, -1)]


def test_an_empty_query_finds_nothing(shows) -> None:
    outcome = find_everything(LibrarySearchIndex(), shows, "   ")
    assert outcome.hits == () and outcome.total == 0


# -- incremental, not rebuilt ------------------------------------------------------- #


def test_a_second_sync_rebuilds_nothing_and_one_change_rebuilds_one(shows) -> None:
    index = LibrarySearchIndex()
    assert index.sync(shows) == 2
    generation = index.generation
    assert index.sync(shows) == 0
    assert index.generation == generation
    shows[1].episodes.append(_episode("d4", "Thursday harbour", "2026-06-01"))
    assert index.sync(shows) == 1
    assert index.generation == generation + 1
    hits, _ = index.search("thursday")
    assert [h.episode_guid for h in hits] == ["d4"]


def test_invalidate_catches_a_title_rewritten_in_place(shows) -> None:
    index = LibrarySearchIndex()
    index.sync(shows)
    shows[1].episodes[1].title = "Tuesday: the regatta"  # count and ends unchanged
    assert index.sync(shows) == 0
    index.invalidate("d")
    assert index.sync(shows) == 1
    assert [h.episode_guid for h in index.search("regatta")[0]] == ["d2"]


def test_a_removed_podcast_leaves_the_index(shows) -> None:
    index = LibrarySearchIndex()
    index.sync(shows)
    index.sync(shows[1:])
    assert index.search("harbour lights")[0] == []
    assert index.stats()["shows"] == 1


class _CountingEpisode(PodcastEpisode):
    """An episode that counts how often its title is read."""

    reads = 0

    def __getattribute__(self, name: str):  # type: ignore[no-untyped-def]
        if name == "title":
            type(self).reads += 1
        return super().__getattribute__(name)


def test_a_narrow_search_reads_no_episode_it_did_not_match() -> None:
    """The structural half of the budget: the search is not a scan in disguise."""
    show = PodcastShow(id="c", title="Counted", feed_url="https://example.invalid/c")
    show.episodes = [
        _CountingEpisode(guid=f"c{i}", title=f"Item {i}", audio_url="") for i in range(1000)
    ]
    index = LibrarySearchIndex()
    index.sync([show])
    _CountingEpisode.reads = 0
    hits, total = index.search("item 777")
    assert total == 1 and hits[0].episode_guid == "c777"
    assert _CountingEpisode.reads <= 3  # the hit's own title, not a thousand


# -- cancellation and memory -------------------------------------------------------- #


def test_a_cancelled_sync_stops_and_the_next_one_finishes(shows) -> None:
    many = [PodcastShow(id=f"s{i}", title=f"Show {i}") for i in range(300)]
    index = LibrarySearchIndex()
    with pytest.raises(CancelledError):
        index.sync(many, cancel=lambda: True)
    assert index.sync(many) > 0
    assert index.stats()["shows"] == 300


def test_a_cancelled_search_raises_rather_than_answering(shows) -> None:
    many = []
    for i in range(300):
        show = PodcastShow(id=f"s{i}", title=f"Show {i}")
        show.episodes = [_episode(f"s{i}e", "same words")]
        many.append(show)
    index = LibrarySearchIndex()
    index.sync(many)
    with pytest.raises(CancelledError):
        index.search("same", cancel=lambda: True)


def test_show_notes_past_the_total_cap_are_counted_not_silently_lost() -> None:
    show = PodcastShow(id="n", title="Notes")
    show.episodes = [_episode(f"n{i}", f"E{i}", description="word " * 50) for i in range(10)]
    index = LibrarySearchIndex(notes_chars_per_episode=100, notes_total_chars=450)
    index.sync([show])
    stats = index.stats()
    assert stats["notes_characters"] <= 450
    assert stats["notes_skipped_for_memory"] == 6


# -- transcripts ------------------------------------------------------------------- #


def _write_transcript(folder: Path, name: str, show_id: str, guid: str, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(f"{show_id}\n{guid}\n{text}".encode())
    return path


def test_transcripts_are_read_once_and_only_changed_files_again(tmp_path: Path) -> None:
    folder = tmp_path / "podcast-transcripts"
    _write_transcript(folder, "a.txt", "d", "d1", "We talked about the Bristol bus boycott.")
    second = _write_transcript(folder, "b.txt", "d", "d2", "Nothing much.")
    index = TranscriptSearchIndex(lambda: folder)
    assert index.refresh() is True
    assert index.last_reads == 2
    assert index.refresh() is True
    assert index.last_reads == 0  # warm: nothing read twice
    matches = list(index.search("bristol"))
    assert [(m.show_id, m.episode_guid) for m in matches] == [("d", "d1")]
    assert "Bristol bus boycott" in matches[0].snippet
    second.write_bytes(b"d\nd2\nNow the Bristol harbour too.")
    index.refresh()
    assert index.last_reads == 1
    assert len(list(index.search("bristol"))) == 2
    second.unlink()
    index.refresh()
    assert len(list(index.search("bristol"))) == 1


def test_a_transcript_refresh_stops_when_cancelled(tmp_path: Path) -> None:
    folder = tmp_path / "podcast-transcripts"
    for i in range(5):
        _write_transcript(folder, f"{i}.txt", "s", f"g{i}", "text")
    index = TranscriptSearchIndex(lambda: folder)
    assert index.refresh(cancel=lambda: True) is False
    assert index.stats()["transcripts"] == 0
    assert index.refresh() is True
    assert index.stats()["transcripts"] == 5


def test_the_transcript_memory_cap_is_observable(tmp_path: Path) -> None:
    folder = tmp_path / "podcast-transcripts"
    for i in range(4):
        _write_transcript(folder, f"{i}.txt", "s", f"g{i}", "x" * 100)
    index = TranscriptSearchIndex(lambda: folder, total_chars=250)
    index.refresh()
    assert index.stats() == {"transcripts": 2, "characters": 200, "skipped_for_memory": 2}
    index.refresh()
    assert index.last_reads == 0  # a skipped file is not re-read until it changes


def test_transcript_memory_accounting_uses_casefolded_length(tmp_path: Path) -> None:
    folder = tmp_path / "podcast-transcripts"
    path = _write_transcript(folder, "sharp.txt", "s", "g", "ß")
    index = TranscriptSearchIndex(lambda: folder, total_chars=2)
    index.refresh()
    assert index.stats()["characters"] == 2
    path.unlink()
    index.refresh()
    assert index.stats()["characters"] == 0


def test_find_everything_searches_transcripts_through_the_index(shows, tmp_path: Path) -> None:
    folder = tmp_path / "podcast-transcripts"
    _write_transcript(folder, "w.txt", "d", "d3", "a long talk about lighthouses")
    outcome = find_everything(
        LibrarySearchIndex(), shows, "lighthouse", transcripts=TranscriptSearchIndex(lambda: folder)
    )
    assert _kinds(outcome) == [("transcript", "d3")]
    assert outcome.hits[0].snippet.startswith("a long talk about lighthouses")
