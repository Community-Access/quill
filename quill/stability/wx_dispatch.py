"""Thread-safe event dispatch from worker threads back to the wx main thread.

Implements: ROADMAP STAB-4 (the ``call_ui_safely`` / event
``EVT_QUILL_TASK_*`` / ``CoalescedUiReporter`` surface that marshals
worker results back to the UI thread without a race) and H-4-core-2
(M-2) from the pre-release review (cross-thread UI updates use
``wx.CallAfter`` / ``call_ui_safely`` rather than touching widgets
directly).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

try:  # pragma: no cover - optional dependency in non-UI test environments
    import wx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - tests can monkeypatch this module
    wx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _FallbackEvent:
    payload: dict[str, Any]


def _build_event(name: str) -> tuple[type[Any], Any]:
    if wx is None:
        return _FallbackEvent, None
    try:  # pragma: no cover - depends on wx being installed in the test env
        import wx.lib.newevent as newevent  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        return _FallbackEvent, None
    # newevent.NewEvent() has no type stubs and the wx import is
    # ``# type: ignore``'d, so mypy sees the return as Any. Cast to the
    # declared return type at the boundary so the rest of the module
    # keeps a clean (type[Any], Any) signature.
    return cast(tuple[type[Any], Any], newevent.NewEvent())


TaskProgressEvent, EVT_QUILL_TASK_PROGRESS = _build_event("progress")
TaskCompletedEvent, EVT_QUILL_TASK_COMPLETED = _build_event("completed")
TaskFailedEvent, EVT_QUILL_TASK_FAILED = _build_event("failed")


def call_ui_safely(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    def wrapped() -> None:
        try:
            func(*args, **kwargs)
        except Exception:
            logger.exception("Exception while running scheduled wx UI callback")

    call_after = getattr(wx, "CallAfter", None) if wx is not None else None
    if callable(call_after):
        call_after(wrapped)
        return
    logger.warning(
        "call_ui_safely: wx.CallAfter unavailable; running %s synchronously on caller thread",
        getattr(func, "__qualname__", repr(func)),
    )
    wrapped()


class CoalescedUiReporter:
    def __init__(self, ui_callback: Callable[..., Any], min_interval_seconds: float = 0.1) -> None:
        self.ui_callback = ui_callback
        self.min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._last_emit = 0.0
        self._pending: tuple[tuple[Any, ...], dict[str, Any]] | None = None
        self._scheduled = False

    def report(self, *args: Any, **kwargs: Any) -> None:
        now = time.monotonic()
        with self._lock:
            self._pending = (args, kwargs)
            if self._scheduled:
                return
            if now - self._last_emit >= self.min_interval_seconds:
                self._scheduled = True
                call_ui_safely(self._flush)

    def _flush(self) -> None:
        with self._lock:
            pending = self._pending
            self._pending = None
            self._last_emit = time.monotonic()
            self._scheduled = False

        if pending is None:
            return
        args, kwargs = pending
        self.ui_callback(*args, **kwargs)
