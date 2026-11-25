"""Startup timing and deferred services for QUILL Lite."""

from __future__ import annotations

import logging
import time
from typing import Any

__all__ = ["LiteStartupMixin"]

logger = logging.getLogger(__name__)


class LiteStartupMixin:
    """Make the first editor ready before optional startup services begin."""

    app_name: str
    shutting_down: bool
    features: Any

    def _init_startup_timing(self) -> None:
        self._startup_started_at = time.perf_counter()
        self._startup_phase_at = self._startup_started_at

    def _startup_phase(self, phase: str) -> None:
        """Bounded timing for startup diagnosis; never records document data."""
        now = time.perf_counter()
        logger.info(
            "QUILL Lite startup: %s in %.1f ms (total %.1f ms)",
            phase,
            (now - self._startup_phase_at) * 1000,
            (now - self._startup_started_at) * 1000,
        )
        self._startup_phase_at = now

    def _finish_startup(self) -> None:
        """Start optional services after the first editor window can respond."""
        if self.shutting_down:
            return
        self._load_optional_stores()  # type: ignore[attr-defined]
        try:
            from quill.core.sound_events import SoundEvent
            from quill.ui.companion_cues import init_app_sound, post_cue

            init_app_sound(app_id="quilllite", app_name=self.app_name)
            post_cue(SoundEvent.APP_STARTED)
        except Exception:  # noqa: BLE001 - sound is never a startup dependency
            logger.warning("Could not finish QUILL Lite sound startup", exc_info=True)
        from quill.apps.lite_updates import check_at_launch
        from quill.core.net import configure_ssl_trust

        configure_ssl_trust()
        check_at_launch(self)
        self._start_sr_watchdog()  # type: ignore[attr-defined]
        self._start_family_prompt_migration()  # type: ignore[attr-defined]
        self._startup_phase("optional services ready")
        import wx

        wx.CallLater(5000, self._resume_scribe_queue)

    def _resume_scribe_queue(self) -> None:
        """Continue saved Scribe work only after the editor has settled."""
        if self.shutting_down or not self.feature_enabled("scribe"):  # type: ignore[attr-defined]
            return
        try:
            from quill.apps.lite_window_scribe import LiteScribeHost
            from quill.ui.scribe_controller import controller_for

            controller_for(LiteScribeHost(self)).start_if_jobs_waiting()
        except Exception:  # noqa: BLE001 - a queue never gets to take startup down
            logger.warning("Could not resume the Scribe queue at startup", exc_info=True)
