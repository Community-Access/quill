"""Undo in the Menus window, and Change History when the Workbench opened it (item 20).

The Menus window renamed, moved and removed menu items with no way back, and
the Workbench's Arrange Items handed off to it, so Ctrl+Z in the Workbench
could not reach those changes either. :class:`MenuSteps` gives the window an
**Undo** button and, when the Workbench opened it, puts each change in the
Workbench's Change History too, so Ctrl+Z there undoes it.

What can be put back is put back: a rename takes its old name again, a move puts
every item back where it stood (:mod:`quill.core.wordpress.menu_layout`), and an
item removed from a Navigation block comes back. An item removed from a classic
menu is deleted by WordPress, so that step says it cannot be undone.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import navigation as nav
from quill.core.wordpress.menu_layout import restore, snapshot

__all__ = ["MenuSteps", "Record"]

#: The Workbench's recorder: a step's sentence, and its undo (or None).
Record = Callable[[str, Callable[[], str] | None], None]


class MenuSteps:
    """The changes made in one Menus window, newest last."""

    def __init__(self, api: Any, menu: nav.Menu, record: Record | None = None) -> None:
        self.api = api
        self.menu = menu
        self.record = record
        self._undos: list[tuple[str, Callable[[], str] | None]] = []

    def _add(self, said: str, undo: Callable[[], str] | None) -> None:
        self._undos.append((said, undo))
        if self.record is not None:
            self.record(said, undo)

    def kept(self) -> list[nav.MenuNode]:
        """The menu's layout now, before a move or a removal."""
        return snapshot(self.menu)

    def moved(self, said: str, before: list[nav.MenuNode]) -> None:
        def undo() -> str:
            restore(self.api, self.menu, before)
            return f"Put back: {said.rstrip('.')}."

        self._add(said, undo)

    def renamed(self, node: nav.MenuNode, old: str, new: str) -> None:
        def undo() -> str:
            nav.rename_item(self.api, self.menu, node, old)
            return f"{new} is called {old} again in {self.menu.name}."

        self._add(f"Renamed {old} to {new} in {self.menu.name}.", undo)

    def removed(self, node: nav.MenuNode, before: list[nav.MenuNode]) -> None:
        said = f"Removed {node.title} from {self.menu.name}."
        if self.menu.source != "navigation":
            self._add(said, None)  # WordPress deleted the classic item itself
            return

        def undo() -> str:
            restore(self.api, self.menu, before)
            return f"{node.title} is back in {self.menu.name}."

        self._add(said, undo)

    def undo(self, _index: int | None) -> str:
        """The window's Undo: the newest change made here, and what happened."""
        while self._undos:
            said, undo = self._undos.pop()
            if undo is not None:
                return undo()
            return f"{said.rstrip('.')} cannot be undone."
        return "Nothing to undo in this window."
