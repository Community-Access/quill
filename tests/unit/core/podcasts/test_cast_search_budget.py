"""qc.md F-09: Cast's library search against a ceiling, on a library far
larger than anyone's.

Marked ``perf`` like the 50 MB document budget. The ceiling is generous on
purpose -- it is there to catch a search that became quadratic, or started
reading files, not to grade a fast machine against a slow one.
"""

from __future__ import annotations

import time

import pytest

from quill.core.podcasts.filtering import search_everywhere
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary

_SHOWS = 1300
_EPISODES = 100
_CEILING_SECONDS = 1.5


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    for s in range(_SHOWS):
        show = PodcastShow(id=f"s{s}", title=f"Show {s} about things", feed_url="x")
        show.episodes = [
            PodcastEpisode(guid=f"{s}-{e}", title=f"Episode {e} of show {s}", audio_url="a")
            for e in range(_EPISODES)
        ]
        library.shows.append(show)
    return library


@pytest.mark.perf
def test_searching_130_000_episodes_and_their_transcripts_stays_under_the_ceiling() -> None:
    library = _library()
    transcripts = [
        (f"s{n}", f"{n}-0", "words about the weather and the news " * 1000) for n in range(400)
    ]
    start = time.perf_counter()
    found = search_everywhere(library, "episode 7", transcripts=transcripts)
    missing = search_everywhere(library, "bristol", transcripts=transcripts)
    elapsed = time.perf_counter() - start
    assert found and not missing
    assert elapsed < _CEILING_SECONDS, f"{elapsed:.2f}s for two searches"


@pytest.mark.perf
def test_merging_a_5000_episode_feed_into_a_5000_episode_show_stays_under_the_ceiling() -> None:
    from quill.core.podcasts.subscriptions import merge_episodes

    show = PodcastShow(id="s", title="Back catalog", feed_url="x")
    show.episodes = [
        PodcastEpisode(guid=str(n), title=f"Episode {n}", audio_url="a") for n in range(5000)
    ]
    incoming = [
        PodcastEpisode(guid=str(n), title=f"Episode {n}", audio_url="a") for n in range(50, 5050)
    ]
    start = time.perf_counter()
    merge_episodes(show, incoming)
    elapsed = time.perf_counter() - start
    assert len(show.episodes) >= 5050
    assert elapsed < _CEILING_SECONDS, f"{elapsed:.2f}s to merge one feed"
