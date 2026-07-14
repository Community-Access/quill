from __future__ import annotations

from quill.core.brf_document import BRFDocument
from quill.core.brf_page_map import build_page_map
from quill.core.brf_repair import (
    compute_layout_metrics,
    iter_lines,
    longest_line_offset,
    longest_page_offset,
    strip_trailing_spaces_all,
    strip_trailing_spaces_current_line,
)


def test_iter_lines_offsets_and_form_feeds() -> None:
    text = "ab\ncde\ffg"
    assert iter_lines(text) == [(0, "ab"), (3, "cde"), (7, "fg")]


def test_iter_lines_crlf_counts_once() -> None:
    assert iter_lines("ab\r\ncd") == [(0, "ab"), (4, "cd")]


def test_longest_line_offset() -> None:
    text = "short\na much longer line\nmid"
    off = longest_line_offset(text)
    assert text[off:].startswith("a much longer line")


def test_strip_trailing_spaces_all_preserves_breaks() -> None:
    text = "abc   \ndef\t\nghi"
    result, removed = strip_trailing_spaces_all(text)
    assert result == "abc\ndef\nghi"
    assert removed == 4  # three spaces on line 1 + one tab on line 2


def test_strip_trailing_spaces_all_exact_count() -> None:
    text = "abc   \ndef\t"
    result, removed = strip_trailing_spaces_all(text)
    assert result == "abc\ndef"
    assert removed == 4  # three spaces + one tab


def test_strip_trailing_spaces_all_keeps_form_feed() -> None:
    text = "page1   \fpage2  "
    result, removed = strip_trailing_spaces_all(text)
    assert result == "page1\fpage2"
    assert removed == 5


def test_strip_trailing_spaces_current_line() -> None:
    text = "keep me  \nother   "
    new_text, new_cursor, removed = strip_trailing_spaces_current_line(text, cursor=3)
    assert new_text == "keep me\nother   "
    assert removed == 2
    assert new_cursor == 3


def test_strip_trailing_spaces_current_line_clamps_cursor() -> None:
    text = "abc   "
    new_text, new_cursor, removed = strip_trailing_spaces_current_line(text, cursor=6)
    assert new_text == "abc"
    assert new_cursor == 3
    assert removed == 3


def test_layout_metrics_flags_over_width() -> None:
    text = "x" * 45 + "\n" + "y" * 10
    doc = BRFDocument.from_text_and_suffix(text, "brf")
    page_map = build_page_map(doc)
    metrics = compute_layout_metrics(page_map, text, 0, cells_per_line=40, lines_per_page=25)
    assert metrics.longest_line_length == 45
    assert metrics.over_width is True
    assert metrics.cells_per_line == 40
    # Going to the longest line lands on the 45-x line (offset 0 here).
    assert longest_line_offset(text) == 0


def test_layout_metrics_page_counts() -> None:
    # Two form-feed pages; second page is deeper.
    text = "a\nb\f" + "\n".join(["line"] * 6)
    doc = BRFDocument.from_text_and_suffix(text, "brf")
    page_map = build_page_map(doc)
    metrics = compute_layout_metrics(page_map, text, 0, cells_per_line=40, lines_per_page=4)
    assert metrics.page_count == 2
    assert metrics.current_page == 1
    assert metrics.longest_page_lines >= 6
    assert metrics.over_depth is True
    assert longest_page_offset(page_map) == text.index("\f") + 1
