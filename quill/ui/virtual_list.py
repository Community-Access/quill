"""A results list whose cost does not grow with the catalogue behind it.

Reported 2026-09-15: "why is the emoji search really slow". The search was not
slow -- ``emoji_data.search`` answers in 1-2 ms across all 3,781 entries. What
was slow was *showing* the answer. The picker filled a ``wx.ListCtrl`` the
obvious way, two native calls per row::

    self._results.DeleteAllItems()
    for row, entry in enumerate(entries):
        self._results.InsertItem(row, entry.char)
        self._results.SetItem(row, 1, entry.name)

and did it on every ``EVT_TEXT``, so typing one character into the search box
cost, measured on the reporter's machine:

===================================  =====  =========
List                                  Rows  Per key
===================================  =====  =========
Emoji catalogue                       3781  1626.3 ms
Special characters                     357   154.3 ms
HTML tags                              111    51.5 ms
===================================  =====  =========

A flat ~0.43 ms per row, so it is the catalogue size that decides. Typing
``smile`` rebuilt the list five times: roughly eight seconds of frozen window
for a search that took 8 ms. ``Freeze()``/``Thaw()`` around the loop only got
it to 974 ms -- still a second per keystroke, because the cost is the
per-row native calls themselves, not the repainting.

A **virtual** list has no rows to insert. ``LC_VIRTUAL`` tells the native
control to ask for a cell's text only when it is about to draw it, so showing
3,781 results is one ``SetItemCount`` call: **1.0 ms**, and the same 1.0 ms for
40,000. The list asks for the twenty-odd rows actually on screen.

**This is not a trade against screen readers**, which is the first thing to ask
of any "draw less" optimisation. ``LC_VIRTUAL`` on wxMSW is the native
``LVS_OWNERDATA`` list -- the control Windows Explorer's own file list uses --
so MSAA/UIA exposes every row exactly as before, including the rows a reader
navigates to but the screen never painted. QUILL already ships two of these
(``table_studio.py``, ``apps/beacon/app.py``). Nothing about naming, selection,
focus or announcement changes here; only who builds the row text, and when.

The class is built per call rather than at module scope because these dialogs
import ``wx`` inside ``__init__`` (they are imported by code paths that must
not pull wx in), and building a class is microseconds against a dialog that is
about to lay out a window.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["virtual_report_list"]


def virtual_report_list(
    wx: Any,
    parent: Any,
    row_text: Callable[[int, int], str],
    *,
    style: int = 0,
) -> Any:
    """A report-mode ``wx.ListCtrl`` that pulls its cells from *row_text*.

    *row_text* is called as ``row_text(row, column)`` and returns the text for
    that cell. It is called during painting, for visible rows only, so it must
    be cheap and must never raise -- a raising callback would fire on every
    paint. Out-of-range rows answer ``""`` rather than raising, because the
    control can ask for a row between a shrink and its repaint.

    Call ``set_rows(n)`` instead of inserting; everything else (columns,
    ``SetName``, ``Select``, ``Focus``, ``GetFirstSelected``, the
    ``EVT_LIST_ITEM_*`` events and their ``GetIndex()``) behaves exactly as it
    does on an ordinary list, so index-based selection handlers need no change.
    """

    class _VirtualReportList(wx.ListCtrl):  # type: ignore[misc, name-defined]
        def __init__(self) -> None:
            super().__init__(parent, style=style | wx.LC_REPORT | wx.LC_VIRTUAL)

        def OnGetItemText(self, item: int, column: int) -> str:  # noqa: N802 - wx callback
            try:
                return row_text(item, column)
            except Exception:  # noqa: BLE001 - a paint callback never raises at the user
                return ""

        def set_rows(self, count: int) -> None:
            """Show *count* rows. Constant time, whatever *count* is."""
            self.SetItemCount(count)
            self.Refresh()

    return _VirtualReportList()
