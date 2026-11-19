"""Lists that stay still (FUX-06): a refill keeps the reader's row where it was.

A feed refresh, a finished download or a queue change made somewhere else
refills a list the listener may be standing in. Three things went wrong when
that refill was written as "clear the list, fill it, select row N again":

* **The row moved under the reader.** New episodes arrive above the one they
  were on, so the same index is now somebody else's episode -- and the next
  Delete or Enter acts on it.
* **The view jumped.** Clearing a list scrolls it to the top; selecting the row
  again scrolls only as far as needed to show it, so the row they were looking
  at lands on the bottom line, or the top one, rather than where it was.
* **Focus went somewhere.** A refill that ends in ``SetFocus`` takes the
  listener out of whatever they were doing in another control.

This module is the second half of the answer. The caller finds the row by
*identity* (a show id and an episode guid, never an index) and hands the new
index here; these put the selection, the focused item and the scroll position
back without touching keyboard focus. They never speak: the screen reader
already says a selection change (GATE-13), and nothing about the row changed.

Two controls, because Cast uses both: the report list (``wx.ListCtrl``, the
main window's content) and the extended list box (``wx.ListBox``, the Play
Queue window).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "RowAnchor",
    "capture_report",
    "capture_listbox",
    "restore_report",
    "restore_listbox",
    "kept_top",
]

#: ``LB_SETCARETINDEX``: the list box row the reader is on. wx sets it as a side
#: effect of ``SetSelection`` but offers no way to set it alone.
_LB_SETCARETINDEX = 0x019E


@dataclass(frozen=True)
class RowAnchor:
    """Where the reader was before a refill: their row, and the first row on screen."""

    index: int = -1
    top: int = -1
    visible: bool = False


NO_ANCHOR = RowAnchor()


def kept_top(anchor: RowAnchor, new_index: int, count: int) -> int:
    """The first row to show so *new_index* sits where ``anchor.index`` sat.

    Rows inserted above the reader push their row down; moving the view down by
    the same amount keeps it on the same line of the screen. Clamped to the
    list, because a list that shrank cannot scroll past its end.
    """
    if anchor.index < 0 or anchor.top < 0 or count <= 0:
        return -1
    return max(0, min(count - 1, anchor.top + (new_index - anchor.index)))


def _visible(top: int, per_page: int, index: int) -> bool:
    return per_page <= 0 or top <= index < top + per_page


# -- the report list ------------------------------------------------------------ #


def capture_report(control: Any) -> RowAnchor:
    """The selected row and the first visible row of a ``wx.ListCtrl``."""
    try:
        index = int(control.GetFirstSelected())
        top = int(control.GetTopItem())
        per_page = int(control.GetCountPerPage())
    except RuntimeError:  # the list is mid-teardown
        return NO_ANCHOR
    if index < 0:
        return NO_ANCHOR
    return RowAnchor(index=index, top=top, visible=_visible(top, per_page, index))


def restore_report(wx: Any, control: Any, anchor: RowAnchor, index: int) -> None:
    """Select and focus exactly *index*, keeping it on the line it was on.

    Only what differs is written: re-selecting the row already selected would
    make the native list raise a selection event for a row that did not change.
    Never calls ``SetFocus`` -- the focused *item* is a list's own state, the
    focused *window* is the listener's.
    """
    count = int(control.GetItemCount())
    if not 0 <= index < count:
        return
    selected = int(control.GetFirstSelected())
    while selected != -1:
        following = int(control.GetNextSelected(selected))
        if selected != index:
            control.Select(selected, on=False)
        selected = following
    focused = wx.LIST_STATE_FOCUSED
    state = int(control.GetItemState(index, wx.LIST_STATE_SELECTED | focused))
    if not state & wx.LIST_STATE_SELECTED:
        control.Select(index)
    if not state & focused:
        # SetItemState rather than Focus(): wxPython's Focus also scrolls.
        control.SetItemState(index, focused, focused)
    top = kept_top(anchor, index, count)
    if top < 0:
        control.EnsureVisible(index)
        return
    _scroll_report_to(control, top)
    per_page = int(control.GetCountPerPage())
    if anchor.visible and not _visible(int(control.GetTopItem()), per_page, index):
        control.EnsureVisible(index)


def _scroll_report_to(control: Any, top: int) -> None:
    current = int(control.GetTopItem())
    if current == top:
        return
    try:
        height = int(control.GetItemRect(current).height)
    except Exception:  # noqa: BLE001 - no row to measure: nothing to scroll
        height = 0
    if height > 0:
        control.ScrollList(0, (top - current) * height)


# -- the list box ------------------------------------------------------------------ #


def capture_listbox(control: Any) -> RowAnchor:
    """The caret row (the topmost selected) and the first visible row of a ``wx.ListBox``."""
    try:
        selections = list(control.GetSelections())
        top = int(control.GetTopItem())
        per_page = int(control.GetCountPerPage()) if hasattr(control, "GetCountPerPage") else 0
    except RuntimeError:
        return NO_ANCHOR
    if not selections:
        return NO_ANCHOR
    index = min(selections)
    return RowAnchor(index=index, top=top, visible=_visible(top, per_page, index))


def restore_listbox(control: Any, anchor: RowAnchor, rows: Sequence[int], caret: int) -> None:
    """Select exactly *rows*, put the caret on *caret*, and keep it on its line."""
    count = int(control.GetCount())
    wanted = [row for row in rows if 0 <= row < count]
    for row in list(control.GetSelections()):
        if row not in wanted:
            control.Deselect(row)
    for row in wanted:
        if not control.IsSelected(row):
            control.SetSelection(row)
    if 0 <= caret < count:
        _set_listbox_caret(control, caret)
        top = kept_top(anchor, caret, count)
        if top >= 0 and int(control.GetTopItem()) != top:
            control.SetFirstItem(top)


def _set_listbox_caret(control: Any, row: int) -> None:
    import sys

    if sys.platform != "win32":
        return
    try:
        import ctypes

        handle = int(control.GetHandle())
        ctypes.windll.user32.SendMessageW(handle, _LB_SETCARETINDEX, row, 0)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - the caret is a courtesy; selection already holds
        return
