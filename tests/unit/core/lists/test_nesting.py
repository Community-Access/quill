"""Unit tests for the wx-free list nesting operations (PRD Phase 2)."""

from __future__ import annotations

from quill.core.lists.model import ListItem
from quill.core.lists.nesting import (
    add_child,
    can_indent,
    can_outdent,
    indent,
    move_subtree,
    outdent,
    subtree_end,
)


def _levels(items: list[ListItem]) -> list[int]:
    return [item.level for item in items]


def _items(*levels: int) -> list[ListItem]:
    return [ListItem(text=f"item{i}", level=lvl) for i, lvl in enumerate(levels)]


# -- subtree_end ----------------------------------------------------------- #


def test_subtree_end_includes_deeper_following_items() -> None:
    items = _items(0, 1, 2, 0)
    assert subtree_end(items, 0) == 3  # item0 owns the two deeper items
    assert subtree_end(items, 1) == 3
    assert subtree_end(items, 3) == 4  # last item, no children


def test_subtree_end_stops_at_sibling() -> None:
    items = _items(0, 1, 1, 0)
    assert subtree_end(items, 1) == 2  # sibling at same level is not a child


# -- indent ---------------------------------------------------------------- #


def test_first_item_cannot_indent() -> None:
    items = _items(0, 0)
    assert can_indent(items, 0) is False
    assert indent(items, 0) is False
    assert _levels(items) == [0, 0]


def test_indent_under_previous_sibling() -> None:
    items = _items(0, 0)
    assert can_indent(items, 1) is True
    assert indent(items, 1) is True
    assert _levels(items) == [0, 1]


def test_cannot_indent_more_than_one_level_past_parent() -> None:
    items = _items(0, 1)
    # item1 is already a child of item0; indenting again would create a gap.
    assert can_indent(items, 1) is False
    assert indent(items, 1) is False


def test_indent_carries_subtree() -> None:
    items = _items(0, 0, 1)  # item1 (top level) owns item2 as a child
    assert indent(items, 1) is True
    assert _levels(items) == [0, 1, 2]


# -- outdent --------------------------------------------------------------- #


def test_outdent_top_level_is_noop() -> None:
    items = _items(0, 0)
    assert can_outdent(items, 0) is False
    assert outdent(items, 0) is False


def test_outdent_carries_subtree() -> None:
    items = _items(0, 1, 2)
    assert outdent(items, 1) is True
    assert _levels(items) == [0, 0, 1]


# -- add_child ------------------------------------------------------------- #


def test_add_child_inserts_one_level_deeper() -> None:
    items = _items(0)
    new_index = add_child(items, 0, text="kid")
    assert new_index == 1
    assert _levels(items) == [0, 1]
    assert items[1].text == "kid"


def test_add_child_with_no_selection_appends_top_level() -> None:
    items = _items(0, 0)
    new_index = add_child(items, -1)
    assert new_index == 2
    assert items[2].level == 0


# -- move_subtree ---------------------------------------------------------- #


def test_move_subtree_down_swaps_with_following_sibling() -> None:
    items = _items(0, 1, 0)  # [a, a.child, b]
    texts_before = [it.text for it in items]
    new_index = move_subtree(items, 0, 1)  # move 'a' (+ its child) below 'b'
    assert _levels(items) == [0, 0, 1]
    assert items[0].text == texts_before[2]  # b first now
    assert new_index == 1


def test_move_subtree_up_swaps_with_preceding_sibling() -> None:
    items = _items(0, 0, 1)  # [a, b, b.child]
    new_index = move_subtree(items, 1, -1)  # move 'b' (+ child) above 'a'
    assert [it.text for it in items][:1] == ["item1"]
    assert _levels(items) == [0, 1, 0]
    assert new_index == 0


def test_move_subtree_no_sibling_is_noop() -> None:
    items = _items(0, 1)  # child has no sibling in either direction
    assert move_subtree(items, 1, -1) == 1
    assert move_subtree(items, 1, 1) == 1
    assert _levels(items) == [0, 1]


def test_move_subtree_rejects_bad_direction() -> None:
    items = _items(0, 0)
    assert move_subtree(items, 0, 0) == 0
