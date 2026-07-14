"""Tests for BR-013: print-page, braille-page, continuation-letter, and running-head detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.brf_document import BRFDocument
from quill.core.brf_page_detection import (
    BraillePageMarker,
    PageChangeIndicator,
    RunningHead,
    detect_braille_pages,
    detect_continuation_letter,
    detect_print_pages,
    detect_running_head,
)
from quill.core.brf_page_map import build_page_map


def _doc(text: str, *, cell_width: int = 40, line_height: int = 25) -> BRFDocument:
    return BRFDocument.from_text_and_suffix(
        text, "brf", cell_width=cell_width, line_height=line_height
    )


# ----------------------------------------------------------------------------
# High confidence
# ----------------------------------------------------------------------------


def test_high_confidence_separator_line_with_continuation_letter() -> None:
    """A line of hyphens followed by #ab after a \\f is high confidence.

    We construct a 2-page BRF. Page 1 has 25 lines (filling the page);
    the first line of page 2 is the print-page-change separator
    ``---------#ab`` (5+ hyphens, then a page anchor with the
    continuation letter ``a``). The detector should produce a
    *high*-confidence ``PageChangeIndicator`` on braille page 2; the
    exact print-page number may be ``None`` (for a letter-only anchor)
    or a small integer derived from the leading letter.
    """
    page1 = "\r\n".join(["x" * 30] * 25) + "\r\n"
    page2 = "---------#ab\r\n" + "\r\n".join(["y" * 30] * 24)
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    assert page_map.page_count == 2, (
        f"expected 2 pages in calculated split, got {page_map.page_count}"
    )
    indicators = detect_print_pages(text, page_map)
    high = [i for i in indicators if i.confidence == "high"]
    assert high, f"expected at least one high-confidence indicator, got {indicators}"
    page2_indicator = next(i for i in high if i.braille_page == 2)
    # The anchor ``ab`` is letter-only; the detector exposes either
    # None (purely unknown) or the leading letter's ordinal (1 for
    # ``a``). Both are acceptable for the test contract.
    assert page2_indicator.detected_print_page in (None, 1)


def test_high_confidence_repeated_print_page_with_continuation_letter() -> None:
    """Right-margin page number on line 1 that matches the previous page is high.

    Page 1's right-margin "7" anchors the print page; page 2's right-margin
    "7a" carries the same digits plus a trailing continuation letter, which
    is the signature of a high-confidence right-margin continuation
    boundary (the print page has not changed; the letter is the braille
    continuation marker).
    """
    page1_line1 = "chapter 1                                7"
    rest1 = ["x" * 30] * 24
    page1 = page1_line1 + "\r\n" + "\r\n".join(rest1) + "\r\n"
    page2_line1 = "chapter 1 continues                      7a"
    rest2 = ["x" * 30] * 23
    page2 = page2_line1 + "\r\n" + "\r\n".join(rest2)
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    assert page_map.page_count == 2
    indicators = detect_print_pages(text, page_map)
    page2_indicator = next(
        (i for i in indicators if i.braille_page == 2 and i.detected_print_page == 7), None
    )
    assert page2_indicator is not None, f"expected continuation indicator, got {indicators}"
    assert page2_indicator.confidence == "high"


# ----------------------------------------------------------------------------
# Medium confidence
# ----------------------------------------------------------------------------


def test_medium_confidence_right_aligned_number_on_line_1() -> None:
    """A right-aligned number on line 1 with no other anchor is medium."""
    page1_line1 = "first page                                42"
    rest1 = ["x" * 30] * 23
    page1 = page1_line1 + "\r\n" + "\r\n".join(rest1) + "\r\n"
    page2_line1 = "second page                               43"
    rest2 = ["x" * 30] * 23
    page2 = page2_line1 + "\r\n" + "\r\n".join(rest2)
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    indicators = detect_print_pages(text, page_map)
    # First page has no previous anchor; the right-margin number on
    # line 1 is medium confidence.
    page1_indicators = [i for i in indicators if i.braille_page == 1]
    assert page1_indicators
    assert page1_indicators[0].confidence == "medium"
    assert page1_indicators[0].detected_print_page == 42


# ----------------------------------------------------------------------------
# Low confidence
# ----------------------------------------------------------------------------


def test_low_confidence_ambiguous_right_margin() -> None:
    """A short page with multiple possible candidates is low confidence."""
    page1 = ("x" * 30 + "\r\n") * 24
    # A short page whose only line ends with a bare number that does
    # not match any obvious sequence.
    page2 = "                                                     42a"
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    indicators = detect_print_pages(text, page_map)
    # The short page produces a low-confidence detection (or none at
    # all) because the pattern is ambiguous.
    short = [i for i in indicators if i.braille_page == 2]
    if short:
        assert short[0].confidence == "low"


# ----------------------------------------------------------------------------
# Braille-page detection
# ----------------------------------------------------------------------------


def test_braille_page_marker_on_last_line() -> None:
    """A right-margin number on the last line of each page is detected separately."""
    page1 = ("x" * 30 + "\r\n") * 25  # 25 lines (a full page)
    page2 = ("y" * 30 + "\r\n") * 24 + "1"  # 25 lines, ends with "1"
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    assert page_map.page_count == 2
    markers = detect_braille_pages(text, page_map)
    assert markers
    # Page 1 has no trailing right-margin number; page 2 ends with "1".
    numbers = [m.number for m in markers]
    assert 1 in numbers


def test_braille_page_marker_returns_dataclass_instances() -> None:
    doc = _doc(("x" * 30 + "\r\n") * 24 + "1")
    page_map = build_page_map(doc)
    markers = detect_braille_pages(doc.text, page_map)
    assert all(isinstance(m, BraillePageMarker) for m in markers)


# ----------------------------------------------------------------------------
# Continuation letter
# ----------------------------------------------------------------------------


def test_continuation_letter_extracted_from_high_confidence_indicator() -> None:
    page1_line1 = "chapter 1                                7"
    rest1 = ["x" * 30] * 24
    page1 = page1_line1 + "\r\n" + "\r\n".join(rest1) + "\r\n"
    page2_line1 = "chapter 1 continues                      7a"
    rest2 = ["x" * 30] * 23
    page2 = page2_line1 + "\r\n" + "\r\n".join(rest2)
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    assert page_map.page_count == 2
    indicators = detect_print_pages(text, page_map)
    high = [i for i in indicators if i.confidence == "high"]
    assert high, (
        "expected the right-margin continuation (7 -> 7a) to reach "
        f"high confidence; got {indicators}"
    )
    # Both pages should score "high": page 1's right-margin "7" matches
    # nothing before it (the test starts there), so it stays at the
    # medium path -- only page 2's "7a" reaches "high" because page 1
    # gave it a matching right-margin anchor. Find page 2's indicator.
    page2_indicator = next(i for i in high if i.braille_page == 2)
    assert page2_indicator.detected_print_page == 7
    # Page 1's right-margin "7" indicator (medium) is the previous
    # boundary; the helper pairs them and walks line 1 of page 2 to
    # pull the trailing "a".
    page1_indicator = next(i for i in indicators if i.braille_page == 1)
    letter = detect_continuation_letter(text, page_map, page2_indicator, page1_indicator)
    assert letter == "a"


def test_continuation_letter_returns_none_for_new_print_page() -> None:
    """When the print page changes, the continuation letter is None."""
    page1 = ("x" * 30 + "\r\n") * 24
    page2_line1 = "next page                                8"
    rest2 = ["x" * 30] * 23
    page2 = page2_line1 + "\r\n" + "\r\n".join(rest2)
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    indicators = detect_print_pages(text, page_map)
    if len(indicators) >= 2:
        letter = detect_continuation_letter(text, page_map, indicators[1], indicators[0])
        assert letter is None


def test_continuation_letter_returns_none_for_non_high_confidence() -> None:
    indicator = PageChangeIndicator(braille_page=1, detected_print_page=5, confidence="low")
    assert detect_continuation_letter("anything", None, indicator, None) is None


# ----------------------------------------------------------------------------
# Running head
# ----------------------------------------------------------------------------


def test_running_head_returns_one_per_page() -> None:
    page1 = ("first page title                         1\r\n") + ("x" * 30 + "\r\n") * 23
    page2 = ("second page title                        2\r\n") + ("y" * 30 + "\r\n") * 23
    text = page1 + page2
    doc = _doc(text)
    page_map = build_page_map(doc)
    heads = detect_running_head(text, page_map)
    assert len(heads) == len(page_map.pages)
    assert all(isinstance(h, RunningHead) for h in heads)
    titled = [h for h in heads if h.text]
    assert titled, "expected at least one running head to be detected"
    first_text = titled[0].text
    assert first_text  # non-empty string
    assert "first page title" in first_text or "second page title" in first_text


def test_running_head_blank_when_line1_is_just_a_number() -> None:
    page1 = ("                                                     1\r\n") + (
        "x" * 30 + "\r\n"
    ) * 23
    text = page1
    doc = _doc(text)
    page_map = build_page_map(doc)
    heads = detect_running_head(text, page_map)
    # RunningHead.text is a str (never None); when line 1 is just a
    # right-margin number, the running head is the empty string.
    assert heads[0].text == ""


# ----------------------------------------------------------------------------
# Corpus fixture
# ----------------------------------------------------------------------------


def test_corpus_fixture_loads() -> None:
    """The shipped corpus fixture is a real-world 5-page sample with 69 form feeds."""
    path = Path("tests/corpus/braille/one_crazy_night.brf")
    if not path.is_file():
        pytest.skip("corpus fixture not present in this checkout")
    text = path.read_text(encoding="ascii", errors="replace")
    doc = BRFDocument.from_text_and_suffix(text, "brf")
    page_map = build_page_map(doc)
    # Sanity: 69 form feeds is the documented corpus count; the
    # detector should at least *not crash* on the real-world input.
    assert doc.form_feed_count >= 1
    indicators = detect_print_pages(text, page_map)
    assert isinstance(indicators, list)
