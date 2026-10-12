"""qc.md F-10: Refresh All Now finishes out loud, once, and F9 can repeat it."""

from __future__ import annotations

from quill.core import activity
from quill.ui.podcasts import check_run


class _Host:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.retried = 0

    def _announce(self, message: str, **_kw: object) -> None:
        self.said.append(message)

    def _on_check_all_feeds(self) -> None:
        self.retried += 1


def test_a_run_says_milestones_and_one_result(monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda *_a, **_k: False)
    host = _Host()
    ids = [f"s{i}" for i in range(4)]
    check_run.start(host, ids)
    check_run.step(host, "s0", new_episodes=2)
    check_run.step(host, "elsewhere", new_episodes=9)  # not part of this run
    check_run.step(host, "s1")
    check_run.step(host, "s2", failed_title="Broken Feed")
    assert host.said == [
        "Checking feeds, 25 percent",
        "Checking feeds, 50 percent",
        "Checking feeds, 75 percent",
    ]
    check_run.step(host, "s3", new_episodes=1)
    assert (
        host.said[-1]
        == "Checked 4 feeds: 3 new episodes from 2 podcasts. 1 could not be read: Broken Feed."
    )
    latest = activity.LOG.latest_important()
    assert latest is not None and latest.has("retry")
    assert host._check_run is None


def test_nothing_new_is_said_as_such() -> None:
    run = check_run.CheckRun(total=2)
    assert check_run.finish_sentence(run) == "Checked 2 feeds: nothing new."


def test_run_flushes_library_and_refreshes_manager_once_at_completion(monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.activity_window.report_result", lambda *_a, **_k: None)

    class Manager:
        def __init__(self) -> None:
            self.refreshes = 0

        def refresh_tree(self) -> None:
            self.refreshes += 1

    class Host(_Host):
        def __init__(self) -> None:
            super().__init__()
            self.events: list[str] = []
            self._podcast_library_dirty = True
            self._podcast_manager_dialog = Manager()

        def podcast_run_maintenance(self) -> None:
            assert self._check_run is None
            self.events.append("maintenance")

        def _flush_podcast_library(self) -> None:
            assert self._check_run is None
            self.events.append("flush")
            self._podcast_library_dirty = False

    host = Host()
    check_run.start(host, ["s1", "s2"])
    check_run.step(host, "s1")
    assert host.events == []
    assert host._podcast_manager_dialog.refreshes == 0

    check_run.step(host, "s2")

    assert host.events == ["maintenance", "flush"]
    assert host._podcast_manager_dialog.refreshes == 1
    assert host._check_run is None


def test_completion_publishes_pending_tree_even_after_a_periodic_save(monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.activity_window.report_result", lambda *_a, **_k: None)
    host = _Host()
    host._podcast_library_dirty = False
    host._tree_reload_pending = True
    updates = []

    def flush():
        assert host._check_run is None
        updates.append("tree")
        host._tree_reload_pending = False

    host._flush_podcast_library = flush
    check_run.start(host, ["s1"])
    check_run.step(host, "s1")
    check_run.step(host, "s1")
    assert updates == ["tree"]


def test_cancel_stops_queued_and_running_feeds_without_waiting(monkeypatch) -> None:
    results = []
    monkeypatch.setattr(
        "quill.ui.activity_window.report_result",
        lambda _host, result, _actions: results.append(result),
    )

    class Monitor:
        def cancel_all(self):
            return ["s1", "s2", "s3"]

        def refresh_completed(self, _show_id):
            return

    host = _Host()
    host._podcast_check_monitor = Monitor()
    check_run.start(host, ["s1", "s2", "s3"])

    check_run.cancel_remaining(host)
    assert host._check_run is None

    check_run.step(host, "s1", new_episodes=1)

    assert host._check_run is None
    assert len(results) == 1
    assert results[0].outcome == activity.CANCELLED
    assert results[0].summary == "Stopped. Checked 0 of 3 feeds: nothing new."
