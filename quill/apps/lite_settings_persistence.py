"""Session-safe settings persistence and failure feedback for QUILL Lite."""

from __future__ import annotations

import logging

import wx

from quill.core.lite import settings as settings_mod

logger = logging.getLogger(__name__)

SETTINGS_NOT_SAVED = (
    "Settings could not be saved. They remain active for this session. Reopen Preferences to retry."
)


class LiteSettingsPersistenceMixin:
    """Keep failed preferences usable and their persistence state reviewable."""

    settings_dirty = False
    _settings_notice_pending = False

    def save_settings(self) -> bool:
        try:
            settings_mod.save(self.settings)
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
