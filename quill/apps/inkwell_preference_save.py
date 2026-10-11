"""Coalesced background persistence for Quill Inkwell preferences."""

from __future__ import annotations

import copy
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.expansion.settings import InkwellSettings, save_settings

logger = logging.getLogger(__name__)


class InkwellPreferenceSaver:
    """Persist the newest preference snapshot without blocking the wx thread."""

    def __init__(
        self,
        data_dir: Path,
        task_manager: Any,
        announce: Callable[[str], None],
    ) -> None:
        self._data_dir = data_dir
        self._task_manager = task_manager
        self._announce = announce
        self._lock = threading.Lock()
        self._generation = 0
        self._pending: tuple[int, InkwellSettings] | None = None
        self._latest: tuple[int, InkwellSettings] | None = None
        self._running = False
        self._task: Any = None
        self._failed_generation: int | None = None
        self._reported_generation: int | None = None
        self._dirty = False

    def queue(self, settings: InkwellSettings) -> None:
        snapshot = copy.deepcopy(settings)
        with self._lock:
            self._generation += 1
            generation = self._generation
            item = (generation, snapshot)
            self._pending = item
            self._latest = item
            if self._running:
                return
            self._running = True

        try:
            self._task = self._task_manager.submit(
                "inkwell-preference-save",
                self._persist_pending,
                on_success=self._save_succeeded,
                on_failure=self._save_failed,
                safe_to_cancel=False,
            )
        except RuntimeError:
            with self._lock:
                self._running = False
                self._dirty = True
                self._failed_generation = generation
            logger.warning("INKWELL-SETTINGS-WRITE: could not queue preference persistence")
            self._report_failure(generation)

    def _persist_pending(self, **_task_args: Any) -> int:
        latest_generation = 0
        while True:
            with self._lock:
                pending = self._pending
                self._pending = None
                if pending is None:
                    self._running = False
                    return latest_generation
            generation, settings = pending
            try:
                save_settings(self._data_dir, settings)
            except OSError:
                with self._lock:
                    if generation != self._generation:
                        continue
                    self._dirty = True
                    self._failed_generation = generation
                    self._running = False
                raise
            with self._lock:
                latest_generation = generation
                if generation == self._generation:
                    self._dirty = False
                    self._failed_generation = None

    def _save_failed(self, _operation_id: str, _error: BaseException) -> None:
        with self._lock:
            generation = self._failed_generation
        if generation is None:
            return
        logger.warning("INKWELL-SETTINGS-WRITE: preference persistence failed")
        self._report_failure(generation)

    def _report_failure(self, generation: int) -> None:
        with self._lock:
            if (
                generation != self._generation
                or generation != self._failed_generation
                or not self._dirty
                or generation == self._reported_generation
            ):
                return
            self._reported_generation = generation
        self._announce(
            "Inkwell preferences could not be saved. Changes remain active for this session."
        )

    def _save_succeeded(self, _operation_id: str, generation: Any) -> None:
        with self._lock:
            if generation != self._generation or self._dirty or self._reported_generation is None:
                return
            self._reported_generation = None
        self._announce("Inkwell preferences saved now, after the earlier failure.")

    def flush(self) -> None:
        """Finish queued writes and synchronously retry the newest dirty snapshot."""
        with self._lock:
            task = self._task
        if task is not None:
            try:
                task.future.result()
            except OSError:
                pass

        with self._lock:
            latest = self._latest
            needs_write = self._dirty or self._pending is not None
        if not needs_write or latest is None:
            return

        generation, settings = latest
        try:
            save_settings(self._data_dir, settings)
        except OSError:
            with self._lock:
                self._dirty = True
                self._failed_generation = generation
            self._report_failure(generation)
            return
        with self._lock:
            self._pending = None
            self._dirty = False
            self._failed_generation = None
        self._save_succeeded("", generation)
