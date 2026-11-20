"""Session-safe settings persistence and failure feedback for QUILL Lite.

**One ordered save.** Settings reach the disk two ways: View commands queue a
snapshot for a background writer, and Preferences, the session and shutdown
save synchronously. Both go through :meth:`_write_snapshot`, which holds one
write lock across *read the disk, merge, write, move the baseline*, and every
snapshot is numbered when it is taken. A snapshot older than one already
written is dropped rather than written, so a paused background write can no
longer land after a newer synchronous one and put the old choice back
(plan.md, settings review: queued versus synchronous overlap).

**Baseline discipline.** The merge baseline is read under that lock at write
time, never captured with the snapshot, and moves after *every* successful
write, not only the newest. Capturing it early is what made a quick
True -> False -> True revert write ``[False, False]`` and clear the dirty flag:
the second snapshot was compared with a baseline the first write had already
overtaken, looked unchanged, and kept the disk's False.

The dirty flag is cleared only when the newest snapshot is on disk, and set
only when the newest one failed. Activity's Retry writes what is current, never
the snapshot that failed (``persistence_outcome.retry_with``).
"""

from __future__ import annotations

import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import wx

from quill.core import persistence_outcome
from quill.core.lite import settings as settings_mod
from quill.core.lite import settings_merge

logger = logging.getLogger(__name__)

SETTINGS_NOT_SAVED = (
    "Settings could not be saved. They remain active for this session. "
    "Shift+F9 opens Activity, with Retry and Open Folder."
)


class LiteSettingsPersistenceMixin:
    """Keep failed preferences usable and their persistence state reviewable."""

    settings_dirty = False
    _settings_notice_pending = False

    # -- ordering ---------------------------------------------------------- #

    def _settings_order(self) -> Lock:
        """The lock guarding snapshot numbers; creates the ordering state once."""
        if "_settings_save_lock" not in self.__dict__:
            self._settings_save_lock = Lock()
            #: Serialises merge + write + baseline, for both kinds of save.
            self._settings_write_lock = Lock()
            self._settings_save_generation = 0
            self._settings_written_generation = 0
            self._settings_save_executor: ThreadPoolExecutor | None = None
            self._settings_save_future = None
            self._settings_save_pending = None
        return self._settings_save_lock

    def _take_snapshot(self) -> tuple[int, settings_mod.Settings]:
        """Number and copy the settings as they are now (UI thread)."""
        with self._settings_order():
            self._settings_save_generation += 1
            return self._settings_save_generation, copy.deepcopy(self.settings)

    def _is_newest(self, generation: int) -> bool:
        with self._settings_order():
            return generation == self._settings_save_generation

    def _write_snapshot(self, generation: int, snapshot: settings_mod.Settings) -> bool:
        """Write *snapshot* in order. ``True`` when it, or something newer, is on disk."""
        self._settings_order()
        with self._settings_write_lock:
            if generation <= self._settings_written_generation:
                return True  # a newer snapshot already reached the disk
            to_write = snapshot
            baseline = getattr(self, "_settings_baseline", None)
            # A three-way merge against the file as it is now, when this process
            # knows what it loaded: a second QUILL Lite started with
            # --new-instance writes the same file, and saving our whole copy
            # undid its changes (qc.md F-11). Without a baseline -- a stub, or
            # before OnInit -- the plain whole-object write is the honest one.
            if baseline is not None:
                disk = settings_merge.load_if_present()
                if disk is not None:
                    to_write = settings_merge.merge_for_save(baseline, snapshot, disk)
            try:
                with persistence_outcome.retry_with(self._retry_settings_save):
                    settings_mod.save(to_write)
            except OSError:
                logger.warning("QUILL-LITE-SETTINGS-WRITE: settings storage unavailable")
                if self._is_newest(generation):
                    self.settings_dirty = True
                    self._queue_settings_failure_report()
                return False
            self._settings_written_generation = generation
            if baseline is not None:
                self._settings_baseline = copy.deepcopy(snapshot)
            if self._is_newest(generation):
                self.settings_dirty = False
            return True

    # -- the two ways in --------------------------------------------------- #

    def _queue_settings_save(self) -> None:
        """Persist a detached, latest-wins settings snapshot off the UI thread."""
        self._ensure_write_reports()
        snapshot = self._take_snapshot()
        with self._settings_order():
            if self._settings_save_executor is None:
                self._settings_save_executor = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="quill-lite-settings"
                )
                self._settings_save_future = None
            self._settings_save_pending = snapshot
            if self._settings_save_future is None:
                self._settings_save_future = self._settings_save_executor.submit(
                    self._save_settings_queue
                )

    def _save_settings_queue(self) -> None:
        while True:
            with self._settings_order():
                item = self._settings_save_pending
                self._settings_save_pending = None
                if item is None:
                    self._settings_save_future = None
                    return
            self._write_snapshot(*item)

    def save_settings(self) -> bool:
        """Save now, in order with any queued write. ``False`` when it failed."""
        self._ensure_write_reports()
        return self._write_snapshot(*self._take_snapshot())

    def _retry_settings_save(self) -> None:
        """Activity's Retry: write what is current, through the same order."""
        if not self.save_settings():
            raise OSError("QUILL Lite settings are still not saved")

    def flush_settings_writes(self) -> None:
        """Wait for queued writes during shutdown, when durability is required.

        A save queued afterwards starts a fresh writer rather than failing.
        """
        with self._settings_order():
            executor = self._settings_save_executor
            future = self._settings_save_future
        if executor is None:
            return
        if future is not None:
            future.result()
        executor.shutdown(wait=True)
        with self._settings_order():
            if self._settings_save_executor is executor:
                self._settings_save_executor = None
                self._settings_save_future = None

    # -- saying so --------------------------------------------------------- #

    def _queue_settings_failure_report(self) -> None:
        if self._settings_notice_pending:
            return
        self._settings_notice_pending = True
        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after) and not self.shutting_down:
            call_after(self._report_settings_failure)
        else:
            self._report_settings_failure()

    def _ensure_write_reports(self) -> None:
        """Failed writes reach Activity with Retry and Open Folder (qc.md F-01).

        Recorded, not spoken: this mixin already says SETTINGS_NOT_SAVED, once.
        """
        if getattr(self, "_stop_write_reports", None) is None:
            from quill.ui.persistence_reporting import install

            self._stop_write_reports = install(self, speak=False)

    def _load_settings(self) -> settings_mod.Settings:
        """Read the settings, dropping deleted recent files if asked to (QUILL's #14)."""
        from quill.core.recent_documents import drop_missing

        loaded = settings_mod.load()
        if loaded.recent_files_auto_clear_missing:
            loaded.recent_files = drop_missing(loaded.recent_files)
        return loaded

    def _report_settings_failure(self) -> None:
        if not self._settings_notice_pending:
            return
        self._settings_notice_pending = False
        if not self.settings_dirty:
            return
        self.voice.speak(SETTINGS_NOT_SAVED)
        if not self.shutting_down:
            for frame in list(self.frames):
                try:
                    frame._touch_status()
                except RuntimeError:
                    pass
