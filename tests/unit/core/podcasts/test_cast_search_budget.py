"""GATE-PERF for Cast: search, transcripts, feed checks and downloads at library scale (F-09).

A synthetic library of 1,500 podcasts x 200 episodes -- 300,000 episodes, the
size QC2 8.4 asks the budgets to be set at -- against ceilings, not against an
older build. The same philosophy as ``tests/unit/core/test_large_document_budget.py``:
the ceilings are generous, because a CI box under load is several times slower
than a desk, and what they catch is a change of *complexity*. A search that
went back to walking every episode in Python, or a sync that rebuilt every
podcast to take in one, does not come in slightly over; it comes in many
times over. The structural half -- a narrow search reads no episode it did not
match, a sync after one change rebuilds one record -- is asserted exactly.

Marked ``perf``. A failure here that passes when the file runs alone is load on
the machine, not a regression; re-run it alone before believing it.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from quill.core.podcasts.download_queue import PodcastDownloadQueue
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.search_index import LibrarySearchIndex, find_everything
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.podcasts.transcript_index import TranscriptSearchIndex

pytestmark = pytest.mark.perf

_SHOWS = 1500
_EPISODES = 200
_WORDS = (
    "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
    "november oscar papa quebec romeo sierra tango uniform victor whiskey xray"
).split()

# -- the ceilings ------------------------------------------------------------------ #

#: Folding 300,000 titles and their show notes, once. Measured about 1 s.
_FIRST_SYNC_CEILING_S = 20.0
#: A sync after one podcast changed. It must not scale with the library.
_RESYNC_CEILING_S = 0.5
#: One narrow search -- the case typing produces. Measured about 0.03 s.
_NARROW_CEILING_S = 1.0
#: The worst query there is: one letter, matching nearly every episode. It still
#: has to count them all, so it is linear in matches; measured about 0.7 s.
_BROADEST_CEILING_S = 10.0
#: A word typed a letter at a time, each letter a search (no pause at all).
_TYPING_CEILING_S = 5.0


@pytest.fixture(scope="module")
def shows() -> list[PodcastShow]:
    built: list[PodcastShow] = []
    for s in range(_SHOWS):
        show = PodcastShow(id=f"s{s}", title=f"Show {s} {_WORDS[s % len(_WORDS)]}")
        show.episodes = [
            PodcastEpisode(
                guid=f"s{s}e{e}",
                title=f"Episode {e}: {_WORDS[(s + e) % len(_WORDS)]} and "
                f"{_WORDS[(s * 7 + e) % len(_WORDS)]}",
                audio_url="",
                published=f"2026-{e % 12 + 1:02d}-{e % 28 + 1:02d}",
                description=f"<p>A talk with guest number {s * 1000 + e} about "
                f"{_WORDS[e % len(_WORDS)]}.</p>",
            )
            for e in range(_EPISODES)
        ]
        built.append(show)
    return built


@pytest.fixture(scope="module")
def warm_index(shows: list[PodcastShow]) -> LibrarySearchIndex:
    index = LibrarySearchIndex()
    began = time.perf_counter()
    index.sync(shows)
    elapsed = time.perf_counter() - began
    assert elapsed < _FIRST_SYNC_CEILING_S, f"first sync took {elapsed:.2f}s"
    return index


def _seconds(action) -> float:  # type: ignore[no-untyped-def]
    began = time.perf_counter()
    action()
    return time.perf_counter() - began


def test_the_whole_library_is_indexed(warm_index: LibrarySearchIndex) -> None:
    stats = warm_index.stats()
    assert stats["shows"] == _SHOWS
    assert stats["episodes"] == _SHOWS * _EPISODES


def test_a_narrow_search_is_quick(warm_index, shows) -> None:
    library = PodcastLibrary(shows=shows)
    outcome = None

    def run() -> None:
        nonlocal outcome
        outcome = find_everything(warm_index, shows, "guest number 1234005", library=library)

    elapsed = _seconds(run)
    assert outcome is not None and outcome.total == 1
    assert elapsed < _NARROW_CEILING_S, f"a narrow search took {elapsed:.3f}s"


def test_the_broadest_search_still_counts_everything_within_its_budget(warm_index, shows) -> None:
    outcome = None

    def run() -> None:
        nonlocal outcome
        outcome = find_everything(warm_index, shows, "e")

    elapsed = _seconds(run)
    assert outcome is not None
    assert len(outcome.hits) == 200
    assert outcome.total >= _SHOWS * _EPISODES
    assert elapsed < _BROADEST_CEILING_S, f"the broadest search took {elapsed:.2f}s"


def test_typing_a_word_a_letter_at_a_time_stays_bounded(warm_index, shows) -> None:
    word = "november tango"
    elapsed = _seconds(
        lambda: [find_everything(warm_index, shows, word[: n + 1]) for n in range(3, len(word))]
    )
    assert elapsed < _TYPING_CEILING_S, f"typing {word!r} took {elapsed:.2f}s"


def test_one_changed_podcast_rebuilds_one_record(warm_index, shows) -> None:
    shows[700].episodes.append(PodcastEpisode(guid="late", title="A late arrival", audio_url=""))
    try:
        rebuilt: list[int] = []
        elapsed = _seconds(lambda: rebuilt.append(warm_index.sync(shows)))
        assert rebuilt == [1]
        assert elapsed < _RESYNC_CEILING_S, f"a one-podcast resync took {elapsed:.3f}s"
        assert [h.episode_guid for h in warm_index.search("late arrival")[0]] == ["late"]
    finally:
        shows[700].episodes.pop()
        warm_index.sync(shows)


def test_a_superseded_search_stops_promptly(warm_index, shows) -> None:
    """Cancellation is the other half of staleness: an old query must let go."""
    asked = threading.Event()

    def cancel() -> bool:
        asked.set()
        return True

    from quill.stability.task_manager import CancelledError

    began = time.perf_counter()
    with pytest.raises(CancelledError):
        find_everything(warm_index, shows, "e", cancel=cancel)
    assert asked.is_set()
    assert time.perf_counter() - began < 1.0


def test_many_transcripts_index_once_and_search_warm(tmp_path: Path) -> None:
    folder = tmp_path / "podcast-transcripts"
    folder.mkdir()
    sentence = "and so the conversation turned to the history of the harbour " * 300
    for i in range(150):
        (folder / f"{i}.txt").write_bytes(f"s{i}\ns{i}e0\n{sentence} token{i}".encode())
    # The first read of a file just written is the antivirus's cost on Windows
    # (measured: ten seconds for 300 of these, against 0.3 s for the indexing
    # itself). Paid outside the clock, so the ceiling measures this code.
    for path in folder.iterdir():
        path.read_bytes()
    index = TranscriptSearchIndex(lambda: folder)
    first = _seconds(lambda: index.refresh())
    assert first < 15.0, f"indexing 150 transcripts took {first:.2f}s"
    warm = _seconds(lambda: index.refresh())
    assert index.last_reads == 0
    assert warm < 1.0, f"a warm transcript refresh took {warm:.3f}s"
    found: list = []
    elapsed = _seconds(lambda: found.extend(index.search("token149")))
    assert [m.show_id for m in found] == ["s149"]
    assert elapsed < 1.0, f"a transcript search took {elapsed:.3f}s"


def test_download_counts_do_not_scan_a_long_queue() -> None:
    """The status cell asks on every progress tick; the answer must be O(1)."""
    queue = PodcastDownloadQueue()
    queue.pause_all()  # nothing starts: this measures the bookkeeping only
    try:
        for i in range(5000):
            queue.enqueue(f"i{i}", show_id="s", episode_guid=f"g{i}", url="", destination=Path("x"))
        elapsed = _seconds(lambda: [queue.count("queued") for _ in range(20000)])
        assert queue.count("queued") == 5000
        assert elapsed < 2.0, f"20,000 count() calls took {elapsed:.2f}s"
    finally:
        queue.shutdown()
