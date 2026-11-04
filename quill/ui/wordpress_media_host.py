"""What the two WordPress host adapters need for media: a clipboard picture, and the AI.

Each editor's adapter (``QuillWordPressHost``, ``LiteWordPressHost``) answers
``clipboard_image_png`` and ``ai_describe_image`` by calling these, so the
wx and the AI plumbing live once and the shared commands stay wx-free in what
they ask for (wordpress.md 6.2, 6.8, 10).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def read_clipboard_png() -> bytes | None:
    """The picture on the clipboard as PNG bytes, or None when there is none."""
    import io

    import wx

    if not wx.TheClipboard.Open():
        return None
    try:
        if not wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
            return None
        data = wx.BitmapDataObject()
        if not wx.TheClipboard.GetData(data):
            return None
        bitmap = data.GetBitmap()
    finally:
        wx.TheClipboard.Close()
    if not bitmap.IsOk():
        return None
    stream = io.BytesIO()
    if not bitmap.ConvertToImage().SaveFile(stream, wx.BITMAP_TYPE_PNG):
        return None
    return stream.getvalue()


def ask_editor_ai(
    ai: Any,
    path: Path,
    question: str,
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
) -> bool:
    """Ask the editor's chosen AI about the picture at *path* (Ask About an Image's route).

    *ai* is the editor object that carries ``HostedAiMixin`` (QUILL's main
    frame, a QUILL Lite window). The same gates as Ask About an Image apply, in
    the same order: the AI area is on, the connection in use can see pictures,
    and the first picture on that connection has the person's agreement. Each
    gate that stops says why itself; False means nothing was sent.
    """
    switched_on = getattr(ai, "_ai_switched_on", None)
    capable = getattr(ai, "_ai_capable", None)
    service_of = getattr(ai, "_ai_service", None)
    if not callable(switched_on) or not callable(capable) or not callable(service_of):
        on_error("AI help is not available in this window.")
        return False
    if not switched_on() or not capable("pictures"):
        return False
    service = service_of()
    connection = str(getattr(service, "connection_in_use", "") or "")
    if connection:
        from quill.ui.hosted_ai_picture_consent import ask_picture_consent

        if not ask_picture_consent(ai, connection):
            return False
    service.describe_image(
        path, question, on_done=on_done, on_error=on_error, requires=("text", "pictures")
    )
    return True
