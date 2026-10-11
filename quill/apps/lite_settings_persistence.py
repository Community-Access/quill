"""Session-safe settings persistence and failure feedback for QUILL Lite."""

from __future__ import annotations

import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import wx

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

    def _queue_settings_save(self) -> None:
        """Persist a detached, latest-wins settings snapshot off the UI thread."""
        self._ensure_write_reports()
        if not hasattr(self, "_settings_save_executor"):
            self._settings_save_lock = Lock()
            self._settings_save_executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="quill-lite-settings"
            )
            self._settings_save_generation = 0
            self._settings_save_pending = None
            self._settings_save_future = None
        with self._settings_save_lock:
            self._settings_save_generation += 1
            self._settings_save_pending = (
                self._settings_save_generation,
                copy.deepcopy(self.settings),
                copy.deepcopy(getattr(self, "_settings_baseline", None)),
            )
            if self._settings_save_future is None:
                self._settings_save_future = self._settings_save_executor.submit(
                    self._save_settings_queue
                )

    def _save_settings_queue(self) -> None:
        while True:
            with self._settings_save_lock:
                item = self._settings_save_pending
                self._settings_save_pending = None
                if item is None:
                    self._settings_save_future = None
                    return
            generation, settings, baseline = item
            to_write = settings
            if baseline is not None:
                disk = settings_merge.load_if_present()
                if disk is not None:
                    to_write = settings_merge.merge_for_save(baseline, settings, disk)
            try:
                settings_mod.save(to_write)
            except OSError:
                with self._settings_save_lock:
                    current = generation == self._settings_save_generation
                if current:
                    self.settings_dirty = True
                    self._queue_settings_failure_report()
                continue
            with self._settings_save_lock:
                current = generation == self._settings_save_generation
            if current:
                self.settings_dirty = False
                if baseline is not None:
                    self._settings_baseline = copy.deepcopy(settings)

    def _queue_settings_failure_report(self) -> None:
        if self._settings_notice_pending:
            return
        self._settings_notice_pending = True
        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after) and not self.shutting_down:
            call_after(self._report_settings_failure)
        else:
            self._report_settings_failure()

    def flush_settings_writes(self) -> None:
        """Wait for queued writes during shutdown, when durability is required."""
        executor = getattr(self, "_settings_save_executor", None)
        if executor is None:
            return
        with self._settings_save_lock:
            future = self._settings_save_future
        if future is not None:
            future.result()
        executor.shutdown(wait=True)
        self._settings_save_executor = None

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

    def save_settings(self) -> bool:
        self._ensure_write_reports()
        # A three-way merge against the file as it is now, when this process
        # knows what it loaded: a second QUILL Lite started with --new-instance
        # writes the same file, and saving our whole copy undid its changes
        # (qc.md F-11). Without a baseline -- a stub, or before OnInit -- the
        # plain whole-object write is the only honest thing to do.
        to_write = self.settings
        baseline = getattr(self, "_settings_baseline", None)
        if baseline is not None:
            disk = settings_merge.load_if_present()
            if disk is not None:
                to_write = settings_merge.merge_for_save(baseline, self.settings, disk)
        try:
            settings_mod.save(to_write)
        except OSError:
            self.settings_dirty = True
            logger.warning("QUILL-LITE-SETTINGS-WRITE: settings storage unavailable")
            if not self._settings_notice_pending:
                self._settings_notice_pending = True
                call_after = getattr(wx, "CallAfter", None)
                if callable(call_after) and not self.shutting_down:
                    call_after(self._report_settings_failure)
                else:
                    self._report_settings_failure()
            return False
        self.settings_dirty = False
        if baseline is not None:
            self._settings_baseline = copy.deepcopy(self.settings)
        return True

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
