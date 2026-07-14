"""MSAA accessibility for the Table Studio grid (Windows; ported from prototype).

A row-indexed ``wx.Accessible`` attached to the virtual ``wx.ListCtrl``: each
row child reports the *active column's* cell as its name, so Up/Down (native
SysListView32 focus events) reads the active column in the new row, and
Left/Right (our synthetic focus events via :func:`fire_focus_child`) re-reads the
row with the new column. This is what lets NVDA and JAWS speak the column as you
arrow across a row.

The child-id scheme (``childId = display_row + 1``) matches SysListView32's own,
so the native row events and our column-move events resolve through the same
simple elements and never fight. All data is pulled live through callbacks; this
module never imports the model or copies data. When wxUSE_ACCESSIBILITY is
absent, attach returns ``None`` and the UI falls back to spoken announcements.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

#: Provider callbacks the accessible reads live: row_count, col_count, caption
#: (all () -> value), active () -> (display_row, col), describe(display_row, col)
#: -> str | None, cell_rect(display_row, col) -> wx.Rect | None.
Providers = dict[str, Callable[..., Any]]


class ListGridAccessible(wx.Accessible):
    """Row-indexed MSAA exposure for the virtual table list control."""

    def __init__(self, window: wx.Window, providers: Providers) -> None:
        super().__init__(window)
        self._p = providers

    def _active_display_row(self) -> int:
        di, _col = self._p["active"]()
        return di if di >= 0 else 0

    def GetChildCount(self) -> tuple[int, int]:
        return (wx.ACC_OK, self._p["row_count"]())

    def GetChild(self, child_id: int) -> tuple[int, Any]:
        # Every child is a simple element: readers query name/role/state on us.
        return (wx.ACC_OK, None)

    def GetName(self, child_id: int) -> tuple[int, str]:
        if child_id == 0:
            cap = self._p["caption"]()
            return (
                wx.ACC_OK,
                f"{cap}. {self._p['row_count']()} rows, {self._p['col_count']()} columns.",
            )
        _di, col = self._p["active"]()
        text = self._p["describe"](child_id - 1, col)
        return (wx.ACC_OK, text) if text is not None else (wx.ACC_FAIL, "")

    def GetRole(self, child_id: int) -> tuple[int, int]:
        if child_id == 0:
            return (wx.ACC_OK, wx.ROLE_SYSTEM_TABLE)
        return (wx.ACC_OK, wx.ROLE_SYSTEM_CELL)

    def GetState(self, child_id: int) -> tuple[int, int]:
        if child_id == 0:
            return (wx.ACC_OK, wx.ACC_STATE_SYSTEM_DEFAULT)
        states = wx.ACC_STATE_SYSTEM_SELECTABLE | wx.ACC_STATE_SYSTEM_FOCUSABLE
        if child_id - 1 == self._active_display_row():
            states |= wx.ACC_STATE_SYSTEM_FOCUSED | wx.ACC_STATE_SYSTEM_SELECTED
        return (wx.ACC_OK, states)

    def GetValue(self, child_id: int) -> tuple[int, str]:
        if child_id == 0:
            return (wx.ACC_NOT_IMPLEMENTED, "")
        _di, col = self._p["active"]()
        text = self._p["describe"](child_id - 1, col)
        return (wx.ACC_OK, text or "Blank")

    def GetFocus(self) -> tuple[int, int, Any]:
        return (wx.ACC_OK, self._active_display_row() + 1, None)

    def GetSelections(self) -> tuple[int, int]:
        return (wx.ACC_OK, self._active_display_row() + 1)

    def GetLocation(self, element_id: int) -> tuple[int, wx.Rect]:
        # A real on-screen rectangle is required: readers drop focus events for
        # elements they consider zero-size or off-screen.
        if element_id == 0:
            return (wx.ACC_NOT_IMPLEMENTED, wx.Rect())
        _di, col = self._p["active"]()
        rect = self._p["cell_rect"](element_id - 1, col)
        if rect is None:
            return (wx.ACC_NOT_IMPLEMENTED, wx.Rect())
        return (wx.ACC_OK, rect)


def attach_list_accessibility(
    list_ctrl: wx.Window, providers: Providers
) -> ListGridAccessible | None:
    """Install the row-based MSAA provider, or ``None`` if unavailable."""
    try:
        acc = ListGridAccessible(list_ctrl, providers)
        list_ctrl.SetAccessible(acc)
        return acc
    except Exception:  # noqa: BLE001 - depends on wx build flags; degrade to announce-only
        return None


def fire_focus_child(acc: wx.Accessible | None, child_id: int) -> None:
    """Raise EVENT_OBJECT_FOCUS for a row child so readers re-query the cell."""
    if acc is None:
        return
    try:
        acc.NotifyEvent(wx.ACC_EVENT_OBJECT_FOCUS, acc.GetWindow(), wx.OBJID_CLIENT, child_id)
    except Exception:  # noqa: BLE001 - a missed focus event must never crash navigation
        pass


__all__ = ["ListGridAccessible", "attach_list_accessibility", "fire_focus_child"]
