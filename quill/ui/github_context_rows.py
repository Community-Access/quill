"""Context-menu rows for GitHub Items and Explore, laid out by the Workbench rules.

The two dialogs decide *which* rows fit the selected item; this collects them
and lays them out the way GitHub PRD section 5 asks: the default action (what
Enter does) first, about eight rows and then a More submenu, and rows about
the whole view kept apart from rows about the item. The split itself is the
shared engine's (:func:`quill.core.workbench.actions.split_for_menu`), so the
Workbench window lays its menus out by the same rule.

A dialog helper that appends a submenu of its own (Housekeeping, Repository
Actions) calls :meth:`ContextRows.AppendSubMenu`, the ``wx.Menu`` spelling, so
the helpers need not know they are being collected.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from quill.core.workbench.actions import split_for_menu

__all__ = ["MORE_LABEL", "VIEW_LABEL", "ContextRows"]

MORE_LABEL = "More"
VIEW_LABEL = "This View"


@dataclass
class _Row:
    label: str
    action: Callable[[], None] | None
    enabled: bool = True
    submenu: Any = None


class ContextRows:
    """Rows collected for one context menu, then laid out onto a ``wx.Menu``.

    *view_labels* names rows that are about the whole view rather than the
    selected item (Refresh, Create Label...); when an item is selected they
    go under a This View submenu at the end, so the item's own rows come
    first and nothing that used to be offered is lost.
    """

    def __init__(self, *, view_labels: Iterable[str] = ()) -> None:
        self._rows: list[_Row] = []
        self._view_labels = frozenset(view_labels)

    def add(self, label: str, action: Callable[[], None], enabled: bool = True) -> None:
        """Add a row; a label already offered is not offered twice."""
        if any(row.label == label for row in self._rows):
            return
        self._rows.append(_Row(label, action, enabled))

    def AppendSubMenu(self, submenu: Any, label: str) -> None:  # noqa: N802 - wx.Menu's name
        self._rows.append(_Row(label, None, True, submenu))

    def labels(self) -> list[str]:
        return [row.label for row in self._rows]

    def populate(self, wx: Any, menu: Any, *, item_selected: bool) -> list[str]:
        """Fill *menu*; returns the top-level labels in the order shown."""
        item_rows = [r for r in self._rows if not item_selected or r.label not in self._view_labels]
        view_rows = [r for r in self._rows if item_selected and r.label in self._view_labels]
        top, more = split_for_menu(item_rows)
        shown: list[str] = []
        for row in top:
            self._append(wx, menu, row)
            shown.append(row.label)
        if more:
            sub = wx.Menu()
            for row in more:
                self._append(wx, sub, row)
            menu.AppendSubMenu(sub, MORE_LABEL)
            shown.append(MORE_LABEL)
        if view_rows:
            sub = wx.Menu()
            for row in view_rows:
                self._append(wx, sub, row)
            menu.AppendSubMenu(sub, VIEW_LABEL)
            shown.append(VIEW_LABEL)
        return shown

    @staticmethod
    def _append(wx: Any, menu: Any, row: _Row) -> None:
        if row.submenu is not None:
            menu.AppendSubMenu(row.submenu, row.label)
            return
        item_id = wx.NewIdRef()
        menu.Append(item_id, row.label)
        menu.Enable(item_id, row.enabled)
        action = row.action
        menu.Bind(wx.EVT_MENU, lambda _event, callback=action: callback(), id=item_id)
