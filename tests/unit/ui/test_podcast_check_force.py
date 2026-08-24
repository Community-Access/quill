"""Force, pause, and the shared stamp, across both apps' refresh paths.

A pause is only safe to offer because Refresh on the row in front of you always
works. That promise lives in three places -- the pure policy, Quill Radio's
worker, and QUILL Cast's monitor -- and it had been broken in the middle one:
``refresh_subscribed_feeds`` took ``force``, documented it, and never passed it
to :func:`~quill.core.podcasts.refresh_policy.shows_to_refresh`, so a forced
check silently skipped exactly the shows it existed for.

The other half is the shared ``last_auto_check`` stamp. Both apps read one
library and each keeps its own cadence -- a single shared switch would mean
enabling the check in Cast enabled it in Radio with no way to say "let the
other one do it" -- so the stamp is what stops two timers from asking one
publisher twice. It has to be claimed *before* the fetch, not after.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.podcasts import refresh_policy
from quill.core.podcasts.subscriptions import PodcastLibrary, PodcastShow, save_library
from quill.ui.radio import podcast_refresh


class _Episodes:
    def __init__(self, episodes: list | None = None) -> None:
        self.episodes = episodes or []
        self.tags = _Tags()


class _Tags:
    is_empty = True


@pytest.fixture
def library(tmp_path, monkeypatch):
    """A two-show library on disk, one of them paused."""
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    live = PodcastShow(id="live", title="The Daily", feed_url="https://example.com/a.xml")
    paused = PodcastShow(id="paused", title="Main Menu", feed_url="https://example.com/b.xml")
    paused.paused = True
    store = PodcastLibrary(shows=[live, paused])
    save_library(tmp_path, store)
    return tmp_path


def _record_fetches(monkeypatch) -> list[str]:
    asked: list[str] = []

    def _fetch(url: str, **_kwargs: Any):
        asked.append(url)
        return _Episodes()

    monkeypatch.setattr("quill.core.podcasts.feed_reader.fetch_and_parse_feed", _fetch)
    monkeypatch.setattr(
        "quill.core.podcasts.feed_auth.auth_for_url", lambda *_args, **_kwargs: ("", "")
    )
    return asked


# -- Radio's worker -------------------------------------------------------------


def test_the_automatic_check_leaves_the_paused_show_alone(library, monkeypatch) -> None:
    asked = _record_fetches(monkeypatch)

    found = podcast_refresh.refresh_subscribed_feeds()

    assert asked == ["https://example.com/a.xml"]
    assert [title for title, _count in (found or [])] == ["The Daily"]


def test_a_forced_check_asks_the_paused_show_too(library, monkeypatch) -> None:
    """The regression: ``force`` was accepted, documented, and then dropped."""
    asked = _record_fetches(monkeypatch)

    found = podcast_refresh.refresh_subscribed_feeds(force=True)

    assert asked == ["https://example.com/a.xml", "https://example.com/b.xml"]
    assert [title for title, _count in (found or [])] == ["The Daily", "Main Menu"]


def test_a_show_with_no_feed_is_never_asked_however_hard_you_press(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    local = PodcastShow(id="local", title="Voice Memos", feed_url="")
    save_library(tmp_path, PodcastLibrary(shows=[local]))
    asked = _record_fetches(monkeypatch)

    assert podcast_refresh.refresh_subscribed_feeds(force=True) == []
    assert asked == []


def test_one_bad_feed_never_stops_the_rest(library, monkeypatch) -> None:
    def _fetch(url: str, **_kwargs: Any):
        if url.endswith("a.xml"):
            raise RuntimeError("that host is down")
        return _Episodes()

    monkeypatch.setattr("quill.core.podcasts.feed_reader.fetch_and_parse_feed", _fetch)
    monkeypatch.setattr(
        "quill.core.podcasts.feed_auth.auth_for_url", lambda *_args, **_kwargs: ("", "")
    )

    found = podcast_refresh.refresh_subscribed_feeds(force=True)

    assert [title for title, _count in (found or [])] == ["Main Menu"]


# -- the shared stamp -----------------------------------------------------------


def test_a_check_the_other_app_just_ran_is_skipped_and_says_so_by_returning_none(
    library, monkeypatch
) -> None:
    import time

    from quill.core.podcasts.subscriptions import load_library

    store = load_library(library)
    store.last_auto_check = refresh_policy.stamp_now(time.time())
    save_library(library, store)
    asked = _record_fetches(monkeypatch)

    assert podcast_refresh.refresh_subscribed_feeds(only_if_due_minutes=60) is None
    assert asked == []


def test_the_round_is_claimed_before_the_fetch_not_after(library, monkeypatch) -> None:
    """Two timers in the same second must not both decide they are the one.

    The fetches take seconds, during which a stamp written afterwards would
    still read as stale to the other app.
    """
    from quill.core.podcasts.subscriptions import load_library

    stamped_when_asked: list[str] = []

    def _fetch(_url: str, **_kwargs: Any):
        stamped_when_asked.append(str(load_library(library).last_auto_check))
        return _Episodes()

    monkeypatch.setattr("quill.core.podcasts.feed_reader.fetch_and_parse_feed", _fetch)
    monkeypatch.setattr(
        "quill.core.podcasts.feed_auth.auth_for_url", lambda *_args, **_kwargs: ("", "")
    )

    podcast_refresh.refresh_subscribed_feeds(only_if_due_minutes=60)

    assert stamped_when_asked and all(stamped_when_asked)


def test_a_forced_check_never_defers_to_the_stamp(library, monkeypatch) -> None:
    import time

    from quill.core.podcasts.subscriptions import load_library

    store = load_library(library)
    store.last_auto_check = refresh_policy.stamp_now(time.time())
    save_library(library, store)
    asked = _record_fetches(monkeypatch)

    found = podcast_refresh.refresh_subscribed_feeds(force=True)

    assert found is not None
    assert len(asked) == 2


def test_the_stamp_survives_a_save_and_load(library) -> None:
    from quill.core.podcasts.subscriptions import load_library

    store = load_library(library)
    store.last_auto_check = refresh_policy.stamp_now(1_700_000_000.0)
    save_library(library, store)

    assert load_library(library).last_auto_check == store.last_auto_check
