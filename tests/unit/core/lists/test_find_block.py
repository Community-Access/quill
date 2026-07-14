"""Unit tests for in-place list detection (find_list_block / list_block_to_flat)."""

from __future__ import annotations

from quill.core.lists.model import ListType
from quill.core.lists.parse import find_list_block, list_block_to_flat

# -- find_list_block ------------------------------------------------------- #


def test_caret_outside_any_list_returns_none() -> None:
    text = "Just a paragraph of prose.\n"
    assert find_list_block(text, 5) is None


def test_finds_contiguous_block_around_caret() -> None:
    text = "intro\n- one\n- two\n- three\noutro\n"
    # Caret on the "- two" line.
    offset = text.index("- two") + 2
    block = find_list_block(text, offset)
    assert block is not None
    start, end = block
    assert text[start:end] == "- one\n- two\n- three"


def test_block_stops_at_blank_line() -> None:
    text = "- a\n- b\n\n- c\n"
    block = find_list_block(text, 0)
    assert block is not None
    start, end = block
    assert text[start:end] == "- a\n- b"


def test_block_excludes_trailing_newline() -> None:
    text = "- only\n"
    block = find_list_block(text, 1)
    assert block == (0, len("- only"))


def test_empty_text_returns_none() -> None:
    assert find_list_block("", 0) is None


# -- list_block_to_flat ---------------------------------------------------- #


def test_block_to_flat_preserves_checklist_and_checked() -> None:
    flat = list_block_to_flat("- [x] done\n- [ ] todo")
    assert flat.list_type is ListType.CHECKLIST
    assert [(i.text, i.checked) for i in flat.items] == [("done", True), ("todo", False)]


def test_block_to_flat_detects_ordered() -> None:
    flat = list_block_to_flat("1. first\n2. second")
    assert flat.list_type is ListType.ORDERED
    assert [i.text for i in flat.items] == ["first", "second"]


def test_block_to_flat_ranks_indentation_into_levels() -> None:
    text = "- top\n  - child\n    - grandchild\n- top2"
    flat = list_block_to_flat(text)
    assert [i.level for i in flat.items] == [0, 1, 2, 0]
    assert [i.text for i in flat.items] == ["top", "child", "grandchild", "top2"]


def test_block_to_flat_normalizes_four_space_indents() -> None:
    text = "- top\n    - child"  # 4-space indent still ranks to level 1
    flat = list_block_to_flat(text)
    assert [i.level for i in flat.items] == [0, 1]


def test_block_to_flat_empty_yields_single_item() -> None:
    flat = list_block_to_flat("")
    assert flat.list_type is ListType.BULLET
    assert len(flat.items) == 1
    assert flat.items[0].text == ""
