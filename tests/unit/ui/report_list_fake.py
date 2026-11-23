"""A headless stand-in for a ``wx.ListCtrl`` report list (FUX-06 tests).

It keeps what a native list keeps -- each row's selected and focused state
travels with the row when rows are inserted or deleted around it, and every
row is a distinct *item* -- so a test can tell "the reader's row stayed the
same item" from "it was destroyed and a look-alike selected". Every change of
selection is recorded in ``events``, which is what a screen reader would hear.
"""

from __future__ import annotations

from itertools import count
from types import SimpleNamespace
from typing import Any

#: The two state bits :mod:`quill.ui.list_stay_still` reads from ``wx``.
#: ``CallLater`` runs at once and every window is in front, so a sentence held
#: back for the screen reader (``list_stay_still.say_when_settled``) is heard.
WX = SimpleNamespace(
    LIST_STATE_SELECTED=4,
    LIST_STATE_FOCUSED=2,
    CallLater=lambda _ms, fn, *args: fn(*args),
    GetTopLevelParent=lambda _control: SimpleNamespace(IsActive=lambda: True),
)

_ROW_HEIGHT = 10
_ids = count(1)


class FakeReportList:
    def __init__(self, per_page: int = 10) -> None:
        self.rows: list[dict[str, Any]] = []
        self.top = 0
        self.per_page = per_page
        self.events: list[tuple[str, int]] = []
        self.set_calls: list[tuple[int, int, str]] = []
        self.inserts: list[tuple[int, str]] = []
        self.deletes: list[int] = []
        self.selects: list[int] = []
        self.focuses: list[int] = []
        self.ensure_visible: list[int] = []
        self.delete_all = 0
        self.took_focus = False

    # -- reading ---------------------------------------------------------------

    def GetItemCount(self) -> int:  # noqa: N802 - wx shape
        return len(self.rows)

    def GetFirstSelected(self) -> int:  # noqa: N802
        return self.GetNextSelected(-1)

    def GetNextSelected(self, after: int) -> int:  # noqa: N802
        for row in range(after + 1, len(self.rows)):
            if self.rows[row]["selected"]:
                return row
        return -1

    def GetFocusedItem(self) -> int:  # noqa: N802
        return self.focused_row()

    def GetTopItem(self) -> int:  # noqa: N802
        return self.top

    def GetCountPerPage(self) -> int:  # noqa: N802
        return self.per_page

    def GetItemRect(self, _row: int) -> Any:  # noqa: N802
        return SimpleNamespace(height=_ROW_HEIGHT)

    def GetItemText(self, row: int, col: int = 0) -> str:  # noqa: N802
        cells = self.rows[row]["cells"]
        return cells[col] if col < len(cells) else ""

    def GetItemState(self, row: int, mask: int) -> int:  # noqa: N802
        state = 0
        if self.rows[row]["selected"]:
            state |= WX.LIST_STATE_SELECTED
        if self.rows[row]["focused"]:
            state |= WX.LIST_STATE_FOCUSED
        return state & mask

    def item(self, row: int) -> int:
        """The native item at *row*: the same number while the row lives."""
        return int(self.rows[row]["item"])

    def selected_rows(self) -> list[int]:
        return [row for row, data in enumerate(self.rows) if data["selected"]]

    def focused_row(self) -> int:
        return next((row for row, data in enumerate(self.rows) if data["focused"]), -1)

    def text(self, row: int) -> str:
        return self.GetItemText(row, 0)

    # -- changing ----------------------------------------------------------------

    def InsertItem(self, row: int, text: str) -> int:  # noqa: N802
        self.inserts.append((row, text))
        self.rows.insert(
            row, {"cells": [text], "selected": False, "focused": False, "item": next(_ids)}
        )
        return row

    def SetItem(self, row: int, col: int, value: str) -> None:  # noqa: N802
        self.set_calls.append((row, col, value))
        cells = self.rows[row]["cells"]
        while len(cells) <= col:
            cells.append("")
        cells[col] = value

    def DeleteItem(self, row: int) -> None:  # noqa: N802
        self.deletes.append(row)
        del self.rows[row]

    def DeleteAllItems(self) -> None:  # noqa: N802
        self.delete_all += 1
        self.rows.clear()
        self.top = 0

    def Select(self, row: int, on: bool = True) -> None:  # noqa: N802
        if on:
            self.selects.append(row)
        if self.rows[row]["selected"] != on:
            self.rows[row]["selected"] = on
            self.events.append(("selected" if on else "deselected", row))

    def SetItemState(self, row: int, state: int, mask: int) -> None:  # noqa: N802
        if mask & WX.LIST_STATE_FOCUSED and state & WX.LIST_STATE_FOCUSED:
            self.Focus(row)

    def Focus(self, row: int) -> None:  # noqa: N802
        self.focuses.append(row)
        for index, data in enumerate(self.rows):
            data["focused"] = index == row
        self.events.append(("focused", row))

    def EnsureVisible(self, row: int) -> None:  # noqa: N802
        self.ensure_visible.append(row)
        if row < self.top:
            self.top = row
        elif row >= self.top + self.per_page:
            self.top = row - self.per_page + 1

    def ScrollList(self, _dx: int, dy: int) -> None:  # noqa: N802
        self.top = max(0, min(len(self.rows) - 1, self.top + dy // _ROW_HEIGHT))

    def SetFocus(self) -> None:  # noqa: N802
        self.took_focus = True

    def fill(self, texts: list[str]) -> None:
        """Rows with these first cells, as a fresh list would have."""
        for text in texts:
            self.InsertItem(len(self.rows), text)
