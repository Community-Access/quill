"""Find This Show's New Feed and Replace Feed (check.md bug 8).

The searcher and verifier are fakes with the shapes of the real test: Living
Blindfully's old feed is gone, the directory lists the show at a new address
alongside an unrelated show with a similar name and a dead copy. No network.
"""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.podcasts import check_state, feed_read, new_feed_finder
from quill.core.podcasts.feed_reader import FeedInfo
from quill.core.podcasts.itunes_search import PodcastSearchResult
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary

OLD = "https://feeds.example.com/livingblindfully"
NEW = "https://media.rss.example/living-blindfully/feed.xml"


def _show() -> PodcastShow:
    return PodcastShow(
        id="s1",
        title="Living Blindfully",
        feed_url=OLD,
        episodes=[
            PodcastEpisode(
                guid="old-1",
                title="Episode 300",
                audio_url="https://feeds.example.com/300.mp3",
                published="Mon, 01 Jun 2026 08:00:00 GMT",
                played=True,
            )
        ],
    )


def _searcher(query: str) -> tuple[list[PodcastSearchResult], list[str]]:
    assert query == "Living Blindfully"
    return (
        [
            PodcastSearchResult(title="Living Blindfully", feed_url=OLD),  # the dead one
            PodcastSearchResult(title="Living Blind", feed_url="https://other.example/feed"),
            PodcastSearchResult(title="Living Blindfully", feed_url=NEW, artist="Jonathan"),
            PodcastSearchResult(title="Living Blindfully", feed_url="https://dead.example/f"),
            PodcastSearchResult(title="Living Blindfully", feed_url="https://empty.example/f"),
        ],
        ["Podcast Index did not answer."],
    )


def _verifier(feed_url: str) -> tuple[int, datetime | None]:
    if "dead" in feed_url:
        raise OSError("refused")
    if "empty" in feed_url:
        return 0, None
    if feed_url == NEW:
        return 312, datetime(2026, 9, 28, tzinfo=UTC)
    return 40, datetime(2026, 9, 30, tzinfo=UTC)


def test_only_verified_feeds_are_offered_the_shows_own_title_first() -> None:
    found = new_feed_finder.find_new_feed(_show(), searcher=_searcher, verifier=_verifier)

    assert [c.feed_url for c in found.candidates] == [NEW, "https://other.example/feed"]
    assert found.rejected == 2  # the dead copy and the empty one
    assert found.candidates[0].describe() == (
        "Living Blindfully, by Jonathan, 312 episodes, newest 28 September 2026, "
        "at media.rss.example"
    )
    assert found.summary("Living Blindfully") == (
        "Found 2 possible new feeds for Living Blindfully. Podcast Index did not answer."
    )


def test_a_close_name_outranks_an_unrelated_newer_show() -> None:
    # The 2026-10-04 test: "The Field of Vision" is now listed as "Field of
    # Vision", and an unrelated show with a newer episode came back first.
    def search(_query: str) -> tuple[list[PodcastSearchResult], list[str]]:
        return (
            [
                PodcastSearchResult(title="Latent Space", feed_url="https://latent.example/f"),
                PodcastSearchResult(title="Field of Vision", feed_url="https://fov.example/f"),
            ],
            [],
        )

    show = PodcastShow(id="s", title="The Field of Vision", feed_url=OLD)
    found = new_feed_finder.find_new_feed(show, searcher=search, verifier=_verifier)
    assert [c.feed_url for c in found.candidates] == [
        "https://fov.example/f",
        "https://latent.example/f",
    ]


def test_nothing_found_is_said_plainly() -> None:
    found = new_feed_finder.find_new_feed(_show(), searcher=lambda _q: ([], []), verifier=_verifier)
    assert found.candidates == []
    assert found.summary("Living Blindfully") == (
        "No working feed for Living Blindfully was found in the podcast directories."
    )


def test_a_search_that_fails_is_a_sentence_not_an_exception() -> None:
    def broken(_query: str) -> tuple[list[PodcastSearchResult], list[str]]:
        raise TimeoutError("timed out")

    found = new_feed_finder.find_new_feed(_show(), searcher=broken, verifier=_verifier)
    assert found.candidates == []
    assert found.problems == [
        "The podcast directories did not answer. The host took too long to answer."
    ]


def test_replace_feed_keeps_the_history_and_starts_the_new_address_afresh() -> None:
    show = _show()
    library = PodcastLibrary(shows=[show])
    check_state.record_failure(library, show, reason="gone", kind="gone")
    check_state.record_failure(library, show, reason="gone", kind="gone")

    new_feed_finder.replace_feed(library, show, NEW)

    assert show.feed_url == NEW
    assert show.episodes[0].played is True
    assert check_state.failure_run(library, show) == 0
    assert check_state.failure_reason(library, show) == ""


def test_the_new_feeds_back_catalogue_is_not_announced_or_listed_twice() -> None:
    show = _show()
    library = PodcastLibrary(shows=[show])
    new_feed_finder.replace_feed(library, show, NEW)
    same_episode_new_id = PodcastEpisode(
        guid="new-host-300",
        title="Episode 300",
        audio_url="https://media.rss.example/300.mp3",
        published="Mon, 01 Jun 2026 08:00:00 GMT",
    )
    older = PodcastEpisode(
        guid="new-host-299",
        title="Episode 299",
        audio_url="https://media.rss.example/299.mp3",
        published="Mon, 25 May 2026 08:00:00 GMT",
    )
    info = FeedInfo(
        title="Living Blindfully",
        homepage="",
        artwork_url="",
        episodes=[same_episode_new_id, older],
    )

    read = feed_read.record_success(library, show, info)

    assert read.baseline is True
    assert read.arrived == []
    titles = [episode.title for episode in show.episodes]
    assert titles.count("Episode 300") == 1
    assert "Episode 299" in titles
    assert show.find_episode("old-1") is not None  # played state kept

    # ...and the read after that is ordinary again.
    newer = PodcastEpisode(
        guid="new-host-301",
        title="Episode 301",
        audio_url="https://media.rss.example/301.mp3",
        published="Mon, 08 Jun 2026 08:00:00 GMT",
    )
    info.episodes = [newer, same_episode_new_id, older]
    assert [e.guid for e in feed_read.record_success(library, show, info).arrived] == [
        "new-host-301"
    ]
