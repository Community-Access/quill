"""The Inbox count in the window title (ear.md R15).

A title is announced on arrival and on every Alt+Tab back, without being asked,
so the count reaches the listener exactly when they are orienting and costs
nothing at any other moment. Announcing it instead would be the same fact twice.
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.window_title import compose_title, inbox_count


def _library(*, routed: int = 0, played: int = 0) -> PodcastLibrary:
    episodes = [
        PodcastEpisode(
            guid=f"e{i}",
            title=f"Episode {i}",
            audio_url=f"https://e/{i}.mp3",
            published="2026-07-01T00:00:00",
            played=i < played,
        )
        for i in range(routed)
    ]
    show = PodcastShow(
        id="s1",
        title="The Daily",
        feed_url="https://e/f.xml",
        route_to_inbox=routed > 0,
        episodes=episodes,
    )
    return PodcastLibrary(shows=[show])


def test_an_empty_inbox_leaves_the_bare_app_name() -> None:
    """A zero is a number somebody has to read before learning there is nothing."""
    assert compose_title("QUILL Cast", 0) == "QUILL Cast"


def test_a_full_inbox_is_named_and_counted() -> None:
    assert compose_title("QUILL Cast", 12) == "QUILL Cast - Inbox (12)"


def test_the_count_comes_from_the_inbox_as_the_inbox_counts_it() -> None:
    """Through inbox_pairs, so caps and filters are already applied and the
    title cannot disagree with the list it is counting."""
    assert inbox_count(_library(routed=3)) == 3
    assert inbox_count(_library(routed=3, played=2)) == 1
    assert inbox_count(_library()) == 0


def test_a_library_that_raises_counts_as_nothing() -> None:
    """A title is never worth a crash."""

    class _Exploding:
        @property
        def shows(self):
            raise RuntimeError("boom")

    assert inbox_count(_Exploding()) == 0
