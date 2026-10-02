"""Session-safe settings persistence and failure feedback for QUILL Lite."""

from __future__ import annotations

import logging

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

    def _ensure_write_reports(self) -> None:
        """Failed writes reach Activity with Retry and Open Folder (qc.md F-01).

        Recorded, not spoken: this mixin already says SETTINGS_NOT_SAVED, once.
        """
        if getattr(self, "_stop_write_reports", None) is None:
            from quill.ui.persistence_reporting import install

            self._stop_write_reports = install(self, speak=False)

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
            import copy

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
