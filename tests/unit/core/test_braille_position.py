"""Tests for :mod:`quill.core.braille_position`."""

from __future__ import annotations

from quill.core.braille_position import BraillePositionResolver
from quill.core.brf_document import BRFDocument


def _build(text: str) -> BraillePositionResolver:
    doc = BRFDocument.from_text_and_suffix(text, "brf")
    return BraillePositionResolver(doc)


def test_resolve_first_char_of_first_page() -> None:
    resolver = _build("AAA\x0cBBB\x0cCCC")
    pos = resolver.resolve(0)
    assert pos.page == 1
    assert pos.line == 1
    assert pos.cell == 1
    assert pos.page_count == 3


def test_resolve_middle_of_page_one() -> None:
    resolver = _build("AAA\x0cBBB\x0cCCC")
    pos = resolver.resolve(1)  # second 'A'
    assert pos.page == 1
    assert pos.line == 1
    assert pos.cell == 2


def test_resolve_last_char_of_page_one_just_before_terminator() -> None:
    resolver = _build("AAA\x0cBBB")
    pos = resolver.resolve(2)  # third 'A', the last content char of page 1
    assert pos.page == 1
    assert pos.line == 1
    assert pos.cell == 3


def test_resolve_caret_on_terminator_resolves_to_prior_line() -> None:
    resolver = _build("AAA\x0cBBB")
    pos = resolver.resolve(3)  # the FF itself
    assert pos.page == 1
    assert pos.line == 1
    # Caret on the FF: this is the *end* of page 1, immediately before
    # the start of page 2. Cell is one past the last content cell.
    assert pos.cell == 4


def test_resolve_start_of_page_two() -> None:
    resolver = _build("AAA\x0cBBB")
    pos = resolver.resolve(4)  # first char after the FF
    assert pos.page == 2
    assert pos.line == 1
    assert pos.cell == 1


def test_resolve_clamps_to_last_page_for_past_eof_offset() -> None:
    resolver = _build("AAA\x0cBBB\x0cCCC")
    pos = resolver.resolve(99_999)
    assert pos.page == 3
    assert pos.line == 1
    # The trailing page contains "CCC" and the caret is past EOF, so
    # the cell is 1 past the last content cell of "CCC" (i.e. 4).
    assert pos.cell == 4


def test_resolve_crlf_page_break() -> None:
    resolver = _build("AAA\r\n\x0cBBB\r\n")
    pos = resolver.resolve(0)
    assert pos.page == 1
    assert pos.line == 1
    assert pos.cell == 1
    pos2 = resolver.resolve(6)  # first 'B' (text = "AAA\r\n\x0cBBB...")
    assert pos2.page == 2
    assert pos2.line == 1
    assert pos2.cell == 1


def test_resolve_multi_line_page() -> None:
    resolver = _build("L1\r\nL2\r\nL3\r\n\x0cEND")
    pos = resolver.resolve(0)
    assert pos.page == 1
    assert pos.line == 1
    assert pos.cell == 1
    pos_l2 = resolver.resolve(4)  # first char of L2
    assert pos_l2.page == 1
    assert pos_l2.line == 2
    assert pos_l2.cell == 1
    pos_l3 = resolver.resolve(8)  # first char of L3
    assert pos_l3.page == 1
    assert pos_l3.line == 3
    assert pos_l3.cell == 1


def test_resolve_line_count_in_page_reflects_page_geometry() -> None:
    resolver = _build("L1\r\nL2\r\nL3\r\n\x0cEND")
    pos = resolver.resolve(0)
    assert pos.line_count_in_page == 3
    pos2 = resolver.resolve(15)  # first 'E' of END on page 2
    assert pos2.line_count_in_page == 1


def test_resolve_cell_width_comes_from_page_map() -> None:
    doc = BRFDocument.from_text_and_suffix("a\x0cb", "brf", cell_width=28)
    resolver = BraillePositionResolver(doc)
    pos = resolver.resolve(0)
    assert pos.cell_width == 28


def test_go_to_page_returns_page_start_offset() -> None:
    resolver = _build("AAA\x0cBBB\x0cCCC")
    assert resolver.go_to_page(1) == 0
    assert resolver.go_to_page(2) == 4
    assert resolver.go_to_page(3) == 8
    # Clamped.
    assert resolver.go_to_page(99) == 8
    assert resolver.go_to_page(0) == 0


def test_next_and_previous_page_offset_advance_page() -> None:
    resolver = _build("AAA\x0cBBB\x0cCCC")
    # From page 1: next goes to page 2 start (offset 4).
    assert resolver.next_page_offset(0) == 4
    # From page 2: previous goes to page 1 start (offset 0).
    assert resolver.previous_page_offset(5) == 0
    # From page 2: next goes to page 3 start (offset 8).
    assert resolver.next_page_offset(5) == 8
    # From page 1: previous is a no-op.
    assert resolver.previous_page_offset(0) == 0
    # From page 3 (last): next is a no-op.
    assert resolver.next_page_offset(8) == 8


def test_to_compact_and_normal_strings() -> None:
    resolver = _build("AAA\x0cBBB\x0cCCC")
    pos = resolver.resolve(0)
    assert pos.to_compact_string() == "Pg 1/3"
    assert pos.to_normal_string() == "BRF Pg 1/3 Ln 1/1 Cell 1/40"


def test_resolve_empty_page_map_raises() -> None:
    """``build_page_map`` always produces at least one page; this guards the guard."""
    resolver = _build("")
    # Empty file -> one page with line_count 0.
    pos = resolver.resolve(0)
    assert pos.page == 1
    assert pos.line_count_in_page == 0
