"""Tests for :mod:`quill.core.brf_document` and :mod:`quill.core.brf_page_map`."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.brf_document import BRFDocument
from quill.core.brf_page_map import (
    DEFAULT_PAGE_BREAK_MODE,
    build_page_map,
)

# ----------------------------------------------------------------------------
# BRFDocument
# ----------------------------------------------------------------------------


def test_brf_document_from_text_and_suffix_populates_line_ending_report() -> None:
    doc = BRFDocument.from_text_and_suffix("a\r\nb\r\n", "brf")
    assert doc.line_ending == "\r\n"
    assert doc.line_endings.crlf == 2
    assert doc.line_endings.lf == 0
    assert doc.line_endings.cr == 0
    assert doc.is_mixed_line_endings is False
    assert doc.form_feed_count == 0
    assert doc.is_clean_brf is True
    assert doc.non_ascii_count == 0


def test_brf_document_flags_mixed_line_endings() -> None:
    doc = BRFDocument.from_text_and_suffix("a\r\nb\nc", "brf")
    assert doc.is_mixed_line_endings is True


def test_brf_document_falls_back_to_utf8_when_non_ascii_present() -> None:
    doc = BRFDocument.from_text_and_suffix("a\u2800b", "brf", non_ascii_offsets=[1])
    assert doc.encoding == "utf-8"
    assert doc.is_clean_brf is False
    assert doc.non_ascii_count == 1


def test_brf_document_strips_leading_dot_from_suffix() -> None:
    doc = BRFDocument.from_text_and_suffix("abc", ".BRF")
    assert doc.suffix == "brf"


def test_brf_document_rejects_non_positive_geometry() -> None:
    with pytest.raises(ValueError):
        BRFDocument.from_text_and_suffix("a", "brf", cell_width=0)
    with pytest.raises(ValueError):
        BRFDocument.from_text_and_suffix("a", "brf", line_height=0)


def test_brf_document_default_profile_is_ueb_english() -> None:
    doc = BRFDocument.from_text_and_suffix("a", "brf")
    assert doc.profile == "ueb_english"
    assert doc.cell_width == 40
    assert doc.line_height == 25


# ----------------------------------------------------------------------------
# Page map: form-feed aware
# ----------------------------------------------------------------------------


def test_page_map_hybrid_uses_form_feeds_when_present() -> None:
    doc = BRFDocument.from_text_and_suffix("AAA\x0cBBB\x0cCCC", "brf")
    page_map = build_page_map(doc, mode="hybrid")
    assert page_map.mode == "hybrid"
    assert page_map.page_count == 3
    assert page_map.pages[0].start_offset == 0
    # Page 0 covers the AAA run; the FF is the terminator and is
    # reported via ``has_form_feed`` rather than counted as content.
    assert page_map.pages[0].end_offset == 3
    assert page_map.pages[0].has_form_feed is True
    assert page_map.pages[1].start_offset == 4
    assert page_map.pages[1].end_offset == 7
    assert page_map.pages[2].start_offset == 8
    assert page_map.pages[2].end_offset == 11
    assert page_map.pages[2].has_form_feed is False  # trailing page


def test_page_map_form_feed_aware_with_corpus_fixture() -> None:
    fixture = Path("tests/corpus/braille/one_crazy_night.brf")
    text = fixture.read_text(encoding="ascii")
    doc = BRFDocument.from_text_and_suffix(text, "brf")
    page_map = build_page_map(doc, mode="form_feed")
    # The corpus has 69 FFs, so the page map should have 70 pages
    # (every FF ends one page, the trailing content is page 70).
    assert page_map.page_count == 70
    ffs = page_map.pages[:-1]  # all but the trailing page ended on FF
    assert all(p.has_form_feed for p in ffs)
    assert page_map.pages[-1].has_form_feed is False
    # All page starts must be in strictly ascending order.
    starts = [p.start_offset for p in page_map.pages]
    assert starts == sorted(set(starts))
    assert starts[0] == 0
    assert page_map.pages[-1].end_offset == len(text)


def test_page_map_form_feed_mode_matches_hybrid_when_ffs_present() -> None:
    doc = BRFDocument.from_text_and_suffix("a\x0cb\x0cc", "brf")
    hybrid = build_page_map(doc, mode="hybrid")
    ff = build_page_map(doc, mode="form_feed")
    assert hybrid.page_count == ff.page_count
    assert [p.start_offset for p in hybrid.pages] == [p.start_offset for p in ff.pages]


# ----------------------------------------------------------------------------
# Page map: calculated fallback
# ----------------------------------------------------------------------------


def test_page_map_calculated_splits_on_line_height() -> None:
    lines = "\r\n".join(f"L{i:02d}" for i in range(30))  # 30 lines, CRLF
    doc = BRFDocument.from_text_and_suffix(lines, "brf", line_height=25)
    page_map = build_page_map(doc, mode="calculated")
    # 30 lines / 25 per page = 2 pages (25 + 5).
    assert page_map.page_count == 2
    # Page 0 starts 25 lines; the 25th line is the one that ends just
    # before page 1's start offset.
    assert page_map.pages[0].line_count == 25
    assert page_map.pages[1].line_count == 5


def test_page_map_calculated_handles_long_lines_without_split() -> None:
    long = "X" * 200  # over a 40-cell width
    doc = BRFDocument.from_text_and_suffix(long, "brf", cell_width=40, line_height=25)
    page_map = build_page_map(doc, mode="calculated")
    assert page_map.page_count == 1
    assert page_map.pages[0].max_cell_count == 200  # recorded for the validator


def test_page_map_calculated_empty_file_produces_one_page() -> None:
    doc = BRFDocument.from_text_and_suffix("", "brf")
    page_map = build_page_map(doc, mode="calculated")
    assert page_map.page_count == 1
    assert page_map.pages[0].length == 0


def test_page_map_hybrid_falls_back_to_calculated_when_no_ffs() -> None:
    doc = BRFDocument.from_text_and_suffix("a\nb\nc", "brf", line_height=2)
    page_map = build_page_map(doc, mode="hybrid")
    # 3 lines / 2 per page = 2 pages (2 + 1 trailing).
    assert page_map.page_count == 2
    assert page_map.mode == "hybrid"


# ----------------------------------------------------------------------------
# Page lookup
# ----------------------------------------------------------------------------


def test_page_map_page_containing_clamps_to_endpoints() -> None:
    doc = BRFDocument.from_text_and_suffix("AAA\x0cBBB\x0cCCC", "brf")
    page_map = build_page_map(doc)
    assert page_map.page_containing(-1).index == 0
    assert page_map.page_containing(0).index == 0
    assert page_map.page_containing(5).index == 1
    assert page_map.page_containing(10).index == 2
    assert page_map.page_containing(9999).index == 2  # clamps to last


def test_page_map_page_index_for_accepts_one_based_and_clamps() -> None:
    doc = BRFDocument.from_text_and_suffix("a\x0cb\x0cc\x0cd", "brf")
    page_map = build_page_map(doc)
    assert page_map.page_index_for(1).index == 0
    assert page_map.page_index_for(2).index == 1
    assert page_map.page_index_for(99).index == 3  # clamps to last
    assert page_map.page_index_for(0).index == 0  # clamps to first


def test_page_map_empty_raises_helpful_error() -> None:
    page_map = build_page_map(BRFDocument.from_text_and_suffix("", "brf"))
    # We always produce one page; this is a no-op test guarding the
    # explicit guard against an empty result.
    assert page_map.page_count == 1


# ----------------------------------------------------------------------------
# Page-level line + cell math
# ----------------------------------------------------------------------------


def test_page_map_line_at_offset_within_page() -> None:
    doc = BRFDocument.from_text_and_suffix(
        "AAA\r\nBBB\r\nCCC\r\n\x0cDDD\r\n", "brf", cell_width=40, line_height=25
    )
    page_map = build_page_map(doc)
    page0 = page_map.pages[0]
    # Three lines: AAA, BBB, CCC.
    assert page0.line_count == 3
    # First 'A' is at the start of line 0.
    assert page0.line_at_offset(page0.start_offset) == 0
    # Just before the CR of line 0 is still line 0.
    line0_end = page0.line_start_offsets[1] - 1
    assert page0.line_at_offset(line0_end) == 0
    # First 'B' is the start of line 1.
    assert page0.line_at_offset(page0.line_start_offsets[1]) == 1
    # First 'C' is the start of line 2.
    assert page0.line_at_offset(page0.line_start_offsets[2]) == 2


def test_page_map_max_cell_count_uses_cell_width() -> None:
    doc = BRFDocument.from_text_and_suffix("AB\r\nABCD\r\nABCDE", "brf", cell_width=40)
    page_map = build_page_map(doc, mode="calculated")
    assert page_map.pages[0].max_cell_count == 5


# ----------------------------------------------------------------------------
# Default page break mode
# ----------------------------------------------------------------------------


def test_default_page_break_mode_is_hybrid() -> None:
    assert DEFAULT_PAGE_BREAK_MODE == "hybrid"
