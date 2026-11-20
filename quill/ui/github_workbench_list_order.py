"""Sort By Column and Group By Column on every Workbench list (GitHub PRD 17.4).

Split out of :mod:`quill.ui.github_workbench_view` (GATE-11). The Issues
lists keep View > Sort By and Group By, which GitHub answers; every other
list is ordered and grouped over its loaded rows by one of its own fields
(:mod:`quill.core.github.list_order`), from View > Sort By > By Column... and
View > Group By > By Column.... The choice is kept per account per list, in
the same store as Columns..., and the group nodes are the same tree nodes
Group By makes on an Issues list.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.list_order import (
    ColumnOrder,
    field_label,
    fields_for,
    group_by_field,
    group_store_key,
    order_rows,
    sort_store_key,
    text_of,
)

__all__ = ["ISSUES_LOADER", "GitHubWorkbenchListOrderMixin"]

#: The one list GitHub sorts and groups itself, through the radio rows.
ISSUES_LOADER = "items:issues"


class GitHubWorkbenchListOrderMixin:
    """Column order and column groups for the GitHub provider's other lists."""

    items: Any
    frame: Any
    _say: Callable[[str], None]

    # -- which list -------------------------------------------------------------

    def _node_now(self) -> Any:
        frame = self.frame
        if frame is None or frame.current is None:
            return None
        try:
            return frame.node(frame.current)
        except (KeyError, AttributeError):
            return None

    def issue_list_shown(self) -> bool:
        node = self._node_now()
        return node is not None and node.loader == ISSUES_LOADER

    def column_list_shown(self) -> bool:
        """A list (not the Issues lists) that Sort By and Group By Column can order."""
        node = self._node_now()
        return node is not None and bool(node.loader) and node.loader != ISSUES_LOADER

    def order_fields(self, node: Any) -> tuple[str, ...]:
        return fields_for(self.all_columns(node))  # type: ignore[attr-defined]

    # -- the remembered choices ---------------------------------------------------

    def _saved(self) -> Any:
        from quill.ui.github_workbench_loaders import saved_items_for

        return saved_items_for(self.items)

    def column_order(self, loader: str) -> ColumnOrder:
        try:
            return ColumnOrder.from_stored(self._saved().columns.get(sort_store_key(loader), []))
        except Exception:  # noqa: BLE001 - an unreadable choice is no order
            return ColumnOrder()

    def column_group(self, loader: str) -> str:
        try:
            saved = self._saved().columns.get(group_store_key(loader), [])
        except Exception:  # noqa: BLE001 - an unreadable choice is no grouping
            return ""
        return str(saved[0]) if saved else ""

    def _store(self, key: str, value: list[str]) -> None:
        saved = self._saved()
        if value:
            saved.set_columns(key, value)
        elif key in saved.columns:
            del saved.columns[key]
            saved.save()

    # -- applying them ------------------------------------------------------------

    def _cell(self, row: object, field: str) -> str:
        cells = self.cells(row, (field,))  # type: ignore[attr-defined]
        return str(cells[0]) if cells else ""

    def order_loaded(self, node: Any, rows: list[object]) -> list[object]:
        """A list's rows in its chosen column order (off the UI thread; no wx)."""
        if not node.loader or node.loader == ISSUES_LOADER:
            return rows
        order = self.column_order(node.loader)
        if not order.chosen or order.field not in self.order_fields(node):
            return rows
        return order_rows(rows, order, lambda row: text_of(row, order.field, self._cell))

    def column_groups(self, node: Any, rows: list[object]) -> list[tuple[str, list[object]]]:
        """The groups for a column-grouped list; [] when it is not grouped."""
        field = self.column_group(node.loader) if node is not None else ""
        if not field or node.loader == ISSUES_LOADER or field not in self.order_fields(node):
            return []
        return group_by_field(rows, lambda row: text_of(row, field, self._cell))

    def column_grouped(self) -> bool:
        node = self._node_now()
        return (
            node is not None
            and node.loader != ISSUES_LOADER
            and bool(self.column_group(node.loader))
        )

    def clear_column_group(self) -> None:
        node = self._node_now()
        if node is not None and node.loader != ISSUES_LOADER:
            self._store(group_store_key(node.loader), [])

    # -- the two commands -----------------------------------------------------------

    def sort_by_column(self) -> None:
        """View > Sort By > By Column...: a field and a direction, or GitHub's own order."""
        node = self._node_now()
        if node is None:
            return
        fields = self.order_fields(node)
        choices: list[tuple[str, bool]] = [("", False)]
        labels = ["As GitHub sends it"]
        for name in fields:
            for descending in (False, True):
                choices.append((name, descending))
                end = "last to first" if descending else "first to last"
                labels.append(f"{field_label(name)}, {end}")
        index = self._choose("Sort by Column", "Order this list by:", labels)  # type: ignore[attr-defined]
        if index < 0:
            return
        order = ColumnOrder(*choices[index])
        self._store(sort_store_key(node.loader), order.stored())
        self._reorder(node, order)

    def _reorder(self, node: Any, order: ColumnOrder) -> None:
        frame = self.frame
        loaded = list(frame._loaded)
        if order.chosen:
            frame._loaded = self.order_loaded(node, loaded)
            frame._fill_list()  # keeps the place: the same item, wherever it moved
            self._say(f"Sorted {order.words()}.")
        else:
            frame.reload()  # GitHub's own order again
            self._say("Sorted as GitHub sends it.")

    def group_by_column(self) -> None:
        """View > Group By > By Column...: the list's groups as tree nodes, by one field."""
        node = self._node_now()
        if node is None:
            return
        fields = self.order_fields(node)
        labels = ["No grouping", *(field_label(name) for name in fields)]
        index = self._choose("Group by Column", "Group this list by:", labels)  # type: ignore[attr-defined]
        if index < 0:
            return
        field = fields[index - 1] if index else ""
        self._store(group_store_key(node.loader), [field] if field else [])
        self.apply_grouping()  # type: ignore[attr-defined]
        if not field:
            self._say("Not grouped.")
            return
        count = len(self.column_groups(node, list(self.frame.rows)))
        self._say(f"{count} groups by {field_label(field).lower()}, in the tree.")
