"""The wx half of opening from the clipboard and by drag and drop (2026-10-04).

Both editors use these two pieces, so a file copied in File Explorer, a path
copied as text, a link, or a file dragged onto the window opens the same way
in QUILL and in QUILL Lite. The decisions -- what counts as a path, what a link
is, what to say -- are wx-free in :mod:`quill.core.open_sources`; this module
only reads the clipboard and receives the drop.

**A text drop still inserts text.** A plain ``wx.FileDropTarget`` on the editor
would replace the control's own drop handling and refuse dragged text, so the
editor gets a composite target that opens files and inserts text at the point
it was dropped, through the editor's ordinary edit (so Ctrl+Z undoes it).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import wx

from quill.core.open_sources import ClipboardOpen, classify_clipboard

__all__ = ["EditorDropTarget", "FrameFileDropTarget", "install_file_drop", "read_clipboard"]


def read_clipboard() -> ClipboardOpen:
    """What the clipboard holds that can be opened (see ``classify_clipboard``)."""
    files: list[str] = []
    text: str | None = None
    clipboard = wx.TheClipboard
    if not clipboard.Open():
        return classify_clipboard([], None)
    try:
        if clipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
            file_data = wx.FileDataObject()
            if clipboard.GetData(file_data):
                files = [str(name) for name in file_data.GetFilenames()]
        if not files and clipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
            text_data = wx.TextDataObject()
            if clipboard.GetData(text_data):
                text = str(text_data.GetText())
    finally:
        clipboard.Close()
    return classify_clipboard(files, text)


class FrameFileDropTarget(wx.FileDropTarget):
    """Files dropped anywhere on the window outside the editor."""

    def __init__(self, on_files: Callable[[Sequence[str]], None]) -> None:
        super().__init__()
        self._on_files = on_files

    def OnDropFiles(self, _x: int, _y: int, filenames: Sequence[str]) -> bool:  # noqa: N802 - wx API
        wx.CallAfter(self._on_files, [str(name) for name in filenames])
        return True


class EditorDropTarget(wx.DropTarget):
    """Files dropped on the editor open; text dropped on it is inserted."""

    def __init__(self, control: Any, on_files: Callable[[Sequence[str]], None]) -> None:
        super().__init__()
        self._control = control
        self._on_files = on_files
        self._files = wx.FileDataObject()
        self._text = wx.TextDataObject()
        self._composite = wx.DataObjectComposite()
        self._composite.Add(self._files, True)
        self._composite.Add(self._text)
        self.SetDataObject(self._composite)

    def OnDragOver(self, x: int, y: int, default: int) -> int:  # noqa: N802 - wx API
        return int(default)

    def OnData(self, x: int, y: int, default: int) -> int:  # noqa: N802 - wx API
        if not self.GetData():
            return int(wx.DragNone)
        received = self._composite.GetReceivedFormat()
        if received.GetType() == wx.DF_FILENAME:
            names = [str(name) for name in self._files.GetFilenames()]
            wx.CallAfter(self._on_files, names)
            return int(wx.DragCopy)
        self._insert_text(x, y, str(self._text.GetText()))
        return int(default)

    def _insert_text(self, x: int, y: int, text: str) -> None:
        if not text:
            return
        control = self._control
        try:
            result, position = control.HitTestPos(wx.Point(x, y))
            if result != wx.TE_HT_UNKNOWN and position >= 0:
                control.SetInsertionPoint(position)
        except (AttributeError, RuntimeError, TypeError):
            pass
        control.WriteText(text)


def install_file_drop(frame: Any, control: Any, on_files: Callable[[Sequence[str]], None]) -> None:
    """Accept dropped files on *frame* and on its editor *control*.

    A control that cannot place a caret from a point (no ``HitTestPos``) keeps
    its own drop handling; the frame around it still opens files.
    """
    try:
        frame.SetDropTarget(FrameFileDropTarget(on_files))
    except (AttributeError, RuntimeError):
        pass
    if control is not None and hasattr(control, "HitTestPos") and hasattr(control, "WriteText"):
        try:
            control.SetDropTarget(EditorDropTarget(control, on_files))
        except (AttributeError, RuntimeError):
            pass
