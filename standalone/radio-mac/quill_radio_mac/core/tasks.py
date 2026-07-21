"""Background task manager for Quill Radio for Mac.

Ported from upstream ``quill.stability.task_manager`` (the
``TaskManager`` / ``CancellationToken`` / ``QuillTask`` surface), with
the one helper it needs from ``quill.stability.wx_dispatch``
(:func:`call_ui_safely`) vendored in, since this port has no separate
dispatch module.

The radio app submits directory searches, stream probes, link-finder
scans, and update checks here so the UI thread never blocks on the
network. The ``submit`` contract matches upstream exactly: the worker
callable always receives ``cancellation_token``, ``operation_id``, and
``progress_callback`` keyword arguments (callers that do not care absorb
them with ``**_kw``), and the optional ``on_success`` / ``on_failure`` /
``on_progress`` callbacks are marshalled back to the UI thread.

Threading contract: ``submit`` may be called from any thread. Worker
callables run on a small daemon-friendly ``ThreadPoolExecutor`` pool
(``quill-worker`` threads) and must not touch widgets; their results
come back through :func:`call_ui_safely`, which uses ``wx.CallAfter``
when wx is importable and a ``wx.App`` is running, and a logged
synchronous call otherwise -- that fallback is what lets the whole core
test suite run headless, with or without wxPython installed. The
module-level ``import wx`` is optional and monkeypatchable, exactly the
upstream ``wx_dispatch`` idiom. The internal task table is guarded by a
lock; finished tasks remove themselves via a future done-callback.

macOS notes: none beyond the general rule -- on macOS, exactly as on
Windows, only the main thread may touch wx widgets, and ``wx.CallAfter``
is the sanctioned bridge.
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from quill_radio_mac.core.error_codes import CodedError

try:  # pragma: no cover - optional dependency in non-UI test environments
    import wx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - tests can monkeypatch this module
    wx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


# A tiny vocabulary of terminal states for ``QuillTask.result_summary``.
# The dataclass can be shown in diagnostics, so the values stay short
# and human-readable. Anything that has not yet reached a terminal state
# remains ``"pending"``.
TaskResult = Literal["ok", "cancelled", "failed", "pending"]
RESULT_PENDING: TaskResult = "pending"
RESULT_OK: TaskResult = "ok"
RESULT_CANCELLED: TaskResult = "cancelled"
RESULT_FAILED: TaskResult = "failed"


class CancelledError(CodedError):
    """Raised inside a worker by ``raise_if_cancelled`` after a cancel."""

    code = "QUILL-STABILITY-TASK-CANCELLED"


# Vendored from upstream ``quill.stability.wx_dispatch.call_ui_safely``:
# the single bridge from worker threads back to the wx main thread.
def call_ui_safely(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Schedule ``func(*args, **kwargs)`` on the wx main thread.

    Uses ``wx.CallAfter`` when wx is importable *and* a ``wx.App``
    exists; otherwise it logs a warning and runs the callback
    synchronously on the calling thread, so headless test runs (no
    wxPython, or wxPython installed but no running app) exercise the
    same code path without a GUI. The wx.App check is a small port
    deviation from upstream, whose ``wx.CallAfter`` asserts when no app
    object has been created yet; upstream tests monkeypatch the module's
    ``wx`` attribute instead (which still works here too). Exceptions
    inside the callback are logged, never propagated, so a bad UI
    callback cannot kill a worker thread or the main loop.
    """

    def wrapped() -> None:
        try:
            func(*args, **kwargs)
        except Exception:
            logger.exception("Exception while running scheduled wx UI callback")

    call_after = getattr(wx, "CallAfter", None) if wx is not None else None
    app = wx.GetApp() if wx is not None and hasattr(wx, "GetApp") else None
    if callable(call_after) and app is not None:
        call_after(wrapped)
        return
    logger.warning(
        "call_ui_safely: wx.CallAfter unavailable; running %s synchronously on caller thread",
        getattr(func, "__qualname__", repr(func)),
    )
    wrapped()


@dataclass(slots=True)
class CancellationToken:
    """Cooperative cancellation flag handed to every submitted worker."""

    event: threading.Event = field(default_factory=threading.Event)

    def cancel(self) -> None:
        """Signal cancellation; the worker notices at its next check."""
        self.event.set()

    def is_cancelled(self) -> bool:
        """True once :meth:`cancel` has been called."""
        return self.event.is_set()

    def raise_if_cancelled(self) -> None:
        """Raise :class:`CancelledError` when cancellation was requested."""
        if self.is_cancelled():
            raise CancelledError("Operation cancelled")


@dataclass(slots=True)
class QuillTask:
    """One submitted background operation and its bookkeeping.

    ``submitted_at`` is the wall-clock moment the task entered the
    manager; ``result_summary`` is the latest terminal state observed by
    the worker wrapper and is useful in diagnostics.
    """

    operation_id: str
    name: str
    future: concurrent.futures.Future[Any]
    cancellation_token: CancellationToken
    started_at: float
    timeout_seconds: float | None
    safe_to_cancel: bool = True
    safe_to_kill: bool = False
    submitted_at: float = 0.0
    result_summary: TaskResult = RESULT_PENDING


class TaskManager:
    """Thread-pool scheduler whose results marshal back to the UI thread.

    One instance lives for the whole app (created by the frame at
    startup, shut down at exit). Workers receive ``cancellation_token``,
    ``operation_id``, and ``progress_callback`` keyword arguments on
    every call; success/failure callbacks receive the operation id plus
    the result or exception, already marshalled to the UI thread.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="quill-worker",
        )
        self._tasks: dict[str, QuillTask] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        timeout_seconds: float | None = None,
        on_success: Callable[[str, Any], None] | None = None,
        on_failure: Callable[[str, BaseException], None] | None = None,
        on_progress: Callable[[str, Any], None] | None = None,
        safe_to_cancel: bool = True,
        safe_to_kill: bool = False,
        **kwargs: Any,
    ) -> QuillTask:
        """Run ``func`` on a worker thread and marshal callbacks to the UI.

        ``func`` is invoked as ``func(cancellation_token=..., operation_id=...,
        progress_callback=..., **kwargs)``; callers that ignore the injected
        keywords absorb them with ``**_kw``. ``on_success(operation_id,
        result)`` / ``on_failure(operation_id, exception)`` /
        ``on_progress(operation_id, payload)`` all run on the UI thread via
        :func:`call_ui_safely`. Returns the :class:`QuillTask` handle, whose
        ``operation_id`` can be passed to :meth:`cancel`.
        """
        operation_id = str(uuid.uuid4())
        token = CancellationToken()

        def report_progress(payload: Any) -> None:
            if on_progress is None:
                return
            call_ui_safely(on_progress, operation_id, payload)

        def wrapped() -> Any:
            started = time.monotonic()
            logger.info("Task started operation_id=%s name=%s", operation_id, name)
            try:
                result = func(
                    cancellation_token=token,
                    operation_id=operation_id,
                    progress_callback=report_progress,
                    **kwargs,
                )
                duration_ms = (time.monotonic() - started) * 1000
                logger.info(
                    "Task finished operation_id=%s name=%s duration_ms=%.1f",
                    operation_id,
                    name,
                    duration_ms,
                )
                if on_success is not None:
                    call_ui_safely(on_success, operation_id, result)
                return result
            except BaseException as exc:
                duration_ms = (time.monotonic() - started) * 1000
                if isinstance(exc, CancelledError):
                    logger.info(
                        "Task cancelled operation_id=%s name=%s duration_ms=%.1f",
                        operation_id,
                        name,
                        duration_ms,
                    )
                else:
                    logger.exception(
                        "Task failed operation_id=%s name=%s duration_ms=%.1f",
                        operation_id,
                        name,
                        duration_ms,
                    )
                if on_failure is not None:
                    call_ui_safely(on_failure, operation_id, exc)
                # Pre-tag the in-flight task with its terminal state so the
                # done-callback does not have to re-derive it from the
                # future (which can race with ``future.cancelled()`` and
                # surface as ``failed`` for a cooperative cancel).
                if isinstance(exc, CancelledError):
                    task.result_summary = RESULT_CANCELLED
                else:
                    task.result_summary = RESULT_FAILED
                raise

        future = self._executor.submit(wrapped)
        task = QuillTask(
            operation_id=operation_id,
            name=name,
            future=future,
            cancellation_token=token,
            started_at=time.monotonic(),
            timeout_seconds=timeout_seconds,
            safe_to_cancel=safe_to_cancel,
            safe_to_kill=safe_to_kill,
            submitted_at=time.time(),
            result_summary=RESULT_PENDING,
        )
        with self._lock:
            self._tasks[operation_id] = task
        future.add_done_callback(self._make_done_callback(task, operation_id))
        return task

    def _make_done_callback(
        self, task: QuillTask, operation_id: str
    ) -> Callable[[concurrent.futures.Future[Any]], None]:
        def _done(future: concurrent.futures.Future[Any]) -> None:
            # Collapse the future's terminal state into one of the
            # ``TaskResult`` literals. We only fall back to the future when
            # the worker never reached its exception path (e.g. a
            # future.cancel() race after success).
            if task.result_summary == RESULT_PENDING:
                if future.cancelled():
                    task.result_summary = RESULT_CANCELLED
                else:
                    exc = future.exception()
                    task.result_summary = RESULT_OK if exc is None else RESULT_FAILED
            self._remove_task(operation_id)

        return _done

    def cancel(self, operation_id: str) -> bool:
        """Request cancellation of a task; True if the future was cancelled.

        The cooperative token is always set (a running worker sees it at
        its next ``raise_if_cancelled`` check); the return value reflects
        only whether the not-yet-started future could be cancelled outright.
        """
        with self._lock:
            task = self._tasks.get(operation_id)
        if task is None:
            return False
        task.cancellation_token.cancel()
        return task.future.cancel()

    def snapshot(self) -> list[QuillTask]:
        """Return a copy of the current in-flight task list (diagnostics)."""
        with self._lock:
            return list(self._tasks.values())

    def shutdown(self, wait: bool = True, cancel_pending: bool = False) -> None:
        """Shut the pool down at app exit; optionally drop queued tasks."""
        self._executor.shutdown(wait=wait, cancel_futures=cancel_pending)

    def _remove_task(self, operation_id: str) -> None:
        with self._lock:
            self._tasks.pop(operation_id, None)
