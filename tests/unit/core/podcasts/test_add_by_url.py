"""Add a podcast by pasting its feed address: one validator, human answers.

Every way the moment can go wrong has a different fix, so every refusal is
pinned as a sentence naming that fix -- a typo, a page instead of a feed, a
feed behind a sign-in, a site that is down, a feed with nothing to play.
And the empty Subscriptions branch offers the three ways in, as rows that
vanish the moment the library holds anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts import add_by_url
from quill.core.podcasts.feed_reader import FeedAuthError, FeedInfo, FeedReaderError
from quill.core.podcasts.models import PodcastEpisode
from quill.core.podcasts.subscriptions import load_library

FEED = "https://feeds.example/show.xml"


def _feed_info(*, title: str = "The Show", episodes: int = 2) -> FeedInfo:
    return FeedInfo(
        title=title,
        homepage="https://example.com",
        artwork_url="",
        episodes=[
            PodcastEpisode(guid=f"g{i}", title=f"Ep {i}", audio_url=f"https://cdn.example/{i}.mp3")
            for i in range(episodes)
        ],
    )


def _patch_fetch(monkeypatch: pytest.MonkeyPatch, result) -> list[str]:
    calls: list[str] = []

    def _fake(url: str, **_kw):
        calls.append(url)
        if isinstance(result, Exception):
            raise result
        return result

    from quill.core.podcasts import feed_reader

    monkeypatch.setattr(feed_reader, "fetch_and_parse_feed", _fake)
    return calls


def test_a_blank_and_a_non_address_each_get_their_own_sentence(tmp_path: Path) -> None:
    assert add_by_url.add_podcast_by_url(tmp_path, "  ").spoken == (
        "Paste or type the feed's web address first."
    )
    outcome = add_by_url.add_podcast_by_url(tmp_path, "the daily")
    assert not outcome.ok
    assert "does not look like a web address" in outcome.spoken
    assert "RSS or Subscribe" in outcome.spoken


def test_http_is_quietly_tried_as_https(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_fetch(monkeypatch, _feed_info())
    outcome = add_by_url.add_podcast_by_url(tmp_path, "http://feeds.example/show.xml")
    assert outcome.ok
    assert calls == ["https://feeds.example/show.xml"]


def test_safe_mode_refuses_before_the_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _patch_fetch(monkeypatch, _feed_info())
    outcome = add_by_url.add_podcast_by_url(tmp_path, FEED, safe_mode=True)
    assert not outcome.ok
    assert "Safe Mode" in outcome.spoken
    assert calls == []


def test_a_signed_in_feed_points_at_cast_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fetch(monkeypatch, FeedAuthError("401"))
    outcome = add_by_url.add_podcast_by_url(tmp_path, FEED)
    assert not outcome.ok
    assert "sign-in" in outcome.spoken
    assert "Quill Cast" in outcome.spoken


def test_an_unreachable_feed_blames_the_address_not_the_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fetch(monkeypatch, FeedReaderError("The connection timed out."))
    outcome = add_by_url.add_podcast_by_url(tmp_path, FEED)
    assert not outcome.ok
    assert "could not be read as a feed" in outcome.spoken
    assert "typos" in outcome.spoken


def test_a_web_page_and_an_audioless_feed_are_told_apart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fetch(monkeypatch, FeedInfo(title="", homepage="", artwork_url="", episodes=[]))
    page = add_by_url.add_podcast_by_url(tmp_path, FEED)
    assert "a web page, not a podcast feed" in page.spoken

    _patch_fetch(monkeypatch, _feed_info(title="Daily News", episodes=0))
    newsy = add_by_url.add_podcast_by_url(tmp_path, FEED)
    assert "no playable episodes" in newsy.spoken
    assert "Daily News" in newsy.spoken
    assert load_library(tmp_path).shows == []


def test_success_subscribes_and_lists_the_episodes_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fetch(monkeypatch, _feed_info(episodes=3))
    outcome = add_by_url.add_podcast_by_url(tmp_path, FEED)
    assert outcome.ok
    assert "Subscribed to The Show" in outcome.spoken
    assert "3 episodes" in outcome.spoken
    assert "Quill Cast" in outcome.spoken
    show = load_library(tmp_path).find_show_by_feed_url(FEED)
    assert show is not None
    assert len(show.episodes) == 3  # synced now, not empty-until-refresh

    again = add_by_url.add_podcast_by_url(tmp_path, FEED)
    assert again.ok
    assert "already follow" in again.spoken


def test_an_empty_subscriptions_branch_offers_the_three_ways_in(tmp_path: Path) -> None:
    from quill.core.radio.browse_libraries import _my_podcast_level

    rows = _my_podcast_level(load_library(tmp_path), None)
    assert [r.node_id for r in rows] == ["addpodcasturl", "importpodcastsopml", "searchpodcasts"]
    assert all(r.is_action for r in rows)


def test_the_fillers_vanish_once_anything_is_subscribed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import paths
    from quill.core.radio.browse_libraries import _my_podcast_level

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    _patch_fetch(monkeypatch, _feed_info())
    add_by_url.add_podcast_by_url(tmp_path, FEED)
    rows = _my_podcast_level(load_library(tmp_path), None)
    assert [r.node_id for r in rows] == [f"mypodcastshow:{FEED}"]
