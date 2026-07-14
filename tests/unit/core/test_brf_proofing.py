from __future__ import annotations

from quill.core import brf_proofing
from quill.core.brf_sidecar import BRFSidecar


def test_mark_proofed_adds_and_dedupes_and_bumps_last() -> None:
    s = BRFSidecar()
    assert brf_proofing.mark_proofed(s, 12) == "Braille page 12 marked proofed."
    brf_proofing.mark_proofed(s, 3)
    brf_proofing.mark_proofed(s, 12)  # duplicate
    assert s.proofing.proofed_pages == [3, 12]
    assert s.proofing.last_proofed_braille_page == 12


def test_mark_needs_review_removes_proofed_mark() -> None:
    s = BRFSidecar()
    brf_proofing.mark_proofed(s, 5)
    msg = brf_proofing.mark_needs_review(s, 5)
    assert msg == "Braille page 5 marked needs review."
    assert s.proofing.proofed_pages == []
    assert s.proofing.pages_needing_review == [5]


def test_mark_proofed_removes_needs_review_mark() -> None:
    s = BRFSidecar()
    brf_proofing.mark_needs_review(s, 7)
    brf_proofing.mark_proofed(s, 7)
    assert s.proofing.pages_needing_review == []
    assert s.proofing.proofed_pages == [7]


def test_clear_proofing_mark() -> None:
    s = BRFSidecar()
    brf_proofing.mark_proofed(s, 4)
    assert brf_proofing.clear_proofing_mark(s, 4) == "Cleared proofing mark on braille page 4."
    assert s.proofing.proofed_pages == []
    assert brf_proofing.clear_proofing_mark(s, 4) == "Braille page 4 had no proofing mark."


def test_add_note_and_ignore_blank() -> None:
    s = BRFSidecar()
    assert brf_proofing.add_note(s, 12, "  check stanza  ") == "Note added to braille page 12."
    assert s.notes[0].braille_page == 12
    assert s.notes[0].text == "check stanza"
    assert brf_proofing.add_note(s, 12, "   ") == "No note added."
    assert len(s.notes) == 1


def test_progress_summary() -> None:
    s = BRFSidecar()
    for p in (1, 2, 3, 9):
        brf_proofing.mark_proofed(s, p)
    brf_proofing.mark_needs_review(s, 5)
    brf_proofing.mark_needs_review(s, 6)
    brf_proofing.mark_needs_review(s, 7)
    msg = brf_proofing.progress_summary(s, page_count=87, current_page=12, print_page="7")
    assert msg == (
        "Progress summary. 87 braille pages. Current page 12. 4 pages proofed. "
        "3 pages need review. Last proofed page 9. Current print page 7. "
        "Estimated completion 5 percent."
    )


def test_progress_summary_singular_review() -> None:
    s = BRFSidecar()
    brf_proofing.mark_needs_review(s, 2)
    msg = brf_proofing.progress_summary(s, page_count=10, current_page=2)
    assert "1 page needs review." in msg
    assert "print page" not in msg.lower()


def test_export_report_contains_counts_and_notes() -> None:
    s = BRFSidecar()
    brf_proofing.mark_proofed(s, 1)
    brf_proofing.mark_proofed(s, 2)
    brf_proofing.mark_needs_review(s, 5)
    brf_proofing.add_note(s, 2, "fixed running head")
    report = brf_proofing.export_report(s, document_name="notes.brf", page_count=20)
    assert "Proofing report for notes.brf" in report
    assert "Proofed pages (2): 1, 2" in report
    assert "Pages needing review (1): 5" in report
    assert "Estimated completion: 10 percent" in report
    assert "Braille page 2: fixed running head" in report


def test_list_helpers_sort_and_dedupe() -> None:
    s = BRFSidecar()
    s.proofing.proofed_pages = [3, 1, 3, 2]
    s.proofing.pages_needing_review = [9, 9, 4]
    assert brf_proofing.proofed_pages(s) == [1, 2, 3]
    assert brf_proofing.pages_needing_review(s) == [4, 9]
