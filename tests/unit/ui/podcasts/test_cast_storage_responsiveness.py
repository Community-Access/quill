from __future__ import annotations

import copy
import os
import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.podcasts import inbox, playback_cache
from quill.core.podcasts.models import ExpiredEntry, PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.stability.task_manager import CancellationToken, UiLifetimeToken
from quill.ui.main_frame_podcast_session import PodcastSessionMixin
from quill.ui.podcasts import storage_delete, storage_snapshot
from quill.ui.podcasts.storage_snapshot import CoherentSnapshot, TurnJob
from quill.ui.podcasts.storage_tasks import for_host
from quill.ui.undo_file_jobs import FileJobs


class Later:
    def __init__(self, callback):
        self.callback = callback
        self.stopped = False

    def Stop(self):
        self.stopped = True


class Scheduler:
    def __init__(self):
        self.callbacks = deque()

    def CallLater(self, _delay, callback, *args):
        later = Later(lambda: callback(*args))
        self.callbacks.append(later)
        return later

    def CallAfter(self, callback, *args):
        self.CallLater(0, callback, *args)

    def tick(self):
        later = self.callbacks.popleft()
        if not later.stopped:
            later.callback()


class Window:
    def __init__(self):
        self.deleted = False
        self.bindings = []

    def GetId(self):
        return id(self)

    def GetTitle(self):
        return "Cast storage test"

    def Bind(self, event, handler):
        self.bindings.append((event, handler))

    def IsBeingDeleted(self):
        return self.deleted


class Manager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.queued = deque()
        self.running = []
        self.submitted = []

    def submit(self, name, work, **options):
        token = CancellationToken()
        task = SimpleNamespace(
            operation_id=str(len(self.submitted)), future=Future(), cancellation_token=token
        )
        self.queued.append((task, work, options))
        self.submitted.append((name, options))
        return task

    def cancel(self, operation):
        for task, _work, _options in self.queued:
            if task.operation_id == operation:
                task.cancellation_token.cancel()

    def start_next(self):
        task, work, options = self.queued.popleft()
        task.future = self.executor.submit(work, cancellation_token=task.cancellation_token)
        self.running.append((task, options))
        return task.future

    def deliver(self):
        for index, (task, options) in enumerate(self.running):
            if not task.future.done():
                continue
            self.running.pop(index)
            token = options.get("ui_lifetime")
            if token is not None and not token.is_alive:
                return True
            try:
                result = task.future.result()
            except BaseException as error:
                options["on_failure"]("test", error)
            else:
                options["on_success"]("test", result)
            return True
        return False


class Host(PodcastSessionMixin):
    def __init__(self, tmp_path):
        self.ui_thread = threading.get_ident()
        self.frame = Window()
        self._wx = Scheduler()
        self._task_manager = Manager()
        self._cast_ui_lifetime = UiLifetimeToken()
        self.frame._quill_ui_lifetime = self._cast_ui_lifetime
        self._cast_closing = self._cast_closed = False
        self._podcast_library_revision = 0
        self._podcast_library = PodcastLibrary()
        self._podcast_download_queue = SimpleNamespace(get=lambda _guid: None)
        self._podcast_controller = SimpleNamespace(
            state=SimpleNamespace(show_id=None, episode_guid=None)
        )
        self._undo_file_jobs = FileJobs(self._task_manager, self, tmp_path)
        self.said = []
        self.saved = []

    def _announce(self, message):
        assert threading.get_ident() == self.ui_thread
        self.said.append(message)

    def _save_podcast_library(self):
        assert threading.get_ident() == self.ui_thread
        self._podcast_library_revision += 1
        self.saved.append(copy.deepcopy(self._podcast_library))

    def step(self):
        if self._task_manager.queued:
            self._task_manager.start_next()
        elif self._task_manager.deliver():
            pass
        elif self._wx.callbacks:
            self._wx.tick()
        else:
            time.sleep(0.001)

    def until(self, predicate):
        deadline = time.monotonic() + 15
        while not predicate():
            assert time.monotonic() < deadline, "Storage work did not complete"
            self.step()

    def drain(self):
        self.until(
            lambda: (
                not self._task_manager.queued
                and not self._task_manager.running
                and not self._wx.callbacks
            )
        )


@pytest.fixture
def host(tmp_path, monkeypatch):
    wx = pytest.importorskip("wx")  # Load wx before filesystem-thread assertions.

    assert wx is not None
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(playback_cache, "cache_root", lambda: tmp_path / "playback-cache")
    result = Host(tmp_path)
    path = tmp_path / "episode.mp3"
    path.write_bytes(b"audio")
    episode = PodcastEpisode(
        guid="episode",
        title="Episode",
        audio_url="https://example.test/audio",
        published=(datetime.now(UTC) - timedelta(days=30)).isoformat(),
        downloaded_path=str(path),
    )
    show = PodcastShow(id="show", title="Show", episodes=[episode])
    result._podcast_library.shows.append(show)
    result._podcast_library.apply_show_override(show, download_retention_days=1)
    yield result
    result.drain()
    result._task_manager.executor.shutdown(wait=True)


def _episode(host):
    return host._podcast_library.shows[0].episodes[0]


def _block_ui_filesystem(host, monkeypatch):
    threads = []

    def wrap(original, name):
        def checked(*args, **kwargs):
            assert threading.get_ident() != host.ui_thread, f"{name} ran on the UI thread"
            threads.append(threading.get_ident())
            return original(*args, **kwargs)

        return checked

    for name in ("stat", "unlink", "read_text", "iterdir"):
        monkeypatch.setattr(Path, name, wrap(getattr(Path, name), name))
    monkeypatch.setattr(os, "scandir", wrap(os.scandir, "scandir"))
    return threads


def test_free_space_returns_immediately_and_performs_no_ui_filesystem_work(host, monkeypatch):
    completed = []
    with monkeypatch.context() as patch:
        threads = _block_ui_filesystem(host, patch)
        assert host.podcast_free_up_space(completed=completed.append) is None
        assert completed == []
        assert host._task_manager.submitted == []
        assert _episode(host).downloaded_path
        host.drain()
    assert threads
    assert completed == [5]
    assert _episode(host).downloaded_path == ""
    assert host.saved[-1].shows[0].episodes[0].downloaded_path == ""
    assert any("Freed 5 bytes from 1" in message for message in host.said)
    assert host._undo_file_jobs.pending == 0
    assert any(not options["safe_to_cancel"] for _, options in host._task_manager.submitted)


@pytest.mark.parametrize("protection", ["queue", "position", "pin", "transfer"])
def test_protection_added_after_planning_is_revalidated_before_deletion(host, protection):
    host.podcast_free_up_space()
    host.until(lambda: bool(host._task_manager.queued))
    future = host._task_manager.start_next()
    future.result(timeout=10)
    episode = _episode(host)
    path = episode.downloaded_path
    if protection == "queue":
        host._podcast_library.queue.append(QueueItem("show", "episode"))
    elif protection == "position":
        episode.position_ms = 2000
    elif protection == "pin":
        host._podcast_library.extra_settings["storage_pinned"] = True
    else:
        host._podcast_download_queue.get = lambda _guid: SimpleNamespace(
            show_id="show", episode_guid="episode", status="downloading"
        )
    host._save_podcast_library()
    host.drain()
    assert episode.downloaded_path == path
    assert Path(path).exists()
    assert not any("Freed 5 bytes" in message for message in host.said)


def test_a_file_pool_backlog_cannot_delete_a_newly_queued_download(host):
    host.podcast_free_up_space()
    host.until(lambda: host._undo_file_jobs.pending == 2)
    path = _episode(host).downloaded_path
    host._podcast_library.queue.append(QueueItem("show", "episode"))
    host._save_podcast_library()
    host.drain()
    assert Path(path).exists()
    assert _episode(host).downloaded_path == path
    assert host._undo_file_jobs.pending == 0
    assert any("protected file(s) were kept" in message for message in host.said)


def test_failed_delete_keeps_metadata_and_reports_only_completed_bytes(host, monkeypatch):
    episode = _episode(host)
    path = episode.downloaded_path
    unlink = Path.unlink

    def locked(candidate, **kwargs):
        if str(candidate) == path:
            raise PermissionError("In use")
        return unlink(candidate, **kwargs)

    monkeypatch.setattr(Path, "unlink", locked)
    completed = []
    host.podcast_free_up_space(completed=completed.append)
    host.drain()
    assert episode.downloaded_path == path
    assert Path(path).exists()
    assert completed == [0]
    assert any("1 file(s) could not" in message for message in host.said)
    assert not any("from 1 downloaded" in message for message in host.said)
    assert host._undo_file_jobs.pending == 0


@pytest.mark.parametrize("protection", ["queue", "position", "transfer"])
def test_permission_is_revoked_when_protection_changes_during_worker_stat(
    host, monkeypatch, protection
):
    original = Path.stat
    path = _episode(host).downloaded_path
    inspected = [0]
    entered, release = threading.Event(), threading.Event()

    def blocked(candidate, **kwargs):
        measured = original(candidate, **kwargs)
        if str(candidate) == path:
            inspected[0] += 1
            if inspected[0] == 2:
                entered.set()
                assert release.wait(10)
        return measured

    monkeypatch.setattr(Path, "stat", blocked)
    completed = []
    host.podcast_free_up_space(completed=completed.append)
    host.until(entered.is_set)
    try:
        if protection == "queue":
            host._podcast_library.queue.append(QueueItem("show", "episode"))
            host._save_podcast_library()
        elif protection == "position":
            _episode(host).position_ms = 1000
        else:
            host._podcast_download_queue.get = lambda _guid: SimpleNamespace(
                show_id="show", episode_guid="episode", status="downloading"
            )
        host.until(lambda: for_host(host).active.gate.cancelled.is_set())
    finally:
        release.set()
    host.drain()
    assert completed == [0]
    assert _episode(host).downloaded_path == path
    assert Path(path).exists()
    assert host._undo_file_jobs.pending == 0


def test_maintenance_preserves_queue_and_inbox_changes_made_during_planning(host):
    library = host._podcast_library
    placements = library.show_folder_copies
    placements["show"] = ["initial-folder", None]
    show = library.shows[0]
    show.route_to_inbox = True
    newer = PodcastEpisode(
        guid="newer",
        title="Newer",
        audio_url="https://example.test/newer",
        published=datetime.now(UTC).isoformat(),
    )
    show.episodes.append(newer)
    library.apply_show_override(show, queue_age_limit_days=1, inbox_max_episodes=1)
    library.queue.append(
        QueueItem("show", "episode", added_at=(datetime.now(UTC) - timedelta(days=5)).isoformat())
    )
    summaries = []
    host.podcast_run_maintenance(completed=summaries.append)
    host.until(lambda: bool(host._task_manager.queued))
    host._task_manager.start_next().result(timeout=10)
    new_queue = QueueItem("show", "newer", added_at=datetime.now(UTC).isoformat())
    library.queue.append(new_queue)
    key = inbox.inbox_key("show", "episode")
    library.inbox_assignments[key] = "my-new-inbox-folder"
    placements["show"].remove("initial-folder")
    placements["show"].append("new-folder")
    host._save_podcast_library()
    host.drain()
    assert library.queue == [new_queue]
    assert library.queue[0] is new_queue
    assert library.inbox_assignments[key] == "my-new-inbox-folder"
    assert library.show_folder_copies is placements
    assert library.show_folder_copies == {"show": [None, "new-folder"]}
    assert library.recently_expired[0].episode_guid == "episode"
    assert _episode(host).downloaded_path
    assert host.saved[-1].queue[0].episode_guid == "newer"
    assert host.saved[-1].show_folder_copies == {"show": [None, "new-folder"]}
    assert "1 episode(s) expired" in summaries[0]


def test_maintenance_preserves_edits_between_bounded_metadata_turns(host):
    library = host._podcast_library
    placements = library.show_folder_copies
    placements["show"] = [None]
    show = library.shows[0]
    show.route_to_inbox = True
    library.apply_show_override(show, queue_age_limit_days=1, inbox_max_episodes=1)
    stamp = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    for number in range(150):
        show.episodes.append(
            PodcastEpisode(
                guid=f"queued-{number}", title="Queued", audio_url="https://example.test/"
            )
        )
        library.queue.append(QueueItem("show", f"queued-{number}", added_at=stamp))
    show.episodes.append(
        PodcastEpisode(guid="newer", title="Newer", audio_url="https://example.test/")
    )
    completed = []
    host.podcast_run_maintenance(completed=completed.append)
    host.until(lambda: bool(host._task_manager.queued))
    host._task_manager.start_next().result(timeout=10)
    host._task_manager.deliver()
    host._wx.tick()
    new_item = QueueItem("show", "newer")
    library.queue.append(new_item)
    key = inbox.inbox_key("show", "episode")
    library.inbox_assignments[key] = "my-new-inbox-folder"
    placements["show"].append("new-folder")
    host.drain()
    assert library.queue == [new_item]
    assert library.queue[0] is new_item
    assert library.inbox_assignments[key] == "my-new-inbox-folder"
    assert library.show_folder_copies is placements
    assert library.show_folder_copies == {"show": [None, "new-folder"]}
    assert host.saved[-1].show_folder_copies == {"show": [None, "new-folder"]}
    assert len(library.recently_expired) == 150
    assert "150 episode(s) expired" in completed[0]


def test_coherent_capture_retries_instead_of_returning_a_hybrid(host, monkeypatch):
    monkeypatch.setattr(storage_snapshot, "ITEMS_PER_TURN", 1)
    show = host._podcast_library.shows[0]
    show.episodes.extend(
        PodcastEpisode(guid=str(n), title=str(n), audio_url="https://example.test/audio")
        for n in range(400)
    )
    show.episodes[-1].downloaded_path = "synthetic-second-download.mp3"
    completed = []
    job = CoherentSnapshot(
        host, completed=completed.append, failed=lambda error: pytest.fail(str(error))
    )
    job.start()
    host._wx.tick()
    assert completed == []
    show.episodes[0].played = True
    show.episodes[-1].played = True
    host._podcast_library_revision += 1
    host.drain()
    snapshot = completed[0].library
    assert [episode.guid for episode in snapshot.shows[0].episodes] == ["episode", "399"]
    assert snapshot.shows[0].episodes[0].played
    assert snapshot.shows[0].episodes[-1].played
    show.episodes[0].played = False
    assert snapshot.shows[0].episodes[0].played


def test_storage_capture_detaches_extra_folder_placements(host):
    library = host._podcast_library
    library.show_folder_copies["show"] = [None, "first-folder", "second-folder"]
    completed = []
    job = CoherentSnapshot(
        host, completed=completed.append, failed=lambda error: pytest.fail(str(error))
    )
    job.start()
    host.drain()
    snapshot = completed[0].library
    assert snapshot.show_folder_copies == library.show_folder_copies
    assert snapshot.show_folder_copies is not library.show_folder_copies
    assert snapshot.show_folder_copies["show"] is not library.show_folder_copies["show"]
    snapshot.show_folder_copies["show"].append("snapshot-only")
    assert library.show_folder_copies["show"] == [None, "first-folder", "second-folder"]
    library.show_folder_copies["show"].append("live-only")
    assert snapshot.show_folder_copies["show"] == [
        None,
        "first-folder",
        "second-folder",
        "snapshot-only",
    ]


def test_folder_copy_capture_is_bounded_per_placement(host, monkeypatch):
    library = host._podcast_library
    library.show_folder_copies["show"] = [f"folder-{number}" for number in range(400)]
    monkeypatch.setattr(storage_snapshot, "perf_counter", lambda: 0)
    captured = storage_snapshot.StorageCapture(
        library, PodcastLibrary(), storage_snapshot.generation(host)
    )
    completed = []
    job = TurnJob(
        host._wx,
        storage_snapshot.capture_chunks(host, captured),
        completed=completed.append,
        failed=lambda error: pytest.fail(str(error)),
        alive=lambda: True,
    )
    job.start()
    host._wx.tick()
    assert completed == []
    assert captured.library.show_folder_copies["show"] == library.show_folder_copies["show"][:126]
    host.drain()
    assert completed == [captured]
    assert captured.library.show_folder_copies == library.show_folder_copies


@pytest.mark.parametrize("change", ["replace", "add", "in-place"])
def test_coherent_capture_retries_after_folder_placement_changes(host, monkeypatch, change):
    library = host._podcast_library
    library.show_folder_copies["show"] = [f"folder-{number}" for number in range(400)]
    monkeypatch.setattr(storage_snapshot, "perf_counter", lambda: 0)
    completed = []
    job = CoherentSnapshot(
        host, completed=completed.append, failed=lambda error: pytest.fail(str(error))
    )
    job.start()
    first_turn = job.job
    host._wx.tick()
    assert completed == []
    if change == "replace":
        library.show_folder_copies = {"show": [None, "replacement-folder"]}
    elif change == "add":
        library.show_folder_copies["other-show"] = [None, "new-folder"]
    else:
        library.show_folder_copies["show"][0] = "new-first-folder"
        library.show_folder_copies["show"][-1] = None
        host._podcast_library_revision += 1
    host.drain()
    assert first_turn is not None and first_turn.cancelled
    assert len(completed) == 1
    assert completed[0].library.show_folder_copies == library.show_folder_copies
    assert completed[0].library.show_folder_copies is not library.show_folder_copies


def test_turns_enforce_the_128_item_ceiling(host, monkeypatch):
    seen = []
    monkeypatch.setattr(storage_snapshot, "perf_counter", lambda: 0)

    def chunks():
        for value in range(300):
            seen.append(value)
            yield

    job = TurnJob(
        host._wx,
        chunks(),
        completed=lambda _result: None,
        failed=lambda error: pytest.fail(str(error)),
        alive=lambda: True,
    )
    job.start()
    host._wx.tick()
    assert len(seen) == 128
    job.cancel()
    host.drain()
    assert len(seen) == 128


def test_turns_enforce_the_eight_millisecond_ceiling(host, monkeypatch):
    elapsed = [0.0]
    seen = []
    monkeypatch.setattr(storage_snapshot, "perf_counter", lambda: elapsed[0])

    def chunks():
        for value in range(300):
            seen.append(value)
            elapsed[0] += 0.001
            yield

    job = TurnJob(
        host._wx,
        chunks(),
        completed=lambda _result: None,
        failed=lambda error: pytest.fail(str(error)),
        alive=lambda: True,
    )
    job.start()
    host._wx.tick()
    assert len(seen) == 8
    assert elapsed[0] == pytest.approx(0.008)
    job.cancel()


def test_lifecycle_cancels_preparations_without_a_late_completion(host):
    from quill.ui.podcasts.lifecycle import cancel_preparations

    completed = []
    path = _episode(host).downloaded_path
    host.podcast_run_maintenance(completed=completed.append)
    host._cast_closing = True
    cancel_preparations(host)
    host.drain()
    assert completed == []
    assert Path(path).exists()
    assert host._undo_file_jobs.pending == 0


def test_close_waits_for_noncancelable_deletion_reconciliation(host):
    from quill.ui.podcasts.lifecycle import cancel_preparations

    completed = []
    host.podcast_free_up_space(completed=completed.append)
    host.until(lambda: host._undo_file_jobs.pending == 2)
    host._cast_closing = True
    cancel_preparations(host)
    host.drain()
    assert completed == []
    assert host._undo_file_jobs.pending == 0
    assert _episode(host).downloaded_path
    assert not any(message.startswith("Freed") for message in host.said)


def test_close_after_unlink_still_reconciles_and_persists_without_announcing(host, monkeypatch):
    from quill.ui.podcasts.lifecycle import cancel_preparations

    removed, release = threading.Event(), threading.Event()
    path = _episode(host).downloaded_path
    original = Path.unlink

    def blocked(candidate, **kwargs):
        result = original(candidate, **kwargs)
        if str(candidate) == path:
            removed.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(Path, "unlink", blocked)
    completed = []
    host.podcast_free_up_space(completed=completed.append)
    host.until(removed.is_set)
    try:
        host._cast_closing = True
        cancel_preparations(host)
    finally:
        release.set()
    host.drain()
    assert not Path(path).exists()
    assert _episode(host).downloaded_path == ""
    assert host.saved[-1].shows[0].episodes[0].downloaded_path == ""
    assert host._undo_file_jobs.pending == 0
    assert completed == []
    assert not any(message.startswith("Freed") for message in host.said)


def test_save_failure_is_explicit_and_does_not_leak_a_pending_lease(host, monkeypatch):
    def failed():
        raise OSError("The library could not be saved")

    monkeypatch.setattr(host, "_save_podcast_library", failed)
    host.podcast_free_up_space()
    host.drain()
    assert _episode(host).downloaded_path == ""
    assert any("could not be saved" in message for message in host.said)
    assert any("could not finish" in message for message in host.said)
    assert host._undo_file_jobs.pending == 0
    assert for_host(host).active is None


def test_permission_watcher_is_bounded_by_items_and_time(host, monkeypatch):
    seen = []
    elapsed = [0.0]
    monkeypatch.setattr(storage_delete, "perf_counter", lambda: elapsed[0])

    def checks():
        for value in range(300):
            seen.append(value)
            elapsed[0] += 0.001
            yield True

    gate = storage_delete.DeletionGate(host, (), lambda _gate: None)
    gate.allow((), checks)
    assert len(seen) == 8
    assert elapsed[0] == pytest.approx(0.008)
    gate.cancel()
    host.drain()
    monkeypatch.setattr(storage_delete, "perf_counter", lambda: 0)
    gate = storage_delete.DeletionGate(host, (), lambda _gate: None)
    gate.allow((), checks)
    assert len(seen) == 8 + 128
    gate.cancel()


def test_two_maintenance_requests_share_a_pass_and_one_announcement(host):
    first, second = [], []
    host.podcast_run_maintenance(completed=first.append)
    host.podcast_run_maintenance(completed=second.append)
    host.drain()
    assert first == second
    assert len(first) == 1
    assert (
        len([message for message in host.said if message.startswith("Podcast housekeeping")]) == 1
    )
    assert for_host(host).active is None


def test_maintenance_finishes_overdue_sweep_and_reports_actual_deletion(host):
    path = _episode(host).downloaded_path
    host._podcast_library.recently_expired.append(
        ExpiredEntry(
            "show", "episode", expired_at=(datetime.now(UTC) - timedelta(days=10)).isoformat()
        )
    )
    completed = []
    host.podcast_run_maintenance(completed=completed.append)
    host.drain()
    assert not Path(path).exists()
    assert _episode(host).downloaded_path == ""
    assert not host._podcast_library.recently_expired
    assert "1 downloaded file(s) removed" in completed[0]
    assert "5 bytes freed" in completed[0]
    assert host.saved[-1].shows[0].episodes[0].downloaded_path == ""


@pytest.fixture
def downloads(host, monkeypatch):
    import wx

    from quill.ui.podcasts.downloads_dialog import DownloadsDialog

    app = wx.GetApp() or wx.App(False)
    loop = wx.GUIEventLoop()
    previous = wx.EventLoop.GetActive()
    wx.EventLoop.SetActive(loop)
    frame = wx.Frame(None, title="Storage test owner")
    frame._quill_ui_lifetime = host._cast_ui_lifetime
    host.frame = frame
    with monkeypatch.context() as patch:
        _block_ui_filesystem(host, patch)
        dialog = DownloadsDialog(
            frame,
            library=host._podcast_library,
            storage_jobs=for_host(host),
            announce_cb=host._announce,
            on_free_space=host.podcast_free_up_space,
            on_library_changed=host._save_podcast_library,
        )

    def pump(predicate):
        deadline = time.monotonic() + 15
        while not predicate():
            assert time.monotonic() < deadline, (
                f"Native Downloads controls did not finish: {dialog._summary.GetLabel()!r}; "
                f"alive={dialog._alive()}, usage={dialog._usage}, "
                f"queued={len(host._task_manager.queued)}, "
                f"running={len(host._task_manager.running)}"
            )
            app.Yield()
            host.step()

    try:
        yield dialog, pump, app
    finally:
        try:
            host.drain()
        finally:
            dialog._cancel_ui()
            if dialog.dialog:
                dialog.dialog.Destroy()
            frame.Destroy()
            app.Yield()
            loop.ProcessIdle()
            wx.EventLoop.SetActive(previous)


def test_downloads_refresh_and_filter_keep_filesystem_work_off_the_ui(host, downloads, monkeypatch):
    dialog, pump, _app = downloads
    with monkeypatch.context() as patch:
        threads = _block_ui_filesystem(host, patch)
        dialog._refresh(announce=True)
        assert dialog._usage is None
        pump(lambda: "downloaded episode(s)" in dialog._summary.GetLabel())
        assert dialog._list.GetItemCount() == 1
        assert "5 bytes" in dialog._summary.GetLabel()
        _episode(host).played = True
        host._save_podcast_library()
        dialog._filter.SetSelection(1)
        dialog._refresh(announce=True)
        pump(lambda: "hiding 1" in dialog._summary.GetLabel())
        assert dialog._list.GetItemCount() == 0
    assert threads


def test_downloads_preserves_saved_column_order_and_visibility_off_thread(
    host, downloads, monkeypatch
):
    from quill.core.media.list_columns import ColumnLayouts
    from quill.core.podcasts.list_columns import DOWNLOADS, SURFACES, save_podcast_column_layouts

    dialog, pump, _app = downloads
    layouts = ColumnLayouts.defaults(SURFACES)
    layouts.set_order(DOWNLOADS.id, ["podcast", "size", "files"])
    layouts.set_visible(DOWNLOADS.id, "files", False)
    save_podcast_column_layouts(host._undo_file_jobs.data_dir, layouts)
    with monkeypatch.context() as patch:
        _block_ui_filesystem(host, patch)
        dialog._refresh()
        pump(lambda: "downloaded episode(s)" in dialog._summary.GetLabel())
    assert [column.id for column in dialog._columns] == ["podcast", "size"]
    assert dialog._list.GetColumnCount() == 2
    assert dialog._list.GetItemText(0, 1) == "5 bytes"


def test_downloads_virtual_rows_keep_selection_and_committed_filter_values(
    host, downloads, monkeypatch, tmp_path
):
    import wx

    dialog, pump, _app = downloads
    for show_id, title, played in (
        ("played", "Already played", True),
        ("last", "Last podcast", False),
    ):
        path = tmp_path / f"{show_id}.mp3"
        path.write_bytes(b"audio")
        host._podcast_library.shows.append(
            PodcastShow(
                id=show_id,
                title=title,
                episodes=[
                    PodcastEpisode(
                        guid=f"{show_id}-episode",
                        title=title,
                        audio_url="https://example.test/audio",
                        downloaded_path=str(path),
                        played=played,
                    )
                ],
            )
        )
    host._save_podcast_library()

    def no_native_row_mutations(*_args, **_kwargs):
        pytest.fail("Downloads must publish virtual rows, not insert or delete native rows")

    monkeypatch.setattr(dialog._list, "InsertItem", no_native_row_mutations)
    monkeypatch.setattr(dialog._list, "DeleteItem", no_native_row_mutations)
    assert dialog._list.GetWindowStyleFlag() & wx.LC_VIRTUAL
    dialog._refresh()
    pump(lambda: "3 downloaded episode(s)" in dialog._summary.GetLabel())
    assert dialog._list.GetItemCount() == 3
    selected_index = next(i for i, row in enumerate(dialog._rows) if row.show_id == "last")
    played_index = next(i for i, row in enumerate(dialog._rows) if row.show_id == "played")
    files_column = next(i for i, column in enumerate(dialog._columns) if column.id == "files")
    dialog._list.Select(dialog._list.GetFirstSelected(), False)
    dialog._list.Select(selected_index)
    dialog._list.Focus(selected_index)

    dialog._filter.SetSelection(1)
    dialog._refresh()
    assert dialog._list.GetItemText(played_index, files_column) == "1"
    assert dialog._selected_show().show_id == "last"
    pump(lambda: "hiding 1 already-played" in dialog._summary.GetLabel())
    assert dialog._list.GetItemCount() == 2
    assert dialog._selected_show().show_id == "last"
    assert dialog._row_text(2, files_column) == ""
    assert dialog._row_text(0, len(dialog._columns)) == ""


def test_downloads_surfaces_report_failure_without_a_success_shaped_empty_report(
    host, downloads, monkeypatch
):
    from quill.core.podcasts.list_columns import FILE_NAME

    dialog, pump, _app = downloads
    (host._undo_file_jobs.data_dir / FILE_NAME).write_text("{bad json", encoding="utf-8")
    with monkeypatch.context() as patch:
        _block_ui_filesystem(host, patch)
        dialog._refresh()
        pump(lambda: dialog._summary.GetLabel().startswith("Could not read"))
    assert _episode(host).downloaded_path
    assert not any(message.startswith("0 downloaded episode") for message in host.said)
    assert any("Could not read podcast storage" in message for message in host.said)
    assert dialog._free_btn.IsEnabled()


def test_downloads_remove_show_reports_failed_deletes_without_clearing_metadata(
    host, downloads, monkeypatch
):
    import wx

    from quill.ui import dialog_contract

    dialog, pump, _app = downloads
    pump(lambda: "downloaded episode(s)" in dialog._summary.GetLabel())
    prompts = []
    monkeypatch.setattr(
        dialog_contract,
        "show_message_box",
        lambda *args, **_kwargs: prompts.append(args[0]) or wx.YES,
    )
    path = _episode(host).downloaded_path
    original = Path.unlink

    def locked(candidate, **kwargs):
        if str(candidate) == path:
            raise PermissionError("In use")
        return original(candidate, **kwargs)

    monkeypatch.setattr(Path, "unlink", locked)
    with monkeypatch.context() as patch:
        _block_ui_filesystem(host, patch)
        dialog._on_remove_show_downloads(None)
        assert prompts == []
        pump(lambda: any(message.startswith("Removed") for message in host.said))
    assert len(prompts) == 1
    assert _episode(host).downloaded_path == path
    assert Path(path).exists()
    assert any(
        "Removed 0 download(s)" in message and "1 file(s) could not" in message
        for message in host.said
    )
    assert not host.saved


def test_closing_downloads_drops_widget_callbacks_but_finishes_owner_reconciliation(
    host, downloads, monkeypatch
):
    import wx

    from quill.ui import dialog_contract

    dialog, pump, app = downloads
    pump(lambda: "downloaded episode(s)" in dialog._summary.GetLabel())
    monkeypatch.setattr(dialog_contract, "show_message_box", lambda *_args, **_kwargs: wx.YES)
    dialog._on_remove_show_downloads(None)
    pump(lambda: host._undo_file_jobs.pending == 2)
    dialog._cancel_ui()
    dialog.dialog.Destroy()
    app.Yield()

    def late(_message):
        raise AssertionError("The closed dialog received a late announcement")

    dialog._announce = late
    host.drain()
    assert _episode(host).downloaded_path == ""
    assert host.saved[-1].shows[0].episodes[0].downloaded_path == ""
    assert host._undo_file_jobs.pending == 0


def test_downloads_free_space_stays_busy_until_completed_then_refreshes(
    host, downloads, monkeypatch
):
    dialog, pump, _app = downloads
    pump(lambda: "downloaded episode(s)" in dialog._summary.GetLabel())
    with monkeypatch.context() as patch:
        _block_ui_filesystem(host, patch)
        dialog._on_free_space_click(None)
        assert dialog._busy
        assert not dialog._free_btn.IsEnabled()
        assert not dialog._remove_show_btn.IsEnabled()
        pump(lambda: dialog._summary.GetLabel().startswith("0 downloaded episode(s)"))
    assert not dialog._busy
    assert dialog._free_btn.IsEnabled()
    assert not dialog._remove_show_btn.IsEnabled()
    assert any(message.startswith("Freed 5 bytes from 1") for message in host.said)


@pytest.mark.parametrize("action", ["refresh", "remove"])
def test_closing_downloads_cancels_a_report_or_proposal_without_late_widgets(
    host, downloads, monkeypatch, action
):
    dialog, pump, app = downloads
    pump(lambda: "downloaded episode(s)" in dialog._summary.GetLabel())
    if action == "refresh":
        dialog._refresh()
    else:
        dialog._on_remove_show_downloads(None)
    host.until(lambda: bool(host._task_manager.queued))
    future = host._task_manager.start_next()
    future.result(timeout=10)
    dialog._cancel_ui()
    dialog.dialog.Destroy()
    app.Yield()

    def late(_message):
        raise AssertionError("The closed dialog received a late announcement")

    monkeypatch.setattr(dialog, "_announce", late)
    host.drain()
    assert _episode(host).downloaded_path
    assert not host.saved


def test_downloads_modal_has_safe_default_and_an_operable_native_close_button(downloads):
    import wx

    dialog, _pump, _app = downloads
    inspected = []

    def close():
        button = dialog.dialog.GetDefaultItem()
        inspected.append((
            dialog.dialog.GetAffirmativeId(),
            dialog.dialog.GetEscapeId(),
            button.GetId(),
        ))
        button.Command(wx.CommandEvent(wx.EVT_BUTTON.typeId, wx.ID_CANCEL))

    timed_out = []

    def timeout():
        timed_out.append(True)
        dialog.dialog.EndModal(wx.ID_CANCEL)

    fallback = wx.CallLater(1000, timeout)
    timer = wx.CallLater(20, close)
    try:
        dialog.show()
    finally:
        timer.Stop()
        fallback.Stop()
    assert not timed_out
    assert inspected == [(wx.ID_CANCEL, wx.ID_CANCEL, wx.ID_CANCEL)]
    assert dialog._closed
