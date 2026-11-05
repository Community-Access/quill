"""The one window the listening commands add: choosing a file on this computer.

Everything else they ask goes through :mod:`quill.ui.wordpress_dialogs`. The
standard Open box is used as it is -- a screen reader already knows it -- and it
runs through the host's modal path like every other WordPress window.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

DOCUMENT_WILDCARD = (
    "PDF and Word documents (*.pdf;*.docx;*.doc;*.rtf;*.odt)|*.pdf;*.docx;*.doc;*.rtf;*.odt"
    "|All files (*.*)|*.*"
)


def pick_file(
    parent: Any, show_modal: Callable[[Any, str], int], *, title: str, wildcard: str
) -> Path | None:
    import wx

    with wx.FileDialog(
        parent, title, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return None
        return Path(picker.GetPath())


def pick_files(
    parent: Any,
    show_modal: Callable[[Any, str], int],
    *,
    title: str,
    wildcard: str,
    folder: Path | None = None,
) -> list[Path]:
    """One or more files, starting in *folder* when it exists."""
    import wx

    with wx.FileDialog(
        parent,
        title,
        defaultDir=str(folder) if folder is not None and folder.is_dir() else "",
        wildcard=wildcard,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return []
        return [Path(p) for p in picker.GetPaths()]
