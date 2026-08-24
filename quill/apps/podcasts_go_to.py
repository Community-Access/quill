"""QUILL Cast's Go To: load the layout, show the popup, open the place (5.2).

The thin middle, mirroring ``quill/apps/radio_go_to.py``. The catalogue is
:mod:`quill.core.podcasts.go_to`, the machinery is
:mod:`quill.core.go_to_menu`, and the two windows are the ones Quill Radio
already had -- handed Cast's layout, they show Cast's places.

**Why Cast needed this at all.** Cast's only "Go To" was
``podcasts.go_to_position``, which jumps to a *time inside an episode*: a
different feature with the same two words. Meanwhile the Podcast Manager, the
Play Queue, Downloads, Statistics and Preferences each had their own key or no
key at all, which is the same recall problem Radio's Go To was written for --
paid by the people least able to afford hunting for a shortcut.

Never raises. A way of getting around the app must not be a way to crash it.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import go_to

__all__ = ["CastGoToMixin"]


class CastGoToMixin:
    """Ctrl+G, and the settings window behind it."""

    def open_cast_go_to(self) -> None:
        """Show the numbered list of places. Escape puts you back."""
        try:
            from quill.core.paths import app_data_dir
            from quill.ui.radio import go_to_dialog

            data_dir = app_data_dir()
            layout = go_to.load_layout(data_dir)
            chosen = go_to_dialog.open_popup(self, layout)
            if chosen == "__settings__":
                from quill.ui.radio import go_to_settings_dialog

                go_to_settings_dialog.edit(self, layout, data_dir, places=go_to)
                return
            if chosen:
                self._open_cast_destination(chosen)
        except Exception:  # noqa: BLE001 - navigation must never take the window down
            announce = getattr(self, "_announce", None)
            if callable(announce):
                announce("Go To could not open.")

    def _open_cast_destination(self, destination_id: str) -> None:
        destination = go_to.destination(destination_id)
        if destination is None:
            return
        handler = getattr(self, destination.opens, None)
        if callable(handler):
            handler()
            return
        # A destination whose door has been renamed says so rather than doing
        # nothing: a menu entry that silently no-ops is indistinguishable from
        # a broken app, and the listener has no way to tell which they have.
        announce = getattr(self, "_announce", None)
        if callable(announce):
            announce(f"{destination.title} is not available in this build.")


def unreachable_destinations(host: Any) -> list[str]:
    """Titles whose opener this *host* does not have. Empty is the healthy answer.

    Used by the tests rather than at runtime: the catalogue names host methods
    by string, which is what lets the pool grow without a migration, and is
    also what lets a rename go unnoticed until somebody presses the number.
    """
    missing: list[str] = []
    for destination in go_to.DESTINATIONS:
        if not callable(getattr(host, destination.opens, None)):
            missing.append(destination.title)
    return missing
