"""Putting a menu's layout back, for Ctrl+Z on a move (review item 20).

A move in the Workbench's Arrange Items window is undone by putting every item
back where it stood. :func:`snapshot` keeps the tree before the move;
:func:`restore` rebuilds that shape from the live items (matched by their
classic item id, or by position in a Navigation block) and saves it, so a
classic menu is sent only the items whose place differs now.
"""

from __future__ import annotations

import copy

from quill.core.wordpress import navigation as nav
from quill.core.wordpress.api import WordPressApi

__all__ = ["restore", "snapshot"]


def snapshot(menu: nav.Menu) -> list[nav.MenuNode]:
    """The menu's tree as it is now, to hand to :func:`restore` later."""
    return copy.deepcopy(menu.nodes)


def _live_by_id(nodes: list[nav.MenuNode]) -> dict[int, nav.MenuNode]:
    return {row.node.item_id: row.node for row in nav.walk(nodes) if row.node.item_id}


def restore(api: WordPressApi, menu: nav.Menu, kept: list[nav.MenuNode]) -> None:
    """Put *menu* back in the shape *kept* recorded, and save what moved."""
    if menu.source == "navigation":
        menu.nodes = copy.deepcopy(kept)
        nav.save_menu(api, menu)
        return
    live = _live_by_id(menu.nodes)

    def rebuild(items: list[nav.MenuNode]) -> list[nav.MenuNode]:
        out = []
        for old in items:
            node = live.get(old.item_id, old)
            node.children = rebuild(old.children)
            out.append(node)
        return out

    menu.nodes = rebuild(kept)
    nav.save_menu(api, menu)
