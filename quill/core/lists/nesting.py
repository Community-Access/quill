"""Nesting operations for flat structured lists (PRD Phase 2 — §6.3, §22).

Pure, wx-free transformations on a ``FlatList``'s item levels: indent, outdent,
add-child, and subtree-aware reordering. A node's descendants always travel with
it so the outline never tears a child away from its parent. All validity rules
live here and are unit-tested (``tests/unit/core/lists/test_nesting.py``); the
F2 Structured List Studio dialog is a thin caller.
"""

from __future__ import annotations

from quill.core.lists.model import ListItem


def subtree_end(items: list[ListItem], index: int) -> int:
    """Exclusive end index of the subtree rooted at ``index``.

    The subtree is ``index`` plus the contiguous run of following items whose
    level is deeper than ``items[index].level``.
    """
    if index < 0 or index >= len(items):
        return index + 1
    base = items[index].level
    end = index + 1
    while end < len(items) and items[end].level > base:
        end += 1
    return end


def can_indent(items: list[ListItem], index: int) -> bool:
    """True when item ``index`` can nest one level deeper.

    An item can indent only if the item directly above it is at the same or a
    deeper level (so it gains a valid parent and no level gap is created). The
    first item never has a parent above it and so can never indent.
    """
    if index <= 0 or index >= len(items):
        return False
    return items[index].level <= items[index - 1].level


def can_outdent(items: list[ListItem], index: int) -> bool:
    """True when item ``index`` is nested and can move one level shallower."""
    return 0 <= index < len(items) and items[index].level > 0


def indent(items: list[ListItem], index: int) -> bool:
    """Nest item ``index`` (and its subtree) one level deeper. Return True if changed."""
    if not can_indent(items, index):
        return False
    for i in range(index, subtree_end(items, index)):
        items[i].level += 1
    return True


def outdent(items: list[ListItem], index: int) -> bool:
    """Un-nest item ``index`` (and its subtree) one level shallower. Return True if changed."""
    if not can_outdent(items, index):
        return False
    for i in range(index, subtree_end(items, index)):
        items[i].level -= 1
    return True


def add_child(items: list[ListItem], index: int, text: str = "") -> int:
    """Insert a new child directly under item ``index``; return the child's index.

    The child is placed immediately after its parent (the parent's first child)
    at one level deeper, which is always structurally valid. With no valid
    selection the new item is appended at the top level.
    """
    if index < 0 or index >= len(items):
        items.append(ListItem(text))
        return len(items) - 1
    child = ListItem(text, level=items[index].level + 1)
    items.insert(index + 1, child)
    return index + 1


def _prev_sibling_start(items: list[ListItem], index: int) -> int:
    """Start index of the sibling subtree immediately preceding ``index``.

    Returns ``-1`` when ``index`` is the first child of its parent (no preceding
    sibling at the same level within the same parent).
    """
    level = items[index].level
    i = index - 1
    while i >= 0:
        if items[i].level < level:
            return -1  # hit the parent — no preceding sibling
        if items[i].level == level:
            return i
        i -= 1
    return -1


def move_subtree(items: list[ListItem], index: int, direction: int) -> int:
    """Reorder the subtree at ``index`` among its siblings. Return its new index.

    ``direction`` is ``-1`` (up) or ``+1`` (down). The whole subtree moves as a
    block and swaps places with the adjacent sibling subtree, so nesting is
    preserved. Returns the unchanged ``index`` when there is no sibling to swap
    with in that direction.
    """
    if index < 0 or index >= len(items) or direction not in (-1, 1):
        return index
    start = index
    end = subtree_end(items, index)
    block = items[start:end]

    if direction == -1:
        prev = _prev_sibling_start(items, index)
        if prev < 0:
            return index
        # Move the block to where the preceding sibling starts.
        del items[start:end]
        items[prev:prev] = block
        return prev

    # direction == +1: the next sibling is whatever begins at ``end`` at the
    # same level; if it is deeper or shallower there is no following sibling.
    if end >= len(items) or items[end].level != items[index].level:
        return index
    next_end = subtree_end(items, end)
    del items[start:end]
    insert_at = next_end - (end - start)
    items[insert_at:insert_at] = block
    return insert_at
