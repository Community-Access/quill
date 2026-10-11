"""Persisting the podcast library, at any size (QUILL Cast 1.1.0).

One method, ``_save_podcast_library``, is called from everywhere: a position
checkpoint on every pause, a finished download, a mark-as-played, every
folder and favourite action, and every dialog that changes anything. For a
normal library that is free.

It stops being free at scale. Measured against a real 1,307-feed OPML export
once every show has been refreshed -- about 196,000 episodes -- one full
write serializes to a 164 MB JSON document and takes roughly seven seconds.
Running that inside a pause would freeze the window for seconds, every time.

Above a threshold writes coalesce onto a short timer. At every size, detached
copies are prepared in bounded UI turns and atomic writes run on a worker.
The shutdown path forces the final generation.

(The same shape as the bug that got Earshot force-quit by iOS: per-save work
that grows with the library until it exceeds the save cadence.)
"""

from __future__ import annotations

import copy
import logging
import threading
from time import perf_counter
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.podcasts.subscriptions import PodcastLibrary, save_library
from quill.ui.podcasts.library_snapshot import (
    EPISODES_PER_TURN,
    ITEMS_PER_TURN,
    TURN_BUDGET_SECONDS,
)
from quill.ui.podcasts.payload_snapshot import PAYLOAD_TURN_BUDGET_SECONDS
from quill.ui.podcasts.save_snapshot import Changes, coherent_chunks, current_scope

logger = logging.getLogger(__name__)

#: Above this many episodes, writes coalesce. See the module docstring.
COALESCE_SAVE_ABOVE_EPISODES = 20_000
COALESCE_SAVE_DELAY_MS = 4000
SHUTDOWN_SAVE_WAIT_SECONDS = 3.0
SNAPSHOT_SHOWS_PER_TURN = 4
SNAPSHOT_ITEMS_PER_TURN = ITEMS_PER_TURN
SNAPSHOT_EPISODES_PER_TURN = EPISODES_PER_TURN


class PodcastLibrarySaveMixin:
    """Coalescing library persistence."""

    def _podcast_library_is_large(self) -> bool:
        """Whether this library is big enough that saves must be coalesced.

        Stop once the threshold is crossed. View labels ask this repeatedly,
        and they need a threshold decision, not the whole catalogue's count.
        """
        total = 0
        for show in self._podcast_library.shows:
            total += len(show.episodes)
            if total > COALESCE_SAVE_ABOVE_EPISODES:
                return True
        return False

    def _save_podcast_library(self) -> None:
        """Persist asynchronously, coalescing mutations in a large library.

        See :data:`COALESCE_SAVE_ABOVE_EPISODES` for why the second mode
        exists and what it costs.
        """
        if getattr(self, "_podcast_library_loading", False):
            raise RuntimeError("The saved podcast library is still loading; no changes were saved")
        self._podcast_library_revision = int(getattr(self, "_podcast_library_revision", 0)) + 1
        scope = current_scope()
        state = getattr(self, "_podcast_snapshot_state", None)
        if scope is None:
            self._podcast_unscoped_revision = (
                int(getattr(self, "_podcast_unscoped_revision", 0)) + 1
            )
        elif state is not None:
            state["changes"].record(scope)
        self._podcast_library_dirty = True
        if getattr(self, "_cast_closing", False):
            return
        if getattr(self, "_check_run", None) is not None:
            self._schedule_podcast_library_flush()
        elif self._podcast_library_is_large():
            self._schedule_podcast_library_flush()
        else:
            self._flush_podcast_library()
        settings = self._podcast_library.settings
        self._podcast_download_queue.set_reconnect_settings(
            enabled=settings.reconnect_enabled,
            max_attempts=settings.reconnect_max_attempts,
            wait_seconds=settings.reconnect_wait_seconds,
        )

    def _schedule_podcast_library_flush(self) -> None:
        """Start (or leave running) the coalescing timer."""
        timer = getattr(self, "_podcast_save_timer", None)
        if timer is None:
            timer = self._wx.Timer(self.frame)
            self.frame.Bind(self._wx.EVT_TIMER, self._on_podcast_save_timer, timer)
            self._podcast_save_timer = timer
        if not timer.IsRunning():
            timer.Start(COALESCE_SAVE_DELAY_MS, oneShot=True)

    def _on_podcast_save_timer(self, event: object) -> None:
        timer = getattr(self, "_podcast_save_timer", None)
        if timer is not None and event.GetId() != timer.GetId():
            event.Skip()
            return
        self._flush_podcast_library()

    def _flush_podcast_library(self) -> None:
        """Snapshot and persist a large library without blocking wx.

        The live model remains UI-owned. Each submitted write receives a
        detached generation. Writes are serialized, and a newer generation
        replaces any pending snapshot so an older write cannot win.
        """
        timer = getattr(self, "_podcast_save_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()
        if not getattr(self, "_podcast_library_dirty", False):
            return
        force_async = bool(getattr(self, "_podcast_save_force_async", False))
        wx = getattr(self, "_wx", None)
        if not force_async and callable(getattr(wx, "CallLater", None)):
            if getattr(self, "_podcast_snapshot_state", None) is None:
                self._begin_podcast_library_snapshot()
            return

        generation = int(getattr(self, "_podcast_save_generation", 0)) + 1
        snapshot = copy.deepcopy(self._podcast_library)
        self._queue_podcast_library_snapshot(generation, snapshot)

    def _begin_podcast_library_snapshot(self) -> None:
        """Copy a large library in short UI turns, never in one long freeze."""
        if (
            getattr(self, "_cast_closing", False)
            or getattr(self, "_podcast_snapshot_state", None) is not None
        ):
            return
        if getattr(self, "_podcast_commit_depth", 0):
            self._podcast_snapshot_later = self._wx.CallLater(
                10, self._begin_podcast_library_snapshot
            )
            return
        library = self._podcast_library
        json_payload = isinstance(library, PodcastLibrary)
        revision = int(getattr(self, "_podcast_unscoped_revision", 0))
        changes = Changes()
        state: dict[str, Any] = {
            "library": library,
            "revision": revision,
            "changes": changes,
            "chunks": coherent_chunks(self, changes, json_payload=json_payload),
            "turn_budget": PAYLOAD_TURN_BUDGET_SECONDS if json_payload else TURN_BUDGET_SECONDS,
        }
        self._podcast_snapshot_state = state
        self._continue_podcast_library_snapshot()

    def _continue_podcast_library_snapshot(self) -> None:
        state = self._podcast_snapshot_state
        if state is None:
            return
        wx = self._wx

        if state["library"] is not self._podcast_library or state["revision"] != int(
            getattr(self, "_podcast_unscoped_revision", 0)
        ):
            state["chunks"].close()
            self._podcast_snapshot_state = None
            self._podcast_snapshot_later = wx.CallLater(1, self._begin_podcast_library_snapshot)
            return
        deadline = perf_counter() + state["turn_budget"]
        while True:
            try:
                next(state["chunks"])
            except StopIteration as result:
                self._podcast_snapshot_state = None
                generation = int(getattr(self, "_podcast_save_generation", 0)) + 1
                self._queue_podcast_library_snapshot(
                    generation,
                    result.value,
                    revision=int(getattr(self, "_podcast_library_revision", 0)),
                )
                return
            except Exception:
                self._podcast_snapshot_state = None
                logger.exception("Could not prepare a podcast library save")
                self._announce(
                    "Could not prepare the podcast library save. Changes remain pending."
                )
                return
            if perf_counter() >= deadline:
                self._podcast_snapshot_later = wx.CallLater(
                    1, self._continue_podcast_library_snapshot
                )
                return

    def _queue_podcast_library_snapshot(
        self, generation: int, snapshot: Any, *, revision: int | None = None
    ) -> None:
        self._podcast_save_generation = generation
        self._podcast_library_dirty = True
        lock = self._podcast_save_lock()
        with lock:
            pending = getattr(self, "_podcast_save_pending", None)
            if pending is None or generation > pending[0]:
                self._podcast_save_pending = (
                    generation,
                    snapshot,
                    int(getattr(self, "_podcast_library_revision", 0))
                    if revision is None
                    else revision,
                )
        self._start_podcast_library_write()

    def _podcast_save_lock(self) -> threading.Lock:
        lock = getattr(self, "_podcast_save_state_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._podcast_save_state_lock = lock
        return lock

    def _start_podcast_library_write(self) -> None:
        lock = self._podcast_save_lock()
        with lock:
            if getattr(self, "_podcast_save_worker_running", False):
                return
            if getattr(self, "_podcast_save_pending", None) is None:
                return
            self._podcast_save_worker_running = True
            run_id = int(getattr(self, "_podcast_save_worker_id", 0)) + 1
            self._podcast_save_worker_id = run_id
        data_dir = app_data_dir()

        def _write(**_kwargs: Any) -> int:
            saved_generation = 0
            while True:
                with lock:
                    pending = getattr(self, "_podcast_save_pending", None)
                    self._podcast_save_pending = None
                    if pending is None:
                        self._podcast_save_worker_running = False
                        return saved_generation
                generation, snapshot, revision = pending
                try:
                    save_library(data_dir, snapshot)
                except Exception:
                    with lock:
                        newer_pending = getattr(self, "_podcast_save_pending", None)
                        if newer_pending is None:
                            self._podcast_save_pending = pending
                            self._podcast_save_worker_running = False
                    if newer_pending is None:
                        if getattr(self, "_podcast_save_shutdown_app", ""):
                            self._record_podcast_final_save_failure(data_dir)
                        raise
                    logger.exception(
                        "A superseded podcast library snapshot failed; writing the newer snapshot"
                    )
                else:
                    saved_generation = generation
                    with lock:
                        self._podcast_save_written_revision = revision

        def _success(_operation: str, saved_generation: int) -> None:
            if run_id != getattr(self, "_podcast_save_worker_id", None):
                return
            self._podcast_save_task = None
            with lock:
                pending = getattr(self, "_podcast_save_pending", None)
                written_revision = getattr(self, "_podcast_save_written_revision", None)
            if (
                saved_generation == getattr(self, "_podcast_save_generation", 0)
                and pending is None
                and written_revision == int(getattr(self, "_podcast_library_revision", 0))
                and getattr(self, "_podcast_snapshot_state", None) is None
            ):
                self._podcast_library_dirty = False
                message = getattr(self, "_podcast_save_success_message", "")
                if message:
                    self._podcast_save_success_message = ""
                    self._announce(message)
            else:
                self._podcast_library_dirty = True

        def _failure(_operation: str, error: BaseException) -> None:
            if run_id != getattr(self, "_podcast_save_worker_id", None):
                return
            self._podcast_save_task = None
            self._podcast_library_dirty = True
            self._podcast_save_success_message = ""
            self._announce(
                "Could not save the podcast library. Your latest changes are still pending. "
                f"{error}"
            )

        from quill.stability.task_manager import TaskManager

        manager = self._task_manager
        if type(manager) is TaskManager:
            pool = getattr(self, "_podcast_save_pool", None)
            if pool is None:
                pool = TaskManager(max_workers=1)
                self._podcast_save_pool = pool
            manager = pool
        options = {}
        if type(manager) is TaskManager:
            options["ui_lifetime"] = getattr(self, "_cast_ui_lifetime", None)
        self._podcast_save_task = manager.submit(
            "podcast-library-save",
            _write,
            on_success=_success,
            on_failure=_failure,
            **options,
        )

    def _record_podcast_final_save_failure(self, data_dir: Any) -> None:
        from quill.core.shutdown_report import (
            MUST_RECORD,
            ShutdownFailure,
            ShutdownReport,
            pending_path,
        )
        from quill.core.storage import read_json

        ready = getattr(self, "_podcast_final_report_ready", None)
        if ready is not None:
            ready.wait()
        app_id = self._podcast_save_shutdown_app
        report = ShutdownReport(app_id, "QUILL Cast")
        raw = read_json(pending_path(data_dir, app_id), default={})
        steps = raw.get("steps", []) if isinstance(raw, dict) else []
        for step in dict.fromkeys([*steps, "podcast_library"]):
            report.failures.append(ShutdownFailure(str(step), MUST_RECORD, "FinalWriteFailed"))
        report.persist(data_dir)

    def _flush_podcast_library_for_shutdown(self, *, transfer_ownership: bool = False) -> None:
        """Start the final generation and wait briefly; its worker drains newer data."""
        later = getattr(self, "_podcast_snapshot_later", None)
        if later is not None:
            later.Stop()
            self._podcast_snapshot_later = None
        state = getattr(self, "_podcast_snapshot_state", None)
        if state is not None:
            state["chunks"].close()
        self._podcast_snapshot_state = None
        if transfer_ownership:
            # Called only after the player, transfers and feed checks have stopped.
            # The closing host relinquishes the model to its ordered writer.
            self._podcast_save_shutdown_app = "cast"
            if getattr(self, "_podcast_library_dirty", False):
                generation = int(getattr(self, "_podcast_save_generation", 0)) + 1
                self._queue_podcast_library_snapshot(generation, self._podcast_library)
            pool = getattr(self, "_podcast_save_pool", None)
            if pool is not None:
                pool.shutdown(wait=False, cancel_pending=False)
            return
        self._podcast_save_force_async = True
        try:
            for attempt in range(2):
                self._flush_podcast_library()
                task = getattr(self, "_podcast_save_task", None)
                future = getattr(task, "future", None)
                if future is None:
                    return
                from concurrent.futures import TimeoutError

                try:
                    saved_generation = future.result(timeout=SHUTDOWN_SAVE_WAIT_SECONDS)
                except TimeoutError:
                    logger.warning(
                        "Podcast library save is still running after the bounded shutdown wait"
                    )
                    return
                except Exception:
                    if attempt:
                        raise
                    logger.exception("Podcast library save failed during shutdown; retrying once")
                    continue
                with self._podcast_save_lock():
                    pending = getattr(self, "_podcast_save_pending", None)
                if (
                    saved_generation == getattr(self, "_podcast_save_generation", 0)
                    and pending is None
                ):
                    self._podcast_library_dirty = False
                return
        finally:
            del self._podcast_save_force_async
