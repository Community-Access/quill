"""Cast's checks of many feeds run as one bounded batch (F-09).

The UI half of ``core/podcasts/refresh_batch.py``: the background tick and Check
All Feeds Now hand every due podcast to :func:`feed_refresh.refresh_feeds`,
which runs three at a time, speaks a manual check's milestones and end once,
merges a second request into the running check, stops on one verb (and on
close), and tells each fetch its deadline and how to know it was stopped.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.stability.task_manager import CancelledError
from quill.ui.podcasts import feed_refresh
from quill.ui.podcasts.check_monitor import PodcastCheckMonitor


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []
        self._safe_mode = False

    def _announce(self, message: str, **_kw: Any) -> None:
        self.said.append(message)


@pytest.fixture
def fetches(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Every refresh_feed the batch starts, with what it was given."""
    started: list[dict[str, Any]] = []

    def fake_refresh_feed(host: Any, show_id: str, **kwargs: Any) -> None:
        started.append({"show_id": show_id, **kwargs})

    monkeypatch.setattr(feed_refresh, "refresh_feed", fake_refresh_feed)
    return started


def _answer(fetch: dict[str, Any], **kwargs: Any) -> None:
    fetch["on_done"](fetch["show_id"], **kwargs)


def test_a_manual_check_runs_three_at_a_time_and_speaks_its_end_once(fetches) -> None:
    host = _Host()
    assert feed_refresh.refresh_feeds(host, ["a", "b", "c", "d", "e"], manual=True) == 5
    assert [f["show_id"] for f in fetches] == ["a", "b", "c"]
    assert fetches[0]["deadline_seconds"] == 60.0
    assert fetches[0]["is_cancelled"]() is False
    _answer(fetches[0], ok=True, new_episodes=2)
    assert [f["show_id"] for f in fetches] == ["a", "b", "c", "d"]
    for fetch in fetches[1:]:
        _answer(fetch, ok=fetch["show_id"] != "c")
    _answer(fetches[-1], ok=True)  # "e", started when "d" answered
    assert host.said == ["Finished checking 5 feeds. 1 failed; Feed Check lists them."]
    assert getattr(host, "_podcast_refresh_batch", None) is None


def test_the_background_check_stays_quiet(fetches) -> None:
    host = _Host()
    feed_refresh.refresh_feeds(host, ["a"], manual=False)
    _answer(fetches[0], ok=True)
    assert host.said == []


def test_a_second_request_joins_the_running_check_instead_of_doubling_it(fetches) -> None:
    host = _Host()
    feed_refresh.refresh_feeds(host, ["a", "b", "c", "d"], manual=False)
    assert feed_refresh.refresh_feeds(host, ["a", "d", "e"], manual=True) == 1
    batch = host._podcast_refresh_batch
    assert batch.total == 5 and batch.speak_progress is True


def test_stop_ends_the_check_and_says_how_far_it_got(fetches) -> None:
    host = _Host()
    feed_refresh.refresh_feeds(host, [f"s{i}" for i in range(10)], manual=True)
    _answer(fetches[0], ok=True)
    assert feed_refresh.stop_feed_checks(host) is True
    assert fetches[1]["is_cancelled"]() is True
    for fetch in fetches[1:]:
        _answer(fetch, ok=False, stopped=True)
    assert len(fetches) == 4  # nothing started after the stop
    assert host.said == ["Stopped checking feeds. 1 of 10 feeds were checked."]
    assert feed_refresh.stop_feed_checks(host) is False
    assert host.said[-1] == "No feed check is running."


def test_stopping_on_close_is_silent(fetches) -> None:
    host = _Host()
    feed_refresh.refresh_feeds(host, ["a", "b"], manual=True)
    feed_refresh.stop_feed_checks(host, announce=False)
    for fetch in fetches:
        _answer(fetch, ok=False, stopped=True)
    assert host.said == []


def test_check_all_feeds_while_one_is_running_says_where_it_is(fetches) -> None:
    host = _Host()
    feed_refresh.refresh_feeds(host, ["a", "b"], manual=False)
    host._podcast_check_monitor = SimpleNamespace(check_now=lambda force: 0)
    assert feed_refresh.check_all_feeds(host) == 0
    assert host.said == ["Already checking feeds. Checked 0 of 2 feeds."]


def test_check_all_feeds_counts_up_front(fetches) -> None:
    host = _Host()
    host._podcast_check_monitor = SimpleNamespace(check_now=lambda force: 1500)
    assert feed_refresh.check_all_feeds(host) == 1500
    assert host.said == ["Checking 1,500 feeds..."]


def test_the_monitor_hands_every_due_podcast_to_the_batch_at_once() -> None:
    shows = [
        PodcastShow(id=f"s{i}", title=f"S{i}", feed_url=f"https://example.invalid/{i}")
        for i in range(5)
    ]
    library = PodcastLibrary(shows=shows)
    handed: list[tuple[list[str], bool]] = []
    singles: list[str] = []
    monitor = PodcastCheckMonitor.__new__(PodcastCheckMonitor)
    monitor._library_provider = lambda: library
    monitor._refresh_show = singles.append
    monitor._refresh_many = lambda ids, manual: handed.append((ids, manual)) or len(ids)
    monitor._enabled = lambda: True  # type: ignore[method-assign]
    monitor._manually_allowed = lambda: True  # type: ignore[method-assign]
    monitor._tick = lambda: None  # type: ignore[method-assign]
    assert monitor.check_now(force=True) == 5
    assert handed == [([f"s{i}" for i in range(5)], True)]
    assert singles == []


# -- one feed tells its batch how it ended ------------------------------------------ #


class _Tasks:
    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> Any:
        self.jobs.append({"name": name, "func": func, **kwargs})
        return SimpleNamespace(operation_id=str(len(self.jobs)))


class _RefreshHost(_Host):
    def __init__(self, show: PodcastShow) -> None:
        super().__init__()
        self._podcast_library = PodcastLibrary(shows=[show])
        self._task_manager = _Tasks()
        self._podcast_manager_dialog = None
        self._podcast_check_monitor = SimpleNamespace(interrupt_speech=False)
        self.index_changes: list[str | None] = []

    def podcast_search_index_changed(self, show_id: str | None = None) -> None:
        self.index_changes.append(show_id)

    def _podcast_filter_new_episodes(self, _show: Any, arrived: list) -> Any:
        return SimpleNamespace(any_filtered=False, arrived=arrived)

    def _podcast_filter_scope(self, _show: Any, outcome: Any, _scope: str) -> list:
        return list(outcome.arrived)

    def _podcast_route_new_episodes(self, _show: Any, _episodes: list) -> int:
        return 0

    def _podcast_file_to_default_playlist(self, *_a: Any) -> None:
        pass

    def _podcast_resurface_republished(self, *_a: Any) -> None:
        pass

    def _save_podcast_library(self) -> None:
        pass

    def _podcast_new_episode_message(self, _show: Any, count: int, _queued: int) -> str:
        return f"{count} new"

    def _podcast_notify_new_episodes(self, *_a: Any) -> None:
        pass

    def _podcast_announce_episode_filter(self, *_a: Any) -> None:
        pass

    def _podcast_apply_auto_download(self, _show: Any) -> None:
        pass

    def podcast_run_maintenance(self) -> None:
        pass


@pytest.fixture
def show() -> PodcastShow:
    return PodcastShow(id="p", title="Pod", feed_url="https://example.invalid/p")


def test_a_merged_feed_reports_its_new_episodes_and_refreshes_the_search_index(
    show, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _kind: True)
    host = _RefreshHost(show)
    done: list[tuple[str, dict]] = []
    feed_refresh.refresh_feed(host, "p", on_done=lambda sid, **kw: done.append((sid, kw)))
    job = host._task_manager.jobs[0]
    info = SimpleNamespace(
        tags=SimpleNamespace(is_empty=True),
        episodes=[PodcastEpisode(guid="n1", title="New", audio_url="")],
    )
    job["on_success"]("op", info)
    assert done == [("p", {"ok": True, "new_episodes": 1})]
    assert host.index_changes == ["p"]


def test_a_stopped_fetch_is_not_recorded_as_a_failure(show, monkeypatch) -> None:
    recorded: list[Any] = []
    monkeypatch.setattr("quill.core.problem_log.record_problem", lambda *a, **k: recorded.append(a))
    host = _RefreshHost(show)
    done: list[tuple[str, dict]] = []
    feed_refresh.refresh_feed(host, "p", on_done=lambda sid, **kw: done.append((sid, kw)))
    host._task_manager.jobs[0]["on_failure"]("op", CancelledError("stopped"))
    assert done == [("p", {"ok": False, "stopped": True})]
    assert recorded == [] and host.said == []


def test_a_failed_fetch_is_recorded_and_reported_failed(show, monkeypatch) -> None:
    recorded: list[Any] = []
    monkeypatch.setattr("quill.core.problem_log.record_problem", lambda *a, **k: recorded.append(a))
    host = _RefreshHost(show)
    done: list[tuple[str, dict]] = []
    feed_refresh.refresh_feed(host, "p", on_done=lambda sid, **kw: done.append((sid, kw)))
    host._task_manager.jobs[0]["on_failure"]("op", OSError("down"))
    assert done == [("p", {"ok": False})]
    assert len(recorded) == 1


def test_a_podcast_that_cannot_be_fetched_still_frees_its_slot(show) -> None:
    host = _RefreshHost(show)
    done: list[tuple[str, dict]] = []
    feed_refresh.refresh_feed(host, "missing", on_done=lambda sid, **kw: done.append((sid, kw)))
    assert done == [("missing", {"ok": False, "stopped": True})]
    assert host._task_manager.jobs == []
