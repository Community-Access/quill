"""Responsiveness and ordering contracts for large Cast library saves."""

from __future__ import annotations

from concurrent.futures import Future, TimeoutError
from types import SimpleNamespace
from typing import Any

import pytest

from quill.ui import main_frame_podcast_save as save_ui


class _Timer:
    def __init__(self) -> None:
        self.running = False

    def IsRunning(self) -> bool:
        return self.running

    def Stop(self) -> None:
        self.running = False


class _TaskManager:
    def __init__(self) -> None:
        self.submissions: list[tuple[Any, Any, Any, Any]] = []

    def submit(self, name: str, func: Any, *, on_success: Any, on_failure: Any) -> object:
        task = object()
        self.submissions.append((task, func, on_success, on_failure))
        return task


class _Host(save_ui.PodcastLibrarySaveMixin):
    def __init__(self) -> None:
        self._podcast_library = SimpleNamespace(
            shows=[
                SimpleNamespace(episodes=[object()] * (save_ui.COALESCE_SAVE_ABOVE_EPISODES + 1))
            ],
            settings=SimpleNamespace(
                reconnect_enabled=True, reconnect_max_attempts=2, reconnect_wait_seconds=1
            ),
        )
        self._podcast_library_dirty = True
        self._podcast_save_timer = _Timer()
        self._task_manager = _TaskManager()
        self._podcast_save_task = None
        self.announcements: list[str] = []
        self._podcast_download_queue = SimpleNamespace(set_reconnect_settings=lambda **_kw: None)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)


@pytest.mark.parametrize("count, expected", [(19_999, False), (20_000, False), (20_001, True)])
def test_large_threshold_keeps_its_exact_boundary(count, expected):
    host = _Host()
    host._podcast_library.shows[0].episodes = [None] * count
    assert host._podcast_library_is_large() is expected


def test_large_threshold_does_not_count_irrelevant_remaining_shows():
    host = _Host()

    class UnneededEpisodes:
        def __len__(self):
            pytest.fail("A threshold decision counted the rest of a large catalogue")

    host._podcast_library.shows.append(SimpleNamespace(episodes=UnneededEpisodes()))
    assert host._podcast_library_is_large()


def test_large_timer_flush_submits_blocked_write_without_waiting(monkeypatch: Any) -> None:
    host = _Host()
    entered = False

    def blocked_write(*_args: Any, **_kwargs: Any) -> None:
        nonlocal entered
        entered = True
        raise AssertionError("the write must not run on the UI thread")

    monkeypatch.setattr(save_ui, "save_library", blocked_write)

    host._flush_podcast_library()

    assert not entered
    assert len(host._task_manager.submissions) == 1
    assert host._podcast_library_dirty


def test_small_mutation_marks_dirty_and_saves_on_a_worker(monkeypatch: Any) -> None:
    host = _Host()
    host._podcast_library.shows[0].episodes = []
    host._podcast_library_dirty = False
    writes: list[Any] = []
    monkeypatch.setattr(save_ui, "save_library", lambda _path, library: writes.append(library))

    host._save_podcast_library()

    assert host._podcast_library_dirty
    assert writes == []
    assert len(host._task_manager.submissions) == 1
    task = host._task_manager.submissions[0]
    result = task[1]()
    task[2]("save", result)
    assert len(writes) == 1
    assert writes[0] is not host._podcast_library
    assert not host._podcast_library_dirty


def test_save_completion_does_not_clear_an_unsnapshotted_mutation(monkeypatch: Any) -> None:
    host = _Host()
    host._podcast_library_revision = 1
    monkeypatch.setattr(save_ui, "save_library", lambda *_args: None)
    host._flush_podcast_library()
    task = host._task_manager.submissions[0]
    result = task[1]()

    host._podcast_library_revision += 1
    host._podcast_library.shows[0].episodes.append(object())
    task[2]("save", result)

    assert host._podcast_library_dirty


def test_large_snapshot_is_copied_in_bounded_ui_turns(monkeypatch: Any) -> None:
    host = _Host()

    class _Later:
        def __init__(self, callback: Any) -> None:
            self.callback = callback

        def Stop(self) -> None:
            return

        def run(self) -> None:
            self.callback()

    class _Wx:
        callbacks: list[_Later]

        def __init__(self) -> None:
            self.callbacks = []

        def CallLater(self, _delay: int, callback: Any) -> _Later:
            later = _Later(callback)
            self.callbacks.append(later)
            return later

    host._wx = _Wx()
    host._podcast_library_revision = 1
    host._podcast_library = SimpleNamespace(
        shows=[SimpleNamespace(episodes=[object()] * 501) for _ in range(40)],
        settings=SimpleNamespace(
            reconnect_enabled=True, reconnect_max_attempts=2, reconnect_wait_seconds=1
        ),
    )
    host._podcast_library_dirty = True
    copied_batches: list[int] = []
    original_deepcopy = save_ui.copy.deepcopy

    def _deepcopy(value: Any) -> Any:
        if isinstance(value, list):
            copied_batches.append(len(value))
        return original_deepcopy(value)

    monkeypatch.setattr(save_ui.copy, "deepcopy", _deepcopy)
    ticks = iter(range(100_000))
    monkeypatch.setattr(save_ui, "perf_counter", lambda: next(ticks) / 100.0)

    host._flush_podcast_library()

    assert host._task_manager.submissions == []
    while host._wx.callbacks:
        host._wx.callbacks.pop(0).run()

    assert copied_batches == [
        size
        for _ in range(40)
        for size in (save_ui.SNAPSHOT_EPISODES_PER_TURN, 501 - save_ui.SNAPSHOT_EPISODES_PER_TURN)
    ]
    assert max(copied_batches) <= save_ui.SNAPSHOT_EPISODES_PER_TURN
    assert len(host._task_manager.submissions) == 1


def test_latest_pending_generation_replaces_an_older_snapshot(monkeypatch: Any) -> None:
    host = _Host()
    writes: list[int] = []
    monkeypatch.setattr(
        save_ui,
        "save_library",
        lambda _path, library: writes.append(len(library.shows[0].episodes)),
    )

    host._flush_podcast_library()
    first = host._task_manager.submissions[0]
    host._podcast_library.shows[0].episodes.append(object())
    host._podcast_library_dirty = True
    host._flush_podcast_library()

    assert len(host._task_manager.submissions) == 1
    first[1]()
    first[2]("first", 2)

    assert writes == [save_ui.COALESCE_SAVE_ABOVE_EPISODES + 2]
    assert not host._podcast_library_dirty
    assert host._podcast_save_pending is None
    assert not host._podcast_save_worker_running


def test_new_generation_arriving_during_write_is_drained_in_order(
    monkeypatch: Any,
) -> None:
    host = _Host()
    writes: list[int] = []

    def _write(_path: Any, library: Any) -> None:
        writes.append(len(library.shows[0].episodes))
        if len(writes) == 1:
            host._podcast_library.shows[0].episodes.append(object())
            host._podcast_library_dirty = True
            host._flush_podcast_library()

    monkeypatch.setattr(save_ui, "save_library", _write)
    host._flush_podcast_library()
    task = host._task_manager.submissions[0]

    task[1]()
    task[2]("write", 2)

    assert writes == [
        save_ui.COALESCE_SAVE_ABOVE_EPISODES + 1,
        save_ui.COALESCE_SAVE_ABOVE_EPISODES + 2,
    ]
    assert host._podcast_save_pending is None
    assert not host._podcast_library_dirty


def test_worker_drains_newer_snapshot_without_a_ui_completion_callback(
    monkeypatch: Any,
) -> None:
    host = _Host()
    writes: list[int] = []
    monkeypatch.setattr(
        save_ui,
        "save_library",
        lambda _path, library: writes.append(len(library.shows[0].episodes)),
    )

    host._flush_podcast_library()
    task = host._task_manager.submissions[0]
    host._podcast_library.shows[0].episodes.append(object())
    host._podcast_library_dirty = True
    host._flush_podcast_library()

    task[1]()

    assert writes == [save_ui.COALESCE_SAVE_ABOVE_EPISODES + 2]
    assert host._podcast_save_pending is None
    assert not host._podcast_save_worker_running
    assert host._podcast_library_dirty


def test_shutdown_wait_is_bounded_and_leaves_the_writer_running(monkeypatch: Any) -> None:
    host = _Host()
    host._podcast_library.shows[0].episodes = []

    class _Future:
        def result(self, *, timeout: float) -> None:
            assert timeout == save_ui.SHUTDOWN_SAVE_WAIT_SECONDS
            raise TimeoutError()

    class _Task:
        future = _Future()

    host._task_manager.submit = lambda *_args, **_kwargs: _Task()
    entered = False

    def _write(*_args: Any) -> None:
        nonlocal entered
        entered = True

    monkeypatch.setattr(save_ui, "save_library", _write)

    host._flush_podcast_library_for_shutdown()

    assert not entered
    assert host._podcast_library_dirty
    assert host._podcast_save_pending is not None


def test_shutdown_retries_a_failed_final_generation_once(monkeypatch: Any) -> None:
    host = _Host()

    class _InlineTaskManager:
        calls = 0

        def submit(
            self,
            name: str,
            func: Any,
            *,
            on_success: Any,
            on_failure: Any,
        ) -> SimpleNamespace:
            self.calls += 1
            future: Future[Any] = Future()
            try:
                result = func()
            except BaseException as error:
                future.set_exception(error)
                on_failure(name, error)
            else:
                future.set_result(result)
                on_success(name, result)
            return SimpleNamespace(future=future)

    manager = _InlineTaskManager()
    host._task_manager = manager
    writes = 0

    def _write(*_args: Any) -> None:
        nonlocal writes
        writes += 1
        if writes == 1:
            raise OSError("temporary disk error")

    monkeypatch.setattr(save_ui, "save_library", _write)

    host._flush_podcast_library_for_shutdown()

    assert manager.calls == 2
    assert writes == 2
    assert not host._podcast_library_dirty
    assert host._podcast_save_pending is None


def test_failed_write_is_reported_and_keeps_library_dirty(monkeypatch: Any) -> None:
    host = _Host()

    def _fail(*_args: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(save_ui, "save_library", _fail)

    host._flush_podcast_library()
    task = host._task_manager.submissions[0]
    try:
        task[1]()
    except OSError as error:
        task[3]("save", error)

    assert host._podcast_library_dirty
    assert host._podcast_save_pending is not None
    assert not host._podcast_save_worker_running
    assert host.announcements
    assert "Could not save the podcast library" in host.announcements[-1]


def test_large_library_timer_flushes_periodically_during_refresh_all() -> None:
    host = _Host()
    host._podcast_save_timer = None
    host._check_run = object()
    host._podcast_library_dirty = True
    flushes: list[bool] = []
    host._flush_podcast_library = lambda: flushes.append(True)

    host._on_podcast_save_timer(object())

    assert flushes == [True]
    assert host._podcast_library_dirty


def test_save_waits_for_a_yielding_feed_commit() -> None:
    host = _Host()
    callbacks: list[Any] = []
    host._wx = SimpleNamespace(CallLater=lambda _delay, callback: callbacks.append(callback))
    host._podcast_commit_depth = 1

    host._flush_podcast_library()

    assert host._task_manager.submissions == []
    assert host._podcast_library_dirty
    assert len(callbacks) == 1

    host._podcast_commit_depth = 0
    while callbacks:
        callbacks.pop(0)()

    assert len(host._task_manager.submissions) == 1


def test_deferred_commit_save_does_not_restart_after_shutdown() -> None:
    host = _Host()
    callbacks: list[Any] = []
    host._wx = SimpleNamespace(CallLater=lambda _delay, callback: callbacks.append(callback))
    host._podcast_commit_depth = 1
    host._flush_podcast_library()

    host._cast_closing = True
    host._podcast_commit_depth = 0
    callbacks.pop(0)()

    assert callbacks == []
    assert host._task_manager.submissions == []
