"""Landing the Podcast Manager's cursor on a row somebody already has (11.6).

Duplicate detection is two halves, and the second one is the useful one: when
adding a show that is already followed, say so *and go to it*. Somebody adds a
podcast twice because they could not find the first copy, so a refusal that
leaves the cursor where it was answers the wrong question.

Extracted from ``manager_dialog.py`` rather than grown inside it -- that
module is at its GATE-11 ceiling, and walking a tree to find one row is a
self-contained concern with one input and one job.
"""

from __future__ import annotations

from typing import Any


def _item_key(item: object) -> int:
    """The stable identity of a tree item (see ``manager_dialog._item_key``)."""
    from quill.ui.podcasts.manager_dialog import _item_key as key_of

    return key_of(item)


class ManagerRevealMixin:
    """Move the show tree's cursor to a named show."""

    def select_show(self, show_id: str) -> bool:
        """Land the cursor on *show_id*'s row. True when it did.

        False when the show is not in the tree -- filtered out, in a collapsed
        branch the walk cannot see, or simply gone. The caller says "nothing
        was added" instead of promising a move that did not happen.
        """
        wanted = (show_id or "").strip()
        if not wanted:
            return False
        for item in self._tree_items():
            if self._tree_item_show.get(_item_key(item)) != wanted:
                continue
            self._tree.SelectItem(item)
            self._tree.EnsureVisible(item)
            self._tree.SetFocus()
            return True
        return False

    def _tree_items(self) -> list[Any]:
        """Every row in the show tree, depth-first (small trees, plain walk)."""
        rows: list[Any] = []

        def walk(parent: Any) -> None:
            child, cookie = self._tree.GetFirstChild(parent)
            while child.IsOk():
                rows.append(child)
                walk(child)
                child, cookie = self._tree.GetNextChild(parent, cookie)

        root = self._tree.GetRootItem()
        if root.IsOk():
            walk(root)
        return rows
