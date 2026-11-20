"""The small window a long GitHub read shows while it pages: a gauge and Cancel (GX11).

Security Overview reads every page of an organization's alert lists, which
can be hundreds of requests. This window says what is being read, pulses a
gauge, and has Cancel (Escape), which stops the read before its next page.
Nothing is spoken while it reads: the count is said once, at the end, by the
command itself (GATE-13). The window is the family's progress window
(:class:`quill.ui.ai_transcribe_dialog.AIProgressDialog`), not a new one.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["PagingWindow"]


class PagingWindow:
    """A gauge and Cancel while a read pages; :meth:`finish` closes it from any thread."""

    def __init__(self, frame: Any, title: str, cancel: Callable[[], None]) -> None:
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        self._window = AIProgressDialog(
            frame.frame,
            title,
            f"Reading every page for {title}. Cancel stops it.",
            on_cancel=cancel,
        )
        self._window.show()

    def quietly(self, rows: int) -> None:
        """The count so far, on the window only: never spoken (any thread)."""
        self._window.set_progress(-1, f"Read {rows} so far. Cancel stops it.")

    def finish(self) -> None:
        """Close the window (any thread); already closed by its own close box is fine."""
        self._window._wx.CallAfter(self._close)

    def _close(self) -> None:
        try:
            self._window.dialog.Destroy()
        except RuntimeError:  # closed already: wx has deleted it
            pass
