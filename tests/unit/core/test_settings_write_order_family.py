"""Every app's settings: an older snapshot never lands after a newer save.

plan.md found QUILL Lite could put an older choice back on disk when a queued
write, paused just before its atomic write, landed after a newer synchronous
save. The family audit (2026-11-20) found the same interleaving in Quill
Inkwell, QUILL Cast, Quill Radio and QUILL itself, and a third shape shared
by all of them: Activity's Retry for an old failure re-sent the failed
content after a later save had worked.

Each test holds the *first* atomic write at a gate in
``quill.core.storage.write_json_atomic``, makes the newer save the app makes,
releases the gate, and reads the file back as the next launch would.
"""

from __future__ import annotations

import concurrent.futures
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import persistence_outcome, storage

WAIT = 10.0


class _Gate:
    def __init__(self, real) -> None:
        self.real = real
        self.hold_next = False
        self.entered = threading.Event()
        self.release = threading.Event()
        self._lock = threading.Lock()

    def __call__(self, path, document, *args, **kwargs):
        with self._lock:
            hold, self.hold_next = self.hold_next, False
        if hold:
            self.entered.set()
            assert self.release.wait(WAIT)
        return self.real(path, document, *args, **kwargs)


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> _Gate:
    gate = _Gate(storage.write_json_atomic)
    monkeypatch.setattr(storage, "write_json_atomic", gate)
    return gate


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    return tmp_path


def _fail(*_args, **_kwargs):
    raise PermissionError(13, "locked")


def _newer_save_while_held(gate: _Gate, start_older, newer) -> None:
    """Hold the older write, run the newer save to completion, then release."""
    gate.hold_next = True
    start_older()
    assert gate.entered.wait(WAIT), "the older write never started"
    worker = threading.Thread(target=newer)
    worker.start()
    worker.join(0.3)  # waits its turn now; before the fix it finished here
    gate.release.set()
    worker.join(WAIT)
    assert not worker.is_alive()


# -- the shared Retry ------------------------------------------------------------- #


def test_retry_of_an_old_failure_does_not_undo_a_later_save(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    heard: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(heard.append)
    old = {"choice": "old"}
    attempts: list[int] = []

    def write_old() -> None:
        attempts.append(1)
        if len(attempts) == 1:
            raise PermissionError(13, "locked")
        storage.write_json_atomic(path, old)

    try:
        with pytest.raises(OSError):
            persistence_outcome.guarded_write("Test settings", path, write_old)
        failed = [o for o in heard if not o.ok][-1]
        persistence_outcome.guarded_write(
            "Test settings", path, lambda: storage.write_json_atomic(path, {"choice": "new"})
        )
        failed.retry()  # pressed in Activity after the later save worked
        assert json.loads(path.read_text(encoding="utf-8")) == {"choice": "new"}
    finally:
        stop()


def test_retry_with_no_later_save_still_writes(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    heard: list[persistence_outcome.WriteOutcome] = []
    stop = persistence_outcome.subscribe(heard.append)
    attempts: list[int] = []

    def write() -> None:
        attempts.append(1)
        if len(attempts) == 1:
            raise PermissionError(13, "locked")
        storage.write_json_atomic(path, {"choice": "only"})

    try:
        with pytest.raises(OSError):
            persistence_outcome.guarded_write("Test settings", path, write)
        [o for o in heard if not o.ok][-1].retry()
        assert json.loads(path.read_text(encoding="utf-8")) == {"choice": "only"}
    finally:
        stop()


# -- Quill Inkwell ------------------------------------------------------------------ #


class _Tasks:
    """The task manager's submit, run on a real thread."""

    def __init__(self) -> None:
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def submit(self, _name, fn, *, on_success=None, on_failure=None, **_kwargs):
        return SimpleNamespace(future=self.pool.submit(fn))


def test_inkwell_a_queued_preference_never_lands_after_a_menu_toggle(
    data_dir: Path, gate: _Gate
) -> None:
    from quill.apps.inkwell_preference_save import InkwellPreferenceSaver
    from quill.core.expansion import settings as inkwell

    live = inkwell.InkwellSettings()
    tasks = _Tasks()
    saver = InkwellPreferenceSaver(data_dir, tasks, lambda _m: None)

    def older() -> None:
        live.announce_expansions = True  # Options > Announce Expansions: queued
        saver.queue(live)

    def newer() -> None:
        live.announce_expansions = False  # then a toggle that saves inline
        inkwell.save_settings(data_dir, live)

    _newer_save_while_held(gate, older, newer)
    saver.flush()  # Exit
    tasks.pool.shutdown(wait=True)
    assert inkwell.load_settings(data_dir).announce_expansions is False


def test_inkwell_exit_does_not_rewrite_an_older_failed_snapshot(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps.inkwell_preference_save import InkwellPreferenceSaver
    from quill.core.expansion import settings as inkwell

    live = inkwell.InkwellSettings()
    tasks = _Tasks()
    saver = InkwellPreferenceSaver(data_dir, tasks, lambda _m: None)
    real = storage.write_json_atomic
    monkeypatch.setattr(storage, "write_json_atomic", _fail)
    live.announce_expansions = True
    saver.queue(live)
    try:
        saver._task.future.result()
    except OSError:
        pass
    monkeypatch.setattr(storage, "write_json_atomic", real)
    live.announce_expansions = False
    inkwell.save_settings(data_dir, live)  # a later inline save works
    saver.flush()  # Exit used to rewrite the failed True over it
    tasks.pool.shutdown(wait=True)
    assert inkwell.load_settings(data_dir).announce_expansions is False


# -- QUILL Cast --------------------------------------------------------------------- #


def test_cast_a_queued_history_write_never_lands_after_resume_on_launch(
    data_dir: Path, gate: _Gate
) -> None:
    from quill.core.podcasts import history as podcast_history
    from quill.stability.task_manager import UiLifetimeToken
    from quill.ui.podcasts import record_writes

    live = podcast_history.PodcastHistory()
    host = SimpleNamespace(
        _cast_ui_lifetime=UiLifetimeToken(), _podcast_history=live, _announce=lambda _m: None
    )

    def older() -> None:
        live.resume_on_launch = True  # a record write: queued snapshot
        assert record_writes.queue_history_save(host)

    def newer() -> None:
        live.resume_on_launch = False  # Resume on Launch toggled: written inline
        podcast_history.save_history(data_dir, live)

    _newer_save_while_held(gate, older, newer)
    host._podcast_record_tasks.shutdown(wait=True)
    assert podcast_history.load_history(data_dir).resume_on_launch is False


# -- Quill Radio -------------------------------------------------------------------- #


def test_radio_a_save_after_a_timed_out_close_is_not_undone_by_the_writer(
    data_dir: Path, gate: _Gate
) -> None:
    from quill.core.radio import (
        history,  # noqa: F401 - the record before its store
        history_store,
    )
    from quill.ui.radio import history_save

    live = history_store.load_history(data_dir)
    host = SimpleNamespace(_radio_history=live, _announce=lambda _m: None)
    original = live.resume_on_launch

    def older() -> None:
        live.resume_on_launch = not original
        assert history_save.save_history_async(host)

    def newer() -> None:
        # The window closes; the writer's wait runs out with the old write
        # still in flight; a late save then takes the synchronous path.
        host._radio_history_save_coordinator.close(timeout=0.05)
        live.resume_on_launch = original
        assert history_save.save_history_async(host)

    _newer_save_while_held(gate, older, newer)
    host._radio_history_save_coordinator.flush(WAIT)
    assert history_store.load_history(data_dir).resume_on_launch is original


# -- QUILL -------------------------------------------------------------------------- #


def test_quill_a_worker_thread_save_never_lands_after_a_newer_ui_save(
    data_dir: Path, gate: _Gate
) -> None:
    from quill.core import settings as quill_settings

    live = quill_settings.Settings()
    original = live.soft_wrap
    workers: list[threading.Thread] = []

    def older() -> None:
        live.soft_wrap = not original  # a download finishing on a worker thread
        workers.append(threading.Thread(target=quill_settings.save_settings, args=(live,)))
        workers[-1].start()

    def newer() -> None:
        live.soft_wrap = original  # the listener changes it back in Preferences
        quill_settings.save_settings(live)

    _newer_save_while_held(gate, older, newer)
    workers[-1].join(WAIT)
    assert quill_settings.load_settings().soft_wrap is original
