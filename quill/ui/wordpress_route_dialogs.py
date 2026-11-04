"""The standard file boxes the 9.16 commands use (wordpress.md 9.16).

Windows' own Open, Save As and Browse for Folder boxes, as they are: a screen
reader already knows them. Each runs through the host's modal path like every
other WordPress window. Everything else the commands ask goes through
:mod:`quill.ui.wordpress_dialogs`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

ShowModal = Callable[[Any, str], int]

LARGE_FILE_WILDCARD = (
    "Audio and video (*.mp3;*.m4a;*.wav;*.ogg;*.mp4;*.m4v;*.mov;*.webm)"
    "|*.mp3;*.m4a;*.wav;*.ogg;*.mp4;*.m4v;*.mov;*.webm|All files (*.*)|*.*"
)


def pick_folder(
    parent: Any, show_modal: ShowModal, *, title: str, must_exist: bool = True
) -> Path | None:
    import wx

    style = wx.DD_DEFAULT_STYLE | (wx.DD_DIR_MUST_EXIST if must_exist else 0)
    with wx.DirDialog(parent, title, style=style) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return None
        return Path(picker.GetPath())


def pick_file(parent: Any, show_modal: ShowModal, *, title: str, wildcard: str) -> Path | None:
    import wx

    with wx.FileDialog(
        parent, title, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return None
        return Path(picker.GetPath())


def save_as(
    parent: Any, show_modal: ShowModal, *, title: str, name: str, wildcard: str
) -> Path | None:
    import wx

    with wx.FileDialog(
        parent,
        title,
        defaultFile=name,
        wildcard=wildcard,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return None
        return Path(picker.GetPath())
