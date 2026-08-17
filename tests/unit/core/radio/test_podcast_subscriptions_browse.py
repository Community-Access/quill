"""The Subscriptions branch: where a subscribed podcast can finally be found.

Before this, Su&bscribe wrote into the shared library and the show was simply
*gone* from Quill Radio's point of view -- "It is waiting in Quill Cast" was
the whole answer ("how do I find those that are subscribed? That feels
weird."). Now Podcasts > Subscriptions lists the shared library as folders,
one per show, each expanding to its newest episodes; and the same menu slot
that subscribed a show unsubscribes it.

Isolation: QUILL_DATA_DIR (honoured because tests/conftest.py sets _DEV_BUILD).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio.browse_libraries import (
    _browse_apple,
    _browse_my_podcast_show,
    _browse_my_podcasts,
)
from quill.core.radio.podcast_follow import follow_feed, is_followed, unfollow_feed


@dataclass
class _Episode:
    title: str
    audio_url: str
    transcript_url: str = ""


@dataclass
class _Feed:
    episodes: list = field(default_factory=list)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    return tmp_path


def _feed_of(count: int) -> _Feed:
    return _Feed(
        episodes=[_Episode(f"Episode {n}", f"https://pod.example/{n}.mp3") for n in range(count)]
    )


# --- finding what you subscribed to -------------------------------------------


def test_the_podcasts_branch_leads_with_subscriptions(data_dir) -> None:
    nodes = _browse_apple([], safe_mode=True)
    assert nodes[0].label == "Subscriptions"
    assert nodes[0].node_id == "mypodcasts"
    assert nodes[0].is_folder


def test_subscribed_shows_list_as_folders_sorted_by_title(data_dir) -> None:
    follow_feed(data_dir, feed_url="https://b.example/feed", title="Zebra Cast")
    follow_feed(data_dir, feed_url="https://a.example/feed", title="Aardvark Hour")
    nodes = _browse_my_podcasts([], safe_mode=True)
    assert [n.label for n in nodes] == ["Aardvark Hour", "Zebra Cast"]
    # The node id carries the feed itself: opening a show needs no directory.
    assert nodes[0].node_id == "mypodcastshow:https://a.example/feed"
    assert all(n.is_folder for n in nodes)


def test_an_empty_library_lists_nothing(data_dir) -> None:
    assert _browse_my_podcasts([], safe_mode=True) == []


def test_a_show_expands_to_its_episodes(data_dir, monkeypatch) -> None:
    from quill.core.podcasts import feed_reader

    monkeypatch.setattr(feed_reader, "fetch_and_parse_feed", lambda url, **_kw: _feed_of(3))
    nodes = _browse_my_podcast_show(["https://a.example/feed"], safe_mode=False)
    assert [n.label for n in nodes] == ["Episode 0", "Episode 1", "Episode 2"]
    assert all(n.station is not None and n.station.is_recording for n in nodes)


def test_the_episode_cap_is_the_one_lite_setting(data_dir, monkeypatch) -> None:
    # Radio deliberately keeps one knob (Preferences: episodes listed per
    # subscribed podcast); retention, downloads and the full archive are
    # Quill Cast's job.
    from quill.core.podcasts import feed_reader
    from quill.core.radio.history import load_history, save_history

    monkeypatch.setattr(feed_reader, "fetch_and_parse_feed", lambda url, **_kw: _feed_of(40))
    history = load_history(data_dir)
    history.subscription_episode_limit = 5
    save_history(data_dir, history)
    nodes = _browse_my_podcast_show(["https://a.example/feed"], safe_mode=False)
    assert len(nodes) == 5
    assert nodes[0].label == "Episode 0"  # feeds publish newest-first: keep the head

    history.subscription_episode_limit = 0  # 0 = every episode the feed carries
    save_history(data_dir, history)
    assert len(_browse_my_podcast_show(["https://a.example/feed"], safe_mode=False)) == 40


def test_the_new_kinds_are_registered_and_named(data_dir) -> None:
    from quill.core.radio import row_actions

    assert "mypodcasts" in bs._HANDLERS
    assert "mypodcastshow" in bs._HANDLERS
    assert row_actions.contents_noun("mypodcasts") == "Shows"
    assert row_actions.contents_noun("mypodcastshow") == "Episodes"
    assert row_actions.is_podcast_show("mypodcastshow")


# --- unsubscribing, from the same slot that subscribed ---------------------------


def test_unfollow_removes_the_show_and_says_so(data_dir) -> None:
    follow_feed(data_dir, feed_url="https://a.example/feed", title="Aardvark Hour")
    assert is_followed(data_dir, "https://a.example/feed")
    result = unfollow_feed(data_dir, "https://a.example/feed")
    assert result.removed
    assert "Aardvark Hour" in result.spoken
    assert not is_followed(data_dir, "https://a.example/feed")


def test_unfollow_of_a_stranger_is_an_answer_not_a_failure(data_dir) -> None:
    result = unfollow_feed(data_dir, "https://never.example/feed")
    assert not result.removed
    assert "not in your subscriptions" in result.spoken
    assert unfollow_feed(data_dir, "").removed is False


def test_subscribe_stores_artwork_and_homepage_for_cast(data_dir) -> None:
    # A show followed from Radio used to arrive in Quill Cast as a bare
    # title; the subscribe path now hands the library a tile and site link.
    from quill.core.podcasts.subscriptions import load_library

    follow_feed(
        data_dir,
        feed_url="https://a.example/feed",
        title="Aardvark Hour",
        homepage="https://podcasts.apple.com/us/podcast/id1",
        artwork_url="https://art.example/600.jpg",
    )
    show = load_library(data_dir).find_show_by_feed_url("https://a.example/feed")
    assert show is not None
    assert show.homepage == "https://podcasts.apple.com/us/podcast/id1"
    assert show.artwork_url == "https://art.example/600.jpg"


def test_subscribe_announcement_names_the_subscriptions_folder(data_dir) -> None:
    # The old announcement ("It is waiting in Quill Cast") described a place
    # this app could not show; it must name the branch that now exists.
    added = follow_feed(data_dir, feed_url="https://a.example/feed", title="Aardvark Hour")
    again = follow_feed(data_dir, feed_url="https://a.example/feed", title="Aardvark Hour")
    assert "Subscriptions" in added.spoken
    assert "Subscriptions" in again.spoken and again.already
