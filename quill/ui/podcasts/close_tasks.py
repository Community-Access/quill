"""A responsive close: stop mutators, finish Undo work, then surrender the library."""

from __future__ import annotations

import copy
import logging
import threading
from queue import Empty
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.podcasts import history as podcast_history
from quill.core.shutdown_report import (
    BACKGROUND,
    BEST_EFFORT,
    MUST_RECORD,
    ShutdownFailure,
    ShutdownReport,
)
from quill.stability.task_manager import TaskManager
from quill.ui.podcasts.lifecycle import cancel_preparations
from quill.ui.undo_file_jobs import pending_for

logger = logging.getLogger(__name__)
CLOSE_POLL_MS = 50


def begin(host: Any, *, forced: bool = False) -> bool:
    if getattr(host, "_cast_shutdown_finished", False):
        return True
    if not getattr(host, "_cast_closing", False):
        host._cast_closing = True
        report = ShutdownReport("cast", "QUILL Cast")
        host._cast_close_report = report
        steps: list[tuple[str, str, Any]] = []
        steps.append((
            "quillins",
            BEST_EFFORT,
            getattr(getattr(host, "_app_host", None), "shutdown", None),
        ))
        windows = getattr(host, "_windows", None)
        now_playing = getattr(host, "_now_playing_window", None)
        if now_playing is not None:
            if windows is not None:
                steps.append((
                    "now_playing_registry",
                    BEST_EFFORT,
                    lambda: windows.unregister(now_playing.frame),
                ))
            steps.append(("now_playing_window", BEST_EFFORT, now_playing.destroy))
        if windows is not None:
            steps.append((
                "peer_windows",
                BEST_EFFORT,
                lambda: windows.destroy_all_except(host.frame),
            ))
        steps.append(("preparations", BEST_EFFORT, lambda: cancel_preparations(host)))
        # A check of many feeds and a search in flight are told to stop, so the
        # worker threads let go at their next read rather than finishing (F-09).
        steps.append((
            "background_work",
            BEST_EFFORT,
            getattr(host, "_stop_cast_background_work", None),
        ))
        for value in list(vars(host).values()):
            if isinstance(value, host._wx.Timer):
                steps.append(("timer", BEST_EFFORT, value.Stop))
        watcher = getattr(host, "_folder_watcher", None)
        steps.append(("folder_watch", BEST_EFFORT, getattr(watcher, "RemoveAll", None)))
        for name, action in (
            (
                "feed_monitor",
                getattr(getattr(host, "_podcast_check_monitor", None), "shutdown", None),
            ),
            ("scan_hold", getattr(getattr(host, "_scan_hold", None), "shutdown", None)),
            ("player", getattr(getattr(host, "_podcast_controller", None), "shutdown", None)),
            ("transfers", getattr(host, "_shutdown_podcast_transfers", None)),
        ):
            steps.append((name, BEST_EFFORT, action))
        from quill.ui.podcasts.feed_refresh import shutdown_feed_checks

        steps.extend((
            ("feed_checks", BACKGROUND, lambda: shutdown_feed_checks(host)),
            (
                "tasks",
                BACKGROUND,
                lambda: host._task_manager.shutdown(wait=False, cancel_pending=True),
            ),
            ("listening_stats", MUST_RECORD, host._podcast_flush_stats),
            ("last_seen", MUST_RECORD, host._stamp_last_seen),
            ("media_keys", BEST_EFFORT, host._unregister_media_keys),
            ("global_hotkeys", BEST_EFFORT, host._unregister_global_hotkeys),
            ("tray", BEST_EFFORT, host._remove_tray_icon),
        ))
        host._cast_close_steps = iter(steps)
        host._announce("Closing Cast: finishing file operations and saving your changes.")
        for window in list(host._wx.GetTopLevelWindows()):
            ancestor = window
            while ancestor is not None and ancestor is not host.frame:
                ancestor = ancestor.GetParent()
            if ancestor is host.frame:
                window.Enable(False)

    if forced:
        for name, category, action in getattr(host, "_cast_close_steps", ()) or ():
            host._cast_close_report.step(name, category, action)
        if pending_for(host):
            host._cast_close_report.failures.append(
                ShutdownFailure("file_operations", MUST_RECORD, "Interrupted")
            )
        start_final_writes(host)
        return True
    host._cast_close_later = host._wx.CallLater(1, advance_close, host)
    return False


def advance_close(host: Any) -> None:
    """Release the event loop after each teardown step, including native closes."""
    host._cast_close_later = None
    if getattr(host, "_cast_closed", False):
        return
    try:
        name, category, action = next(host._cast_close_steps)
    except StopIteration:
        host._cast_close_steps = None
        poll(host)
        return
    host._cast_close_report.step(name, category, action)
    host._cast_close_later = host._wx.CallLater(1, advance_close, host)


def start_final_writes(host: Any) -> None:
    if getattr(host, "_cast_close_task", None) is not None:
        return
    data_dir = app_data_dir()
    history = copy.deepcopy(host._podcast_history)
    report = host._cast_close_report
    ready = threading.Event()
    host._podcast_final_report_ready = ready
    record_pool = getattr(host, "_podcast_record_tasks", None)
    record_tasks = record_pool.snapshot() if record_pool is not None else []
    failures = getattr(host, "_podcast_record_failures", None)
    close_pool = TaskManager(max_workers=1)
    host._cast_close_pool = close_pool

    def write_metadata(**_kwargs: Any) -> None:
        try:
            for task in record_tasks:
                try:
                    task.future.result()
                except Exception:
                    logger.warning("A final podcast bookkeeping write failed", exc_info=True)
            if failures is not None:
                while True:
                    try:
                        step, error_type = failures.get_nowait()
                    except Empty:
                        break
                    report.failures.append(ShutdownFailure(step, MUST_RECORD, error_type))
            report.step(
                "cast_history", MUST_RECORD, lambda: podcast_history.save_history(data_dir, history)
            )
            report.persist(data_dir)
        finally:
            ready.set()

    host._cast_close_task = close_pool.submit("cast-final-settings", write_metadata)
    if not getattr(host, "_podcast_library_loading", False):
        host._flush_podcast_library_for_shutdown(transfer_ownership=True)
    if record_pool is not None:
        record_pool.shutdown(wait=False, cancel_pending=False)
    close_pool.shutdown(wait=False, cancel_pending=False)


def poll(host: Any) -> None:
    host._cast_close_later = None
    if getattr(host, "_cast_closed", False):
        return
    if not pending_for(host):
        start_final_writes(host)
        tasks = [
            getattr(host, "_cast_close_task", None),
            getattr(host, "_podcast_save_task", None),
        ]
        if all(task is None or task.future.done() for task in tasks):
            failed = bool(host._cast_close_report.must_record_failures)
            for task in tasks:
                if task is not None:
                    try:
                        task.future.result()
                    except Exception:
                        failed = True
                        logger.warning(
                            "A final Cast write failed; recovery was recorded", exc_info=True
                        )
            if failed:
                host._announce(
                    "Cast could not save some final changes. Please check Recent Problems "
                    "when it next opens."
                )
            host._cast_shutdown_finished = True
            host.frame.Enable(True)
            host.frame.Close()
            return
    host._cast_close_later = host._wx.CallLater(CLOSE_POLL_MS, poll, host)
