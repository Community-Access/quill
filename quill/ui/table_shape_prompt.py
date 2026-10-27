"""Insert > Table: ask how many columns and rows, and whether the first is a header.

QUILL's prompt, moved here from ``main_frame.py`` when QUILL Lite gained Insert
Table (2026-10-25), so both editors ask the same three questions the same way
rather than keeping two copies that drift. Each editor passes its own hardened
modal path and message box, which is all that differs between them.

Three plain questions rather than one form, on purpose: a number typed into a
box that names its own range is the fastest thing there is with a screen reader,
and a wrong number is answered with what the range is, then asked again.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["MAX_COLUMNS", "MAX_ROWS", "prompt_table_shape"]

MAX_COLUMNS = 12
MAX_ROWS = 50
_TITLE = "Insert Table"


def prompt_table_shape(
    parent: Any,
    show_modal: Callable[[Any, str], int],
    show_message: Callable[[str, str, int], object],
    *,
    wx_module: Any = None,
) -> tuple[int, int, bool] | None:
    """``(rows, columns, include_header)``, or None when any question is cancelled.

    *show_modal* is the editor's modal path (``dialog, label -> id``) and
    *show_message* its message box (``message, title, style``). *wx_module* is
    QUILL's injected ``self._wx``, so its tests can answer the dialogs.
    """
    if wx_module is None:
        import wx as wx_module
    wx = wx_module

    def prompt_dimension(label: str, maximum: int) -> int | None:
        while True:
            with wx.TextEntryDialog(
                parent, f"Enter number of {label.lower()} (1-{maximum}):", _TITLE, value="2"
            ) as dialog:
                if show_modal(dialog, _TITLE) != wx.ID_OK:
                    return None
                raw_value = dialog.GetValue().strip()
            try:
                value = int(raw_value)
            except ValueError:
                show_message(
                    "Rows and columns must be whole numbers.", _TITLE, wx.ICON_ERROR | wx.OK
                )
                continue
            if not 1 <= value <= maximum:
                show_message(
                    f"{label} must be between 1 and {maximum}.", _TITLE, wx.ICON_ERROR | wx.OK
                )
                continue
            return value

    columns = prompt_dimension("Columns", MAX_COLUMNS)
    if columns is None:
        return None
    rows = prompt_dimension("Rows", MAX_ROWS)
    if rows is None:
        return None
    with wx.MessageDialog(
        parent, "Include a header row?", _TITLE, wx.YES_NO | wx.ICON_QUESTION
    ) as header_dialog:
        include_header = show_modal(header_dialog, _TITLE) == wx.ID_YES
    return rows, columns, include_header
