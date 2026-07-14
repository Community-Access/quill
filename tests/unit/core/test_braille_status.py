"""Tests for BR-009: Braille Mode status-string builders."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.braille_position import BraillePosition
from quill.core.braille_status import (
    ConfidenceLevel,
    PrintPageInfo,
    ProofingStatus,
    brief_status,
    detailed_status,
    normal_status,
    spoken_status,
)


def _position(
    page: int = 12,
    line: int = 14,
    cell: int = 31,
    page_count: int = 87,
    line_count_in_page: int = 25,
    cell_width: int = 40,
) -> BraillePosition:
    return BraillePosition(
        page=page,
        line=line,
        cell=cell,
        page_offset=0,
        line_offset=0,
        page_count=page_count,
        line_count_in_page=line_count_in_page,
        cell_width=cell_width,
    )


def _profile(verbosity: str = "normal") -> SimpleNamespace:
    return SimpleNamespace(braille_status_verbosity=verbosity)


def test_brief_status_matches_braille_md_example() -> None:
    out = brief_status(_position(), 87, _profile("brief"))
    assert out == "Page 12. Line 14. Cell 31."


def test_normal_status_matches_braille_md_example() -> None:
    out = normal_status(_position(), 87, PrintPageInfo(number=7), _profile("normal"))
    assert out == ("Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7.")


def test_detailed_status_matches_braille_md_example() -> None:
    out = detailed_status(
        _position(),
        87,
        PrintPageInfo(number=7),
        "a",
        "Chapter 2",
        ProofingStatus(last_proofed_page=9, pages_needing_review=3, total_pages=87),
        ConfidenceLevel("high", 0.97),
        _profile("detailed"),
    )
    assert out == (
        "Braille page 12 of 87. "
        "Line 14 of 25. Cell 31 of 40. "
        "Print page 7. "
        "continuation a; "
        "Running head: Chapter 2; "
        "Last proofed page: 9; "
        "3 pages marked needs review; "
        "detected with high confidence."
    )


def test_normal_status_says_print_page_unknown_when_absent() -> None:
    out = normal_status(_position(page=14), 87, PrintPageInfo(number=None), _profile("normal"))
    assert out == "Braille page 14 of 87. Line 14 of 25. Cell 31 of 40. Print page unknown."


def test_detailed_status_reports_all_proofed() -> None:
    out = detailed_status(
        _position(),
        87,
        PrintPageInfo(number=7),
        None,
        None,
        ProofingStatus(last_proofed_page=87, pages_needing_review=0, total_pages=87),
        ConfidenceLevel("high", 1.0),
        _profile("detailed"),
    )
    assert "All pages proofed" in out
    assert "needs review" not in out


def test_detailed_status_singular_needs_review() -> None:
    out = detailed_status(
        _position(),
        87,
        PrintPageInfo(number=7),
        None,
        None,
        ProofingStatus(last_proofed_page=9, pages_needing_review=1, total_pages=87),
        ConfidenceLevel("high", 1.0),
        _profile("detailed"),
    )
    assert "One page marked needs review" in out


def test_detailed_status_omits_continuation_and_running_head_when_absent() -> None:
    out = detailed_status(
        _position(),
        87,
        PrintPageInfo(number=7),
        None,
        None,
        ProofingStatus(),
        ConfidenceLevel("high", 1.0),
        _profile("detailed"),
    )
    assert "continuation" not in out
    assert "Running head" not in out


def test_spoken_status_dispatches_on_profile_verbosity() -> None:
    position = _position()
    print_page = PrintPageInfo(number=7)
    assert (
        spoken_status(position, 87, print_page, _profile("brief")) == "Page 12. Line 14. Cell 31."
    )
    assert spoken_status(position, 87, print_page, _profile("normal")).startswith(
        "Braille page 12 of 87."
    )
    assert spoken_status(position, 87, print_page, _profile("detailed")).startswith(
        "Braille page 12 of 87."
    )


def test_spoken_status_falls_back_to_normal_for_unknown_verbosity() -> None:
    position = _position()
    out = spoken_status(position, 87, PrintPageInfo(number=7), _profile("shouty"))
    assert out.startswith("Braille page 12 of 87.")
    assert out.endswith("Print page 7.")


def test_spoken_status_falls_back_to_normal_when_profile_lacks_field() -> None:
    out = spoken_status(_position(), 87, PrintPageInfo(number=7), object())
    assert out.startswith("Braille page 12 of 87.")


def test_normal_status_handles_zero_line_count() -> None:
    out = normal_status(
        _position(line_count_in_page=0, cell_width=0),
        87,
        PrintPageInfo(number=1),
        _profile("normal"),
    )
    assert "Line 14. Cell 31." in out


def test_detailed_status_uses_medium_confidence_label() -> None:
    out = detailed_status(
        _position(),
        87,
        PrintPageInfo(number=7),
        None,
        None,
        ProofingStatus(),
        ConfidenceLevel("medium", 0.5),
        _profile("detailed"),
    )
    assert "detected with medium confidence" in out


def test_print_page_info_uses_default_confidence_when_none() -> None:
    info = PrintPageInfo(number=3)
    assert info.effective_confidence.label == "high"


def test_proofing_status_empty_default() -> None:
    proofing = ProofingStatus()
    assert proofing.is_empty


def test_proofing_status_not_empty_when_review_count_set() -> None:
    assert not ProofingStatus(pages_needing_review=2).is_empty


@pytest.mark.parametrize(
    "label,expected",
    [("high", "high"), ("medium", "medium"), ("low", "low"), ("weird", "high"), ("", "high")],
)
def test_detailed_status_normalizes_unknown_confidence_label(label: str, expected: str) -> None:
    out = detailed_status(
        _position(),
        87,
        PrintPageInfo(number=7),
        None,
        None,
        ProofingStatus(),
        ConfidenceLevel(label, 0.5),
        _profile("detailed"),
    )
    assert f"detected with {expected} confidence" in out
