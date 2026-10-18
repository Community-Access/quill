"""UI-thread snapshot capture and asynchronous persistence for Radio history."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.radio.history import RadioHistory
from quill.core.radio.history_store import snapshot_history
from quill.core.radio.history_writer import RadioHistorySnapshotWriter
from quill.stability.wx_dispatch import call_ui_safely

logger = logging.getLogger(__name__)

_FAILURE_MESSAGE = "Radio settings could not be saved. Check that Quill can write its settings."
_SHUTDOWN_TIMEOUT_SECONDS = 1.0


class RadioHistorySaveCoordinator:
    """Capture RadioHistory on the UI thread and persist detached snapshots."""

    def __init__(
        self,
        announce: Callable[[str], None] | None,
        *,
        writer: RadioHistorySnapshotWriter | None = None,
        dispatch: Callable[[Callable[[], None]], None] = call_ui_safely,
    ) -> None:
        self._announce = announce
        self._writer = writer or RadioHistorySnapshotWriter()
        self._dispatch = dispatch
        self._alive = True

    @property
    def closed(self) -> bool:
        """True once :meth:`close` ran: the window is going or gone."""
        return not self._alive

    def save(self, data_dir: Path, history: RadioHistory) -> int:
        snapshot = snapshot_history(history)
        return self._writer.submit(data_dir, snapshot, on_failure=self._report_failure)

    def _report_failure(self, _generation: int, _error: Exception) -> None:
        def announce_failure() -> None:
            if self._alive and self._announce is not None:
                self._announce(_FAILURE_MESSAGE)

        self._dispatch(announce_failure)

    def flush(self, timeout: float) -> bool:
        return self._writer.flush(timeout)

    def close(self, timeout: float = _SHUTDOWN_TIMEOUT_SECONDS) -> bool:
        self._alive = False
        finished = self._writer.close(timeout)
        if not finished:
            logger.warning(
                "Radio history writer could not confirm the latest snapshot was saved at shutdown"
            )
        return finished


def _host_is_open(host: Any) -> bool:
    """False once the host's window is being destroyed or is gone.

    A failure that arrives after the listener closed Radio has nobody to tell:
    speaking it then is a sentence about a window that no longer exists, and
    during a test run it was a sentence spoken to whoever sat at the computer
    (Jeff, 2026-10-17). The log keeps it either way.
    """
    window = getattr(host, "frame", None)
    if window is None:
        window = host
    try:
        import wx
    except ImportError:  # pragma: no cover - wx is always present in the UI layer
        return True
    if not isinstance(window, wx.Window):
        return True  # a test host or an embedded controller: nothing to ask
    try:
        return bool(window) and not window.IsBeingDeleted()
    except RuntimeError:  # the wrapped C++ window is already deleted
        return False


def _announcer_for(host: Any) -> Callable[[str], None] | None:
    announce = getattr(host, "_announce", None)
    if not callable(announce):
        return None

    def announce_while_open(message: str) -> None:
        if _host_is_open(host):
            announce(message)
        else:
            logger.warning("Radio history save failed after the window closed; not announced")

    return announce_while_open


def _save_now(data_dir: Path, history: RadioHistory) -> bool:
    """The synchronous save used once the writer has shut down. Never raises."""
    from quill.core.radio.history_store import save_history

    try:
        save_history(data_dir, history)
    except Exception:  # noqa: BLE001 - logged; nobody is left to tell
        logger.exception("Could not save Radio history after its writer closed")
        return False
    return True


def save_history_async(host: Any, history: RadioHistory | None = None) -> bool:
    """Queue the host's current history snapshot without blocking the UI.

    After :func:`close_history_writer` (the window is closing) a late save --
    a timer, a deferred call, a settings change racing the close -- used to
    raise "writer is closing" and be announced as "Radio settings could not be
    saved". It is written synchronously instead, and a failure there is
    logged, not spoken: the window it would be spoken over is gone.
    """
    try:
        from quill.core.paths import app_data_dir

        selected_history = history if history is not None else host._radio_history
        coordinator = getattr(host, "_radio_history_save_coordinator", None)
        if coordinator is not None and coordinator.closed:
            return _save_now(app_data_dir(), selected_history)
        if coordinator is None:
            coordinator = RadioHistorySaveCoordinator(_announcer_for(host))
            host._radio_history_save_coordinator = coordinator
        coordinator.save(app_data_dir(), selected_history)
    except Exception:
        logger.exception("Could not queue a Radio history snapshot")
        announce = _announcer_for(host)
        if announce is not None:
            announce(_FAILURE_MESSAGE)
        return False
    return True


def close_history_writer(host: Any) -> bool:
    """Stop accepting Radio snapshots and perform a bounded final flush."""
    coordinator = getattr(host, "_radio_history_save_coordinator", None)
    if coordinator is None:
        return True
    return bool(coordinator.close())
