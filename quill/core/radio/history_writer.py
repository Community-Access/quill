"""Single-threaded, coalescing writer for detached Radio history snapshots."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

Snapshot = dict[str, object]
WriteSnapshot = Callable[[Path, Snapshot], None]
FailureCallback = Callable[[int, Exception], None]


class RadioHistorySnapshotWriter:
    """Write snapshots serially, replacing queued work with the newest generation."""

    def __init__(self, write_snapshot: WriteSnapshot | None = None) -> None:
        if write_snapshot is None:
            from quill.core.radio.history_store import save_history_snapshot

            write_snapshot = save_history_snapshot
        self._write_snapshot = write_snapshot
        self._condition = threading.Condition()
        self._generation = 0
        self._completed_generation = 0
        self._completed_success = True
        self._pending: tuple[int, Path, Snapshot, FailureCallback | None] | None = None
        self._active = False
        self._closing = False
        self._thread = threading.Thread(
            target=self._run,
            name="quill-radio-history-writer",
            daemon=True,
        )
        self._thread.start()

    def submit(
        self,
        data_dir: Path,
        snapshot: Snapshot,
        *,
        on_failure: FailureCallback | None = None,
    ) -> int:
        """Queue a detached snapshot and return its monotonically increasing generation."""
        target = Path(data_dir)
        with self._condition:
            if self._closing:
                raise RuntimeError("Radio history writer is closing")
            self._generation += 1
            generation = self._generation
            self._pending = (generation, target, snapshot, on_failure)
            self._condition.notify()
            return generation

    def flush(self, timeout: float) -> bool:
        """Wait at most *timeout* for the newest submitted generation to finish."""
        deadline = time.monotonic() + max(0.0, timeout)
        with self._condition:
            while self._active or self._pending is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return self._completed_generation == self._generation and self._completed_success

    def close(self, timeout: float) -> bool:
        """Stop accepting snapshots and wait a bounded time for the latest write."""
        with self._condition:
            self._closing = True
            self._condition.notify_all()
        return self.flush(timeout)

    def _write_with_folder(self, data_dir: Path, snapshot: Snapshot) -> None:
        """Write, recreating a data folder that vanished under the writer.

        The folder can go between the moment a save is queued and the moment
        it is written -- a cleanup tool, a synced folder briefly offline, a
        test's temporary folder removed while its window's last save was in
        flight. A missing folder is not a reason to lose the listener's
        settings: it is made again and the write tried once more. Any other
        failure, or a second one, is reported as before.
        """
        try:
            self._write_snapshot(data_dir, snapshot)
        except FileNotFoundError:
            logger.warning("Radio data folder was missing; recreating it: %s", data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            self._write_snapshot(data_dir, snapshot)

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending is None and not self._closing:
                    self._condition.wait()
                if self._pending is None:
                    return
                generation, data_dir, snapshot, on_failure = self._pending
                self._pending = None
                self._active = True

            success = True
            try:
                self._write_with_folder(data_dir, snapshot)
            except Exception as exc:
                success = False
                logger.exception("Radio history write failed at generation %d", generation)
                with self._condition:
                    is_latest = generation == self._generation
                if on_failure is not None and is_latest:
                    try:
                        on_failure(generation, exc)
                    except Exception:
                        logger.exception(
                            "Radio history failure callback failed at generation %d", generation
                        )
            finally:
                with self._condition:
                    self._completed_generation = generation
                    if generation == self._generation:
                        self._completed_success = success
                    self._active = False
                    self._condition.notify_all()
