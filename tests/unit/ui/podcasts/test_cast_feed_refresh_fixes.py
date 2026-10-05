"""The refresh after the Downcast import test (check.md bugs 2, 7 and 10).

``refresh_feed`` is driven with a fake host whose task manager runs the work at
once, and a fake feed reader -- so what is routed, announced and written down
can be asserted without wx or the network. Radio's own podcast check gets the
same first-read rule, tested through ``refresh_subscribed_feeds``.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.podcasts import check_state, feed_reader
from quill.core.podcasts.feed_reader import FeedInfo, FeedReaderError
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts import feed_refresh


def _episodes() -> list[PodcastEpisode]:
    return [
        PodcastEpisode(
            guid=f"e{n}",
            title=f"Episode {n}",
            audio_url=f"https://art19.example/{n}.mp3",
            published=f"Mon, 0{n} Apr 2018 08:00:00 GMT",
        )
        for n in range(1, 4)
    ]


class _Now:
    """A task manager that runs the work straight away, on this thread."""

    def submit(self, _name: str, func: Any, *, on_success: Any, on_failure: Any) -> None:
        try:
            result = func()
        except Exception as error:  # noqa: BLE001
            on_failure("op", error)
        else:
            on_success("op", result)


class _Host:
    def __init__(self, show: PodcastShow) -> None:
        self._podcast_library = PodcastLibrary(shows=[show])
        self._safe_mode = False
        self._task_manager = _Now()
        self._podcast_manager_dialog = None
        self._podcast_history = None
        self._podcast_feed_tasks = None
        self._check_run = None
        self.spoken: list[str] = []
        self.routed: list[list[Any]] = []
        self.saved = 0

    def _announce(self, message: str, **_kwargs: object) -> None:
        self.spoken.append(message)

    def _podcast_filter_new_episodes(self, _show: Any, arrived: list[Any]) -> Any:
        from types import SimpleNamespace

        return SimpleNamespace(arrived=list(arrived), any_filtered=False)

    def _podcast_filter_scope(self, _show: Any, outcome: Any, _scope: str) -> list[Any]:
        return list(outcome.arrived)

    def _podcast_route_new_episodes(self, _show: Any, episodes: list[Any]) -> int:
        self.routed.append(list(episodes))
        return 0

    def _save_podcast_library(self) -> None:
        self.saved += 1

    def __getattr__(self, name: str) -> Any:
        # Every other host hook is a no-op recorder.
        return lambda *_a, **_k: None


@pytest.fixture
def no_problem_log(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    from quill.core import problem_log

    written: list[tuple[Any, ...]] = []
    monkeypatch.setattr(problem_log, "record_problem", lambda *args, **kwargs: written.append(args))
    return written


def test_an_imported_shows_first_check_routes_and_announces_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show = PodcastShow(id="s1", title="The Mayan Crystal", feed_url="https://rss.art19.com/m")
    host = _Host(show)
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(title="T", homepage="", artwork_url="", episodes=_episodes()),
    )

    feed_refresh.refresh_feed(host, "s1")

    assert host.routed == [[]]
    assert not [line for line in host.spoken if "new episode" in line.lower()]
    assert len(show.episodes) == 3
    assert host.saved == 1


def test_a_failure_is_written_down_in_plain_words(
    monkeypatch: pytest.MonkeyPatch, no_problem_log: list[tuple[Any, ...]]
) -> None:
    show = PodcastShow(id="s1", title="Alex Jones Show", feed_url="http://xml.nfowars.net/A.rss")
    host = _Host(show)

    def _gone(*_a: object, **_k: object) -> FeedInfo:
        raise FeedReaderError("This podcast's web address no longer exists.", kind="no_such_host")

    monkeypatch.setattr(feed_reader, "fetch_and_parse_feed", _gone)

    feed_refresh.refresh_feed(host, "s1")

    library = host._podcast_library
    assert check_state.failure_reason(library, show) == (
        "This podcast's web address no longer exists."
    )
    detail = no_problem_log[-1][3]
    assert detail == "This podcast's web address no longer exists."
    assert "[QUILL" not in detail


def test_feed_checks_get_their_own_pool_not_the_shared_workers() -> None:
    from types import SimpleNamespace

    from quill.stability.task_manager import TaskManager

    shared = TaskManager(max_workers=4)
    host = SimpleNamespace(_task_manager=shared)
    try:
        pool = feed_refresh.feed_check_pool(host)
        assert isinstance(pool, TaskManager)
        assert pool is not shared
        assert feed_refresh.feed_check_pool(host) is pool  # made once
        assert pool._executor._max_workers == feed_refresh.FEED_CHECK_WORKERS
    finally:
        feed_refresh.shutdown_feed_checks(host)
        shared.shutdown(wait=False)


def test_a_test_double_keeps_receiving_the_submission() -> None:
    from types import SimpleNamespace

    fake = _Now()
    assert feed_refresh.feed_check_pool(SimpleNamespace(_task_manager=fake)) is fake


def test_radios_check_treats_a_first_read_as_a_starting_point(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    from quill.core import paths
    from quill.core.podcasts.subscriptions import load_library, save_library
    from quill.ui.radio import podcast_refresh

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    show = PodcastShow(id="s1", title="The Mayan Crystal", feed_url="https://rss.art19.com/m")
    save_library(tmp_path, PodcastLibrary(shows=[show]))
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(title="T", homepage="", artwork_url="", episodes=_episodes()),
    )

    found = podcast_refresh.refresh_subscribed_feeds(force=True)

    assert found is not None
    assert [row.new_count for row in found] == [0]
    # ...and the episodes it did bring were saved, not lost with the count.
    assert len(load_library(tmp_path).shows[0].episodes) == 3
