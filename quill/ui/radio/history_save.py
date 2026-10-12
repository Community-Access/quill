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


def save_history_async(host: Any, history: RadioHistory | None = None) -> bool:
    """Queue the host's current history snapshot without blocking the UI."""
    try:
        coordinator = getattr(host, "_radio_history_save_coordinator", None)
        if coordinator is None:
            announce = getattr(host, "_announce", None)
            coordinator = RadioHistorySaveCoordinator(announce if callable(announce) else None)
            host._radio_history_save_coordinator = coordinator
        from quill.core.paths import app_data_dir

        selected_history = history if history is not None else host._radio_history
        coordinator.save(app_data_dir(), selected_history)
    except Exception:
        logger.exception("Could not queue a Radio history snapshot")
        announce = getattr(host, "_announce", None)
        if callable(announce):
            announce(_FAILURE_MESSAGE)
        return False
    return True


def close_history_writer(host: Any) -> bool:
    """Stop accepting Radio snapshots and perform a bounded final flush."""
    coordinator = getattr(host, "_radio_history_save_coordinator", None)
    if coordinator is None:
        return True
    return bool(coordinator.close())
