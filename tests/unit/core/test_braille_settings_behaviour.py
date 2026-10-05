"""The six Braille Mode settings change what happens (questions.md item 38).

Each was saved and shown and read by nothing. Every test here flips one switch
and proves the outcome differs, through the same functions the shell calls.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.braille_cues import (
    CaretSnapshot,
    already_said,
    movement_cues,
    page_break_mode,
    print_page_at,
    proofing_status_from_sidecar,
    snapshot,
)
from quill.core.braille_position import BraillePositionResolver
from quill.core.braille_status import (
    ConfidenceLevel,
    PrintPageInfo,
    ProofingStatus,
    detailed_status,
)
from quill.core.brf_document import BRFDocument
from quill.core.brf_page_detection import PageChangeIndicator
from quill.core.brf_sidecar import BRFSidecar
from quill.core.settings import Settings


def _no_form_feeds(lines: int = 30) -> BRFDocument:
    text = "\n".join(f"line {n}" for n in range(lines)) + "\n"
    return BRFDocument.from_text_and_suffix(text, ".brf", line_height=25)


# --- braille_calculate_pages -------------------------------------------------


def test_calculate_pages_on_splits_a_file_with_no_page_breaks() -> None:
    mode = page_break_mode(Settings())
    assert mode == "hybrid"
    assert BraillePositionResolver(_no_form_feeds(), mode=mode).page_map.page_count == 2


def test_calculate_pages_off_leaves_a_file_with_no_page_breaks_as_one_page() -> None:
    mode = page_break_mode(Settings(braille_calculate_pages=False))
    assert mode == "form_feed"
    assert BraillePositionResolver(_no_form_feeds(), mode=mode).page_map.page_count == 1


def test_form_feeds_off_counts_pages_by_size_alone() -> None:
    text = "a\x0cb\n" + "\n".join("x" for _ in range(30))
    doc = BRFDocument.from_text_and_suffix(text, ".brf", line_height=25)
    hybrid = BraillePositionResolver(doc, mode=page_break_mode(Settings()))
    sized = BraillePositionResolver(
        doc, mode=page_break_mode(Settings(braille_use_form_feeds=False))
    )
    assert hybrid.page_map.page_count == 2
    assert sized.page_map.page_count == 2
    assert hybrid.page_map.pages[0].end_offset == 1  # the form feed ends page 1
    assert sized.page_map.pages[0].end_offset != 1


# --- braille_include_continuation / braille_include_proofing_status ---------


def _detailed(settings: object, proofing: ProofingStatus) -> str:
    position = BraillePositionResolver(_no_form_feeds()).resolve(0)
    print_page = PrintPageInfo(number=7, continuation="a")
    return detailed_status(
        position, 2, print_page, None, None, proofing, ConfidenceLevel(), settings
    )


def test_include_continuation_on_names_the_letter() -> None:
    assert "continuation a" in _detailed(Settings(), ProofingStatus())


def test_include_continuation_off_drops_the_letter() -> None:
    text = _detailed(Settings(braille_include_continuation=False), ProofingStatus())
    assert "continuation" not in text
    assert "Print page 7" in text


def test_include_proofing_on_reports_the_companion_file() -> None:
    sidecar = BRFSidecar()
    sidecar.proofing.last_proofed_braille_page = 9
    sidecar.proofing.pages_needing_review = [3, 4, 4]
    proofing = proofing_status_from_sidecar(sidecar, 87)
    text = _detailed(Settings(), proofing)
    assert "Last proofed page: 9" in text
    assert "2 pages marked needs review" in text


def test_include_proofing_off_leaves_it_out() -> None:
    proofing = ProofingStatus(last_proofed_page=9, pages_needing_review=2, total_pages=87)
    text = _detailed(Settings(braille_include_proofing_status=False), proofing)
    assert "proofed" not in text
    assert "review" not in text


def test_no_companion_file_means_no_proofing_clause() -> None:
    assert proofing_status_from_sidecar(None, 5).is_empty
    assert "proofed" not in _detailed(Settings(), proofing_status_from_sidecar(None, 5))


# --- the three movement cues -------------------------------------------------


def _snap(page: int = 1, print_page: int | None = None, line: int = 0, cells: int = 10):
    return CaretSnapshot(
        page=page, print_page=print_page, line_offset=line, line_cells=cells, cell_width=40
    )


def test_page_change_cue_follows_its_setting() -> None:
    before, after = _snap(page=1), _snap(page=2, line=500)
    assert movement_cues(before, after, Settings()) == []
    on = Settings(braille_auto_announce_page_changes=True)
    assert movement_cues(before, after, on) == ["Braille page 2."]
    assert movement_cues(after, _snap(page=2, line=520), on) == []


def test_print_page_change_cue_follows_its_setting() -> None:
    before, after = _snap(print_page=6), _snap(print_page=7)
    assert movement_cues(before, after, Settings()) == []
    on = Settings(braille_auto_announce_print_page_changes=True)
    assert movement_cues(before, after, on) == ["Print page 7."]
    # No print page map: skipped, as the setting's help says.
    assert movement_cues(before, _snap(print_page=None), on) == []


def test_line_overflow_cue_follows_its_setting() -> None:
    short, long_line = _snap(line=0, cells=10), _snap(line=50, cells=45)
    assert movement_cues(short, long_line, Settings()) == []
    on = Settings(braille_auto_announce_line_overflow=True)
    assert movement_cues(short, long_line, on) == ["Line too long: 45 cells, limit 40."]
    # Moving along the same long line says nothing more.
    assert movement_cues(long_line, _snap(line=50, cells=45), on) == []
    # Typing the current line past the limit says it once.
    assert movement_cues(_snap(line=50, cells=40), _snap(line=50, cells=41), on) == [
        "Line too long: 41 cells, limit 40."
    ]


def test_first_position_says_nothing() -> None:
    every = SimpleNamespace(
        braille_auto_announce_page_changes=True,
        braille_auto_announce_print_page_changes=True,
        braille_auto_announce_line_overflow=True,
    )
    assert movement_cues(None, _snap(page=3, print_page=2, cells=90), every) == []


def test_snapshot_measures_the_caret_line() -> None:
    text = "short\n" + "x" * 45 + "\nend\n"
    doc = BRFDocument.from_text_and_suffix(text, ".brf")
    position = BraillePositionResolver(doc).resolve(8)
    snap = snapshot(text, position)
    assert snap.line_cells == 45
    assert snap.overflowing


def test_print_page_at_uses_the_latest_indicator() -> None:
    indicators = [
        PageChangeIndicator(braille_page=1, detected_print_page=1, confidence="high"),
        PageChangeIndicator(braille_page=3, detected_print_page=2, confidence="high"),
    ]
    assert print_page_at(indicators, 2) == 1
    assert print_page_at(indicators, 3) == 2
    assert print_page_at([], 3) is None


def test_already_said_matches_whole_page_numbers_only() -> None:
    assert already_said("Braille page 5 of 87.", "Braille page 5.")
    assert not already_said("Braille page 50 of 87.", "Braille page 5.")
    assert not already_said("", "Braille page 5.")
