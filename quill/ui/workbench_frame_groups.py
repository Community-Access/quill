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

from quill.core.counted import plural

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
    _shown_cells: list[list[str]]
    _wx: Any
    selected_indices: Any

    # -- counts after node names (GitHub PRD 3.3 and 9, GH-R-010) -----------------

    def _count_store(self) -> tuple[dict[Any, str], dict[Any, str]]:
        """(count words by node, plain label by node), made on first use."""
        if not hasattr(self, "_node_counts"):
            self._node_counts: dict[Any, str] = {}
            self._node_labels: dict[Any, str] = {}
        return self._node_counts, self._node_labels

    def counted_label(self, ref: Any, label: str) -> str:
        """*label* with the node's count after it, once it has one: "Issues (12)"."""
        counts, labels = self._count_store()
        labels[ref] = label
        words = counts.get(ref, "")
        return f"{label} ({words})" if words else label

    def remember_count(self, count: int) -> None:
        """Keep the count of the list just loaded; it reaches the tree when you leave."""
        ref = self.current
        if ref is None:
            return
        node = self.node(ref)  # type: ignore[attr-defined]
        if not node.loader or self.provider.remote_words(node):
            return  # a search's rows depend on what was typed, so it has no count of its own
        hook = getattr(self.provider, "count_words", None)
        words = str(hook(ref, count)) if callable(hook) else str(count)
        self._count_store()[0][ref] = words

    def write_count(self, ref: Any) -> None:
        """Put *ref*'s count after its name, as it is left, so no reader announces it."""
        counts, labels = self._count_store()
        item = self._items.get(ref)
        if ref not in counts or ref not in labels or item is None:
            return
        try:
            text = f"{labels[ref]} ({counts[ref]})"
            if self.tree.GetItemText(item) != text:
                self.tree.SetItemText(item, text)
        except Exception:  # noqa: BLE001 - a stale item after a rebuild; the next build counts
            return

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
        self._shown_cells = []  # the next fill of the node's own list is a real one
        if self.rows:
            self.focus_row(0)
        self.status.refresh()

    def focus_row(self, index: int) -> None:
        """Select *index* alone and focus it in ONE state change, and show it.

        ``Select`` then ``Focus`` is two changes, and JAWS read the row once for
        each; one ``SetItemState`` with both states is read once.
        """
        wx = self._wx
        for other in self.selected_indices():
            if other != index:
                self.list.Select(other, False)
        both = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
        self.list.SetItemState(index, both, both)
        self.list.EnsureVisible(index)

    # -- the tree and the list, kept as they were (items 26 and 30) ----------------

    def rebuild_tree(self) -> None:
        """Build the tree again after an instance was added; selection and openings kept.

        Discovery rebuilds the tree, and a rebuild that closed every branch you had
        opened would undo your place (review item 30), so what was expanded is
        expanded again.
        """
        current = self.current
        tree = self.tree
        opened = [ref for ref, item in self._items.items() if item.IsOk() and tree.IsExpanded(item)]
        self._navigating = self._rebuilding = True
        try:
            self._build_tree()
            for ref in opened:
                item = self._items.get(ref)
                if item is not None:
                    tree.Expand(item)
        finally:
            self._navigating = self._rebuilding = False
        if current is not None and current in self._items:
            self.select(current, remember=False)

    def loaded_words(self) -> str:
        """How a reported load ended: the count and any limit, or why it is empty."""
        if not self.rows:
            return self.empty_words() or "No rows here."
        said = f"{plural(len(self.rows), 'row')} shown."
        cut = getattr(self.provider, "cut_for", None)
        more = str(cut(self.current) or "") if callable(cut) and self.current is not None else ""
        return f"{said} {more}".strip()
