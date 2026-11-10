"""Group By in the Workbench window: the list's groups as tree nodes (GitHub PRD 17.4).

Split out of :mod:`quill.ui.workbench_frame` (GATE-11). A screen reader reads
group nodes in a tree far better than group rows inside a list, so View >
Group By puts "Issues > by Milestone > 2027.1 (12)" in the tree: the provider
hands :meth:`WorkbenchGroupsMixin.show_groups` its groups, each becomes a
child of the list's node, and selecting one shows its rows without loading
anything. Moving to another node takes the groups away.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = ["GroupRef", "WorkbenchGroupsMixin"]


@dataclass(frozen=True)
class GroupRef:
    """A Group By node: one group of the list under *parent* (a ``NodeRef``), by name."""

    parent: Any
    name: str


class WorkbenchGroupsMixin:
    """Group nodes for :class:`~quill.ui.workbench_frame.WorkbenchFrame`."""

    tree: Any
    list: Any
    status: Any
    provider: Any
    current: Any
    rows: list[object]
    _items: dict[Any, Any]
    _columns: tuple[str, ...]
    _groups: dict[GroupRef, tuple[Any, list[object]]]

    def show_groups(self, groups: Sequence[tuple[str, list[object]]]) -> None:
        """Put the list's groups in the tree under the current node; [] removes them."""
        for _ref, (item, _rows) in list(self._groups.items()):
            if item.IsOk():
                self.tree.Delete(item)
        self._groups.clear()
        if self.current is None:
            return
        parent = self._items.get(self.current)
        if parent is None:
            return
        for name, rows in groups:
            ref = GroupRef(self.current, name)
            item = self.tree.AppendItem(parent, name)
            self.tree.SetItemData(item, ref)
            self._groups[ref] = (item, list(rows))

    def _show_group(self, ref: GroupRef) -> None:
        _item, rows = self._groups.get(ref, (None, []))
        self.rows = list(rows)
        columns = self._columns or ("name",)
        self.list.DeleteAllItems()
        for index, row in enumerate(self.rows):
            cells = self.provider.cells(row, columns)
            self.list.InsertItem(index, cells[0] if cells else "")
            for column, text in enumerate(cells[1:], start=1):
                self.list.SetItem(index, column, text)
        if self.rows:
            self.list.Select(0)
            self.list.Focus(0)
        self.status.refresh()
