"""Post-window startup services for Quill Beacon."""

from __future__ import annotations

import logging
from typing import Any


def prepare_auto_sync(frame: Any, wx: Any) -> None:
    """Create Beacon's inert auto-sync timer."""
    if getattr(frame, "_sync_timer", None) is not None:
        return
    from quill.ui.surface_lifetime import stop_timer_on_destroy

    frame._sync_timer = wx.Timer(frame)
    frame.Bind(wx.EVT_TIMER, frame._on_auto_sync_tick, frame._sync_timer)
    stop_timer_on_destroy(frame, frame._sync_timer)


def defer_services(frame: Any, wx: Any, *, version: str) -> None:
    """Queue optional Beacon integrations once its named window is visible."""
    from quill.ui.startup_launch import defer_startup_tasks

    def record_release_data_format() -> None:
        from quill.core.data_format_ledger import record_running_build

        record_running_build("beacon", version)

    def start_sounds() -> None:
        from quill.ui import app_sounds
        from quill.ui.companion_cues import init_app_sound

        init_app_sound()
        app_sounds.apply(frame)

    def report_failure(label: str) -> None:
        logging.getLogger(__name__).exception(
            "Optional Beacon startup task failed after the window was ready: %s", label
        )

    defer_startup_tasks(
        wx,
        (
            ("release data-format ledger", record_release_data_format),
            ("application sounds", start_sounds),
            ("capture bridge", frame._start_capture_bridge),
            ("system tray", frame._start_tray),
            ("auto sync", frame._setup_auto_sync),
        ),
        on_failure=report_failure,
    )
