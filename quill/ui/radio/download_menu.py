"""Quill Radio's download-queue wiring: the window, and what closing means.

Two small pieces that would otherwise sit in the app shell, which is at its
GATE-11 ceiling -- and they read better together anyway, because both are about
the *edges* of the queue rather than the queue itself: how you look at it, and
what happens to it when the window goes away.

The rule both share: **the listener is told either way.** A queue that silently
keeps running when you close the window is exactly as surprising as one that
silently stops, and which of the two happens is a preference somebody set once
and will not remember at the moment it matters.
"""

from __future__ import annotations

from typing import Any

#: What the tray says with nothing outstanding.
STILL_RUNNING = "Quill Radio is still running in the system tray."


def open_queue(host: Any) -> None:
    """Show the queue, and keep it refreshed while it is open."""
    from quill.ui.radio import download_runner
    from quill.ui.radio.download_queue_dialog import DownloadQueueDialog

    dialog = DownloadQueueDialog(
        host.frame,
        queue=download_runner.queue_of(host),
        cancel=lambda item: download_runner.cancel_item(host, item),
        clear_all=lambda: download_runner.clear_all(host),
        announce=host._announce,
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
        open_preferences=getattr(host, "radio_download_preferences", None),
    )
    # Held while it is open so the runner can refresh it as transfers move on;
    # cleared afterwards so a finished transfer never calls into a dead window.
    host._download_monitor = dialog
    try:
        dialog.show()
    finally:
        host._download_monitor = None


def tray_message(host: Any) -> str:
    """What to say when the window hides, including any download still going."""
    from quill.ui.radio import download_runner

    outstanding = download_runner.on_window_closing(host)
    return f"{STILL_RUNNING} {outstanding}".strip() if outstanding else STILL_RUNNING
