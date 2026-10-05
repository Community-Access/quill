"""Cast's Transcript reader, as a peer window (qc.md section 6, Phase 4).

Read-along wants to sit beside the library while the episode plays, so in Cast
the transcript is a window rather than a dialog. The reader itself is the
shared :class:`~quill.ui.transcript_reader.TranscriptReader` -- Find, Play from
Here, Links, Copy, Save As and Open in QUILL are exactly Quill Radio's -- built
into a panel instead of a dialog. Radio keeps its modal transcript.

Made once: asked for again, for this episode or another, the one window is
raised with the transcript asked about. Escape, Ctrl+W or Close hide it and
return focus to whatever opened it.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.transcript_reader import TranscriptReader

__all__ = ["TITLE", "TranscriptWindow", "open_transcript_window"]

TITLE = "Transcript"


class _PeerReader(TranscriptReader):
    """The shared reader in a panel, with a Close that closes a frame."""

    def __init__(self, frame: Any, **kwargs: Any) -> None:
        super().__init__(frame, **kwargs)
        close_btn = self._close_btn
        # No access key on Close: Escape already serves it (GATE-14's first rule).
        close_btn.SetLabel("Close")
        close_btn.SetHelpText("Closes the transcript and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(frame, close_btn, modeless=True)

    def _peer_panel(self, parent: Any) -> Any:
        return wx.Panel(parent, style=wx.TAB_TRAVERSAL)


class TranscriptWindow:
    """The frame; the reader inside it is rebuilt for each transcript."""

    TITLE = TITLE
    MENU_TITLE = "Transc&ript"

    def __init__(self, parent: Any, **content: Any) -> None:
        self.reader: _PeerReader | None = None
        self.frame = wx.Frame(parent, title="Transcript", size=(1000, 760))
        self.frame.SetMinSize((640, 520))
        self.frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.load(**content)
        self.frame.CentreOnParent()

    def load(self, **content: Any) -> None:
        """Show a transcript: the first, or the next one asked about."""
        sizer = self.frame.GetSizer()
        if self.reader is not None:
            sizer.Clear(delete_windows=True)
        self.reader = _PeerReader(self.frame, **content)
        self.frame.SetTitle(f"Transcript: {content.get('title', '')}")
        sizer.Add(self.reader.dialog, 1, wx.EXPAND)
        self.frame.Layout()

    def focus_target(self) -> Any:
        return self.reader._text if self.reader is not None else None


def open_transcript_window(host: Any, parent: Any, **content: Any) -> TranscriptWindow:
    """Open, or raise, the host's one Transcript window, on *content*."""
    from quill.ui.podcasts.peer_window import open_peer

    existing = getattr(host, "_transcript_window", None)
    if existing is not None and existing.frame:
        existing.load(**content)
    window: TranscriptWindow = open_peer(
        host, "_transcript_window", lambda _owner: TranscriptWindow(parent, **content)
    )
    return window
