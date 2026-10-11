"""The refresh after the Downcast import test (check.md bugs 2, 7 and 10).

``refresh_feed`` is driven with a fake host whose task manager runs the work at
once, and a fake feed reader -- so what is routed, announced and written down
can be asserted without wx or the network. Radio's own podcast check gets the
same first-read rule, tested through ``refresh_subscribed_feeds``.
"""

from __future__ import annotations

from types import SimpleNamespace
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


class _Deferred:
    def __init__(self) -> None:
        self.job: tuple[Any, Any, Any] | None = None

    def submit(self, _name: str, func: Any, *, on_success: Any, on_failure: Any) -> None:
        self.job = (func, on_success, on_failure)


class _Queued:
    def __init__(self) -> None:
        self.jobs: list[tuple[Any, Any, Any]] = []

    def submit(self, _name: str, func: Any, *, on_success: Any, on_failure: Any) -> None:
        self.jobs.append((func, on_success, on_failure))

    def shutdown(self, **_options: object) -> None:
        self.jobs.clear()


class _Later:
    def __init__(self) -> None:
        self.callbacks: list[Any] = []

    def CallLater(self, _delay: int, callback: Any) -> None:
        self.callbacks.append(callback)


class _Host:
    def __init__(self, show: PodcastShow) -> None:
        self._podcast_library = PodcastLibrary(shows=[show])
        self._safe_mode = False
        self._task_manager = _Now()
        self._podcast_manager_dialog = None
        self._podcast_history = None
        self._podcast_feed_tasks = None
        self._check_run = None
        self._podcast_check_monitor = SimpleNamespace(interrupt_speech=False)
        self._podcast_download_queue = SimpleNamespace(get=lambda *_args: object())
        self.spoken: list[str] = []
        self.routed: list[list[Any]] = []
        self.saved = 0
        self.maintenance_runs = 0
        self.flushes = 0
        self._podcast_library_dirty = False

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

    def podcast_run_maintenance(self) -> None:
        self.maintenance_runs += 1

    def _flush_podcast_library(self) -> None:
        self.flushes += 1
        self._podcast_library_dirty = False

    def __getattr__(self, name: str) -> Any:
        # Every other host hook is a no-op recorder.
        return lambda *_a, **_k: None


@pytest.fixture
def no_problem_log(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    from quill.core import problem_log

    written: list[tuple[Any, ...]] = []
    monkeypatch.setattr(problem_log, "record_problem", lambda *args, **kwargs: written.append(args))
    monkeypatch.setattr("quill.ui.podcasts.record_tasks.submit", lambda _host, _step, work: work())
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

    assert host.routed == []
    assert not [line for line in host.spoken if "new episode" in line.lower()]
    assert len(show.episodes) == 3
    assert host.saved == 1
    assert host.maintenance_runs == 1


def test_refresh_all_batches_maintenance_save_and_manager_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.ui.podcasts import check_run

    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(title="T", homepage="", artwork_url="", episodes=_episodes()),
    )
    monkeypatch.setattr("quill.ui.activity_window.report_result", lambda *_a, **_k: None)
    show = PodcastShow(id="s1", title="The Mayan Crystal", feed_url="https://rss.art19.com/m")
    host = _Host(show)

    class Manager:
        refreshes = 0

        def refresh_tree(self) -> None:
            self.refreshes += 1

    manager = Manager()
    host._podcast_manager_dialog = manager
    host._podcast_library_dirty = True
    check_run.start(host, ["s1", "s2"])

    feed_refresh.refresh_feed(host, "s1")

    assert host.maintenance_runs == 0
    assert host.flushes == 0
    assert manager.refreshes == 0

    check_run.step(host, "s2")

    assert host.maintenance_runs == 1
    assert host.flushes == 1
    assert manager.refreshes == 1


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
        assert feed_refresh.FEED_CHECK_WORKERS == 2
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


def test_individual_feed_refresh_coalesces_manager_rebuilds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show = PodcastShow(id="s1", title="The Mayan Crystal", feed_url="https://rss.art19.com/m")
    host = _Host(show)
    host._wx = _Later()

    class Manager:
        refreshes = 0

        def refresh_tree(self) -> None:
            self.refreshes += 1

    manager = Manager()
    host._podcast_manager_dialog = manager
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(title="T", homepage="", artwork_url="", episodes=[]),
    )

    feed_refresh.refresh_feed(host, "s1")
    feed_refresh.refresh_feed(host, "s1")

    assert manager.refreshes == 0
    assert len(host._wx.callbacks) == 1
    host._wx.callbacks[0]()
    assert manager.refreshes == 1


def test_feed_merge_filter_and_routing_run_before_the_ui_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = PodcastEpisode(guid="old", title="Old episode", audio_url="https://x/old.mp3")
    show = PodcastShow(
        id="s1",
        title="The Mayan Crystal",
        feed_url="https://rss.art19.com/m",
        auto_queue=True,
        episodes=[existing],
    )
    host = _Host(show)
    queued = _Queued()
    host._podcast_feed_tasks = queued
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(title="T", homepage="", artwork_url="", episodes=_episodes()),
    )

    feed_refresh.refresh_feed(host, "s1")
    fetch, fetched, _fetch_failed = queued.jobs.pop(0)
    fetched("fetch", fetch())

    assert [episode.guid for episode in show.episodes] == ["old"]
    assert host._podcast_library.queue == []
    prepare, prepared, _prepare_failed = queued.jobs.pop(0)
    result = prepare()

    assert [episode.guid for episode in show.episodes] == ["old"]
    assert host._podcast_library.queue == []
    assert result.queued == 3

    prepared("prepare", result)

    assert [episode.guid for episode in show.episodes] == ["old", "e1", "e2", "e3"]
    assert [item.episode_guid for item in host._podcast_library.queue] == ["e1", "e2", "e3"]


def test_feed_preparation_preserves_library_changes_before_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show = PodcastShow(id="s1", title="The Mayan Crystal", feed_url="https://rss.art19.com/m")
    host = _Host(show)
    queued = _Queued()
    host._podcast_feed_tasks = queued
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(title="T", homepage="", artwork_url="", episodes=_episodes()),
    )

    feed_refresh.refresh_feed(host, "s1")
    fetch, fetched, _fetch_failed = queued.jobs.pop(0)
    fetched("fetch", fetch())
    prepare, prepared, _prepare_failed = queued.jobs.pop(0)
    result = prepare()
    host._podcast_library_revision = 1
    show.is_favorite = True

    prepared("prepare", result)

    assert show.is_favorite
    assert [episode.guid for episode in show.episodes] == ["e1", "e2", "e3"]


def test_late_feed_result_is_discarded_when_show_was_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show = PodcastShow(id="s1", title="The Mayan Crystal", feed_url="https://rss.art19.com/m")
    host = _Host(show)
    deferred = _Deferred()
    host._task_manager = deferred
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_a, **_k: FeedInfo(title="T", homepage="", artwork_url="", episodes=_episodes()),
    )

    feed_refresh.refresh_feed(host, "s1")
    assert deferred.job is not None
    host._podcast_library.shows.clear()
    work, success, _failure = deferred.job
    success("op", work())

    assert host.saved == 0
    assert host.maintenance_runs == 0


def test_large_feed_snapshot_is_copied_in_bounded_ui_turns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show = PodcastShow(
        id="s1",
        title="Long-running show",
        feed_url="https://example.test/feed.xml",
        episodes=[
            PodcastEpisode(
                guid=f"e{index}",
                title=f"Episode {index}",
                audio_url=f"https://example.test/{index}.mp3",
            )
            for index in range(300)
        ],
    )
    host = _Host(show)
    host._wx = _Later()
    queued = _Queued()
    host._podcast_feed_tasks = queued
    copied_batches: list[int] = []
    original_deepcopy = feed_refresh.copy.deepcopy

    def track_deepcopy(value: Any) -> Any:
        if isinstance(value, list):
            copied_batches.append(len(value))
        return original_deepcopy(value)

    monkeypatch.setattr(feed_refresh.copy, "deepcopy", track_deepcopy)

    feed_refresh.refresh_feed(host, show.id)

    assert queued.jobs == []
    while host._wx.callbacks:
        host._wx.callbacks.pop(0)()

    assert max(copied_batches) <= feed_refresh.SNAPSHOT_EPISODES_PER_TURN
    assert sum(copied_batches) == len(show.episodes)
    assert len(queued.jobs) == 1


def test_refresh_commit_preserves_listener_state_changed_during_fetch() -> None:
    import copy

    from quill.ui.podcasts.feed_refresh import _commit_prepared_refresh, _PreparedRefresh

    episode = PodcastEpisode(
        guid="e1",
        title="Old feed title",
        audio_url="https://example.test/e1.mp3",
    )
    live_show = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://example.test/feed.xml",
        episodes=[episode],
    )
    live_library = PodcastLibrary(shows=[live_show])
    prepared_library = copy.deepcopy(live_library)
    prepared_show = prepared_library.shows[0]
    prepared_show.episodes[0].title = "Updated feed title"

    episode.played = True
    episode.position_ms = 42_000
    episode.downloaded_path = "episode.mp3"
    episode.mode_override = "stream"
    episode.position_updated_at = "2026-10-04T12:00:00+00:00"
    prepared = _PreparedRefresh(
        library=prepared_library,
        show_id="s1",
        read=object(),
        outcome=object(),
        fresh=[],
        queued=0,
        returned=[],
        queue_additions=[],
        assignment_changes={},
        assignment_before={},
        playlist_additions={},
        auto_download=[],
    )

    _commit_prepared_refresh(SimpleNamespace(_podcast_library=live_library), prepared)

    refreshed = live_show.episodes[0]
    assert refreshed.title == "Updated feed title"
    assert refreshed is episode
    assert refreshed.played
    assert refreshed.position_ms == 42_000
    assert refreshed.downloaded_path == "episode.mp3"
    assert refreshed.mode_override == "stream"
    assert refreshed.position_updated_at == "2026-10-04T12:00:00+00:00"


@pytest.mark.parametrize("change", ["stop", "remove", "replace_url"])
def test_late_failed_feed_check_cannot_change_live_state(change: str) -> None:
    show = PodcastShow(id="s1", title="Show", feed_url="https://example.test/feed")
    host = _Host(show)
    queued = _Queued()
    host._podcast_feed_tasks = queued
    feed_refresh.refresh_feed(host, show.id)
    _work, _success, failure = queued.jobs.pop()
    if change == "stop":
        feed_refresh.shutdown_feed_checks(host)
    elif change == "remove":
        host._podcast_library.shows.clear()
    else:
        show.feed_url = "https://example.test/replacement"
    failure("fetch", FeedReaderError("Temporary failure"))
    assert not host._podcast_library.show_check_state
    assert host.saved == 0


def test_refresh_working_set_is_detached_and_contains_no_other_show() -> None:
    show = PodcastShow(id="s1", title="Show", feed_url="https://example.test/feed")
    library = PodcastLibrary(shows=[show, PodcastShow(id="other", title="Other")])
    library.extra_settings["nested"] = {"values": [1]}
    library.show_labels["s1"] = ["original"]
    snapshot, _assignments, _playlists = feed_refresh._snapshot_for_refresh(library, show)
    snapshot.extra_settings["nested"]["values"].append(2)
    snapshot.show_labels["s1"].append("worker")
    snapshot.shows[0].title = "Changed off-thread"
    assert [item.id for item in snapshot.shows] == ["s1"]
    assert library.extra_settings["nested"] == {"values": [1]}
    assert library.show_labels["s1"] == ["original"]
    assert show.title == "Show"


def test_large_commit_yields_and_keeps_live_listener_and_object_state(monkeypatch) -> None:
    import copy

    from quill.ui.podcasts import refresh_commit

    show = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://example.test/feed",
        episodes=[
            PodcastEpisode(guid=f"e{index}", title="Old", audio_url="https://example.test/audio")
            for index in range(1500)
        ],
    )
    host = _Host(show)
    copied = copy.deepcopy(host._podcast_library)
    for episode in copied.shows[0].episodes:
        episode.title = "Updated"
    prepared = feed_refresh._PreparedRefresh(
        library=copied,
        show_id=show.id,
        read=None,
        outcome=None,
        fresh=[],
        queued=0,
        returned=[],
        queue_additions=[],
        assignment_changes={},
        assignment_before={},
        playlist_additions={},
        auto_download=[],
    )
    clock = iter(index * 0.01 for index in range(200))
    monkeypatch.setattr(refresh_commit, "perf_counter", lambda: next(clock))
    host._wx = _Later()
    original = show.episodes[0]
    completed: list[Any] = []
    failures: list[BaseException] = []
    refresh_commit.commit(
        host,
        prepared,
        active=lambda: True,
        completed=completed.append,
        failed=failures.append,
    )
    assert not completed and host._wx.callbacks
    original.played = True
    original.position_ms = 42000
    original.feed_title = "Old"
    original.title = "My title"
    while host._wx.callbacks:
        host._wx.callbacks.pop(0)()
    assert not failures
    assert completed == [show]
    assert show.episodes[0] is original
    assert original.title == "My title"
    assert original.feed_title == "Updated"
    assert original.played and original.position_ms == 42000


@pytest.mark.parametrize("change", ["remove_in_place", "remove_all", "append"])
def test_yielding_commit_cannot_overwrite_a_changed_episode_list(monkeypatch, change) -> None:
    import copy

    from quill.ui.podcasts import refresh_commit

    show = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://example.test/feed",
        episodes=[
            PodcastEpisode(guid=f"e{index}", title="Old", audio_url="https://example.test/audio")
            for index in range(400)
        ],
    )
    host = _Host(show)
    host._wx = _Later()
    prepared = feed_refresh._PreparedRefresh(
        library=copy.deepcopy(host._podcast_library),
        show_id=show.id,
        read=None,
        outcome=None,
        fresh=[],
        queued=0,
        returned=[],
        queue_additions=[],
        assignment_changes={},
        assignment_before={},
        playlist_additions={},
        auto_download=[],
        episode_before={episode.guid for episode in show.episodes},
    )
    clock = iter(index * 0.01 for index in range(200))
    monkeypatch.setattr(refresh_commit, "perf_counter", lambda: next(clock))
    completed: list[Any] = []
    failures: list[BaseException] = []
    refresh_commit.commit(
        host,
        prepared,
        active=lambda: True,
        completed=completed.append,
        failed=failures.append,
    )
    if change == "remove_in_place":
        show.episodes.pop(0)
    elif change == "remove_all":
        show.episodes.clear()
    else:
        show.episodes.append(
            PodcastEpisode(guid="arrived", title="Arrived", audio_url="https://example.test/new")
        )
    expected = list(show.episodes)
    while host._wx.callbacks:
        host._wx.callbacks.pop(0)()
    assert not failures
    assert completed == [None]
    assert show.episodes == expected
    assert host._podcast_commit_depth == 0


def test_refresh_reprepares_routing_when_auto_queue_changed_during_fetch(monkeypatch) -> None:
    show = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://example.test/feed",
        episodes=[PodcastEpisode("old", "Old", audio_url="https://example.test/old")],
    )
    host = _Host(show)
    pool = _Queued()
    host._podcast_feed_tasks = pool
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_args, **_kwargs: FeedInfo(
            title="T", homepage="", artwork_url="", episodes=_episodes()
        ),
    )
    feed_refresh.refresh_feed(host, show.id)
    fetch, fetched, _failed = pool.jobs.pop(0)
    fetched("fetch", fetch())
    prepare, prepared, _failed = pool.jobs.pop(0)
    result = prepare()
    show.auto_queue = True
    prepared("prepare", result)
    assert len(pool.jobs) == 1
    prepare, prepared, _failed = pool.jobs.pop(0)
    prepared("prepare", prepare())
    assert [item.episode_guid for item in host._podcast_library.queue] == ["e1", "e2", "e3"]


def test_routing_repreparation_does_not_restore_a_removed_catalogue(monkeypatch) -> None:
    show = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://example.test/feed",
        episodes=[PodcastEpisode("e1", "Old", audio_url="https://example.test/e1")],
    )
    host = _Host(show)
    pool = _Queued()
    host._podcast_feed_tasks = pool
    monkeypatch.setattr(
        feed_reader,
        "fetch_and_parse_feed",
        lambda *_args, **_kwargs: FeedInfo(
            title="T", homepage="", artwork_url="", episodes=_episodes()
        ),
    )
    feed_refresh.refresh_feed(host, show.id)
    fetch, fetched, _failed = pool.jobs.pop(0)
    fetched("fetch", fetch())
    prepare, prepared, _failed = pool.jobs.pop(0)
    result = prepare()
    show.episodes.clear()
    show.auto_queue = True
    prepared("prepare", result)
    prepare, prepared, _failed = pool.jobs.pop(0)
    prepared("prepare", prepare())

    assert [episode.guid for episode in show.episodes] == ["e2", "e3"]
    assert all(item.episode_guid != "e1" for item in host._podcast_library.queue)
