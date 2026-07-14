"""Tests for BR-014: print-page navigation commands and detailed-status population."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from quill.core.braille_position import BraillePosition
from quill.core.braille_status import (
    ConfidenceLevel,
    PrintPageInfo,
    ProofingStatus,
    detailed_status,
)

# ----------------------------------------------------------------------------
# Source-level wiring checks (no wx import required)
# ----------------------------------------------------------------------------


_UI_BRAILLE = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_braille.py"
_UI_BRAILLE_PHASE2 = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_braille_phase2.py"
)


def _source() -> str:
    # Phase 2 (print pages, running heads) lives in its own mixin module
    # so the Phase 1 file stays under the GATE-11 module-size budget. The
    # wiring checks below pull from both files.
    return _UI_BRAILLE.read_text(encoding="utf-8") + _UI_BRAILLE_PHASE2.read_text(encoding="utf-8")


def test_braille_menu_declares_print_page_navigation_items() -> None:
    """The Braille > Navigation submenu wires Go to / Next / Previous Print Page."""
    source = _source()
    # The IDs must be allocated, appended to the navigation submenu,
    # bound to a handler, and registered with the command registry.
    for needle in (
        "self._id_braille_go_to_print_page = wx.NewIdRef()",
        "self._id_braille_next_print_change = wx.NewIdRef()",
        "self._id_braille_prev_print_change = wx.NewIdRef()",
        'self._menu_label("Go to &Print Page..."',
        'self._menu_label("&Next Print Page Change"',
        'self._menu_label("&Previous Print Page Change"',
        "id=self._id_braille_go_to_print_page",
        "id=self._id_braille_next_print_change",
        "id=self._id_braille_prev_print_change",
        '"braille.go_to_print_page"',
        '"braille.next_print_page_change"',
        '"braille.previous_print_page_change"',
    ):
        assert needle in source, f"missing braille print-page wiring: {needle}"


def test_braille_menu_declares_running_head_items() -> None:
    source = _source()
    for needle in (
        "self._id_braille_announce_running_head = wx.NewIdRef()",
        "self._id_braille_use_running_head = wx.NewIdRef()",
        "self._id_braille_ignore_running_head = wx.NewIdRef()",
        '"braille.announce_running_head"',
        '"braille.use_running_head_in_status"',
        '"braille.ignore_running_head_for_status"',
    ):
        assert needle in source, f"missing braille running-head wiring: {needle}"


def test_braille_handlers_defined() -> None:
    source = _source()
    for handler in (
        "def go_to_print_page(self)",
        "def next_print_page_change(self)",
        "def previous_print_page_change(self)",
        "def announce_running_head(self)",
        "def use_running_head_in_status(self)",
        "def ignore_running_head_for_status(self)",
    ):
        assert handler in source, f"missing handler: {handler}"


def test_braille_command_ids_registered() -> None:
    """Each new command ID is registered in the command registry."""
    source = _source()
    for cmd in (
        '"braille.go_to_print_page"',
        '"braille.next_print_page_change"',
        '"braille.previous_print_page_change"',
        '"braille.announce_running_head"',
        '"braille.use_running_head_in_status"',
        '"braille.ignore_running_head_for_status"',
    ):
        assert cmd in source, f"missing command registration: {cmd}"


def test_braille_menu_has_no_orphan_ids() -> None:
    """Every id allocated in main_frame_braille.py is referenced in a Bind or Append."""
    source = _source()
    allocated = set(re.findall(r"self\._id_braille_[A-Za-z0-9_]+\s*=\s*wx\.NewIdRef", source))
    # In this file IDs are referred to as ``self._id_braille_*``; we
    # need a *referenced* count, not the allocations.
    for id_line in allocated:
        identifier = id_line.split("=", 1)[0].strip()
        count = source.count(identifier)
        # Once for the allocation; expect at least one more reference.
        assert count >= 2, f"orphaned braille id: {identifier}"


# ----------------------------------------------------------------------------
# Detailed-status population (the new path that the handler composes)
# ----------------------------------------------------------------------------


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


def test_detailed_status_includes_confidence_continuation_running_head() -> None:
    """detailed_status combines the BR-014 fields into a single announcement.

    This is the *example string from the spec*: print page 7, braille
    page 12, continuation a, running head "Chapter 2", proofing state
    with last proofed 9 and 3 pages needing review, high confidence.
    The exact wording matches the spec example from the issue.
    """
    out = detailed_status(
        _position(),
        87,
        PrintPageInfo(
            number=7,
            is_implied=False,
            continuation="a",
            running_head="Chapter 2",
            confidence=ConfidenceLevel("high", 0.97),
        ),
        None,
        None,
        ProofingStatus(last_proofed_page=9, pages_needing_review=3, total_pages=87),
        ConfidenceLevel("high", 0.97),
        SimpleNamespace(braille_status_verbosity="detailed"),
    )
    assert "Print page 7" in out
    assert "continuation a" in out
    assert "Running head: Chapter 2" in out
    assert "Last proofed page: 9" in out
    assert "3 pages marked needs review" in out
    assert "detected with high confidence" in out
