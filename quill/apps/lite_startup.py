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

    @staticmethod
    def _record_lite_running_build() -> None:
        from quill.core.data_format_ledger import record_running_build
        from quill.core.lite import APP_VERSION

        record_running_build("quilllite", APP_VERSION)

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
        from quill.ui.startup_launch import run_product_startup_tasks

        run_product_startup_tasks(
            "quilllite",
            (
                ("print settings", self._ensure_print_settings),
                ("optional stores", self._load_optional_stores),  # type: ignore[attr-defined]
                ("application sounds", self._start_lite_sounds),
                ("TLS trust setup", self._configure_lite_tls),
                ("update check", self._check_lite_updates),
                ("screen-reader watchdog", self._start_sr_watchdog),  # type: ignore[attr-defined]
                (
                    "family prompt migration",
                    self._start_family_prompt_migration,  # type: ignore[attr-defined]
                ),
            ),
            on_failure=self._report_lite_startup_failure,
        )
        self._startup_phase("optional services ready")
        import wx

        wx.CallLater(1000, self._resume_transcription_queue)
        wx.CallLater(5000, self._resume_scribe_queue)

    def _ensure_print_settings(self) -> Any:
        """Build print state lazily; Print remains available on its first use."""
        current = getattr(self, "print_settings", None)
        if current is None:
            from quill.apps.lite_printing import PrintSettings

            current = PrintSettings(getattr(self, "settings", None))
            self.print_settings = current
        return current

    def _start_lite_sounds(self) -> None:
        from quill.core.sound_events import SoundEvent
        from quill.ui.companion_cues import init_app_sound, post_cue

        init_app_sound(app_id="quilllite", app_name=self.app_name)
        post_cue(SoundEvent.APP_STARTED)

    @staticmethod
    def _configure_lite_tls() -> None:
        from quill.ui.startup_launch import ensure_ssl_trust

        ensure_ssl_trust()

    def _check_lite_updates(self) -> None:
        from quill.ui.startup_launch import ensure_ssl_trust

        ensure_ssl_trust()
        from quill.apps.lite_updates import check_at_launch

        check_at_launch(self)

    @staticmethod
    def _report_lite_startup_failure(label: str) -> None:
        logger.warning("QUILL Lite startup task failed: %s", label, exc_info=True)

    def _resume_transcription_queue(self) -> None:
        """Continue durable local recording work after the editor is ready."""
        if self.shutting_down or not self.feature_enabled("dictation"):  # type: ignore[attr-defined]
            return
        try:
            from quill.ui import transcription_queue_runtime

            transcription_queue_runtime.resume(self)
        except Exception:  # noqa: BLE001 - a queue never gets to take startup down
            logger.warning("Could not resume the transcription queue at startup", exc_info=True)

    def _resume_scribe_queue(self) -> None:
        """Continue saved Scribe work only after the editor has settled."""
        if self.shutting_down or not self.feature_enabled("scribe"):  # type: ignore[attr-defined]
            return
        try:
            # The app's one controller, the same one every window's Scribe
            # commands use: a throwaway host here made a second controller
            # (and service) for the same queue, keyed by an id() that could
            # later be reused.
            from quill.apps.lite_window_scribe import lite_controller

            lite_controller(self).start_if_jobs_waiting()
        except Exception:  # noqa: BLE001 - a queue never gets to take startup down
            logger.warning("Could not resume the Scribe queue at startup", exc_info=True)
