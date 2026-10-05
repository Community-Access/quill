"""What the Braille Mode settings decide, as pure functions.

Six settings on **Settings > Braille Mode** were saved and shown and read by
nothing (questions.md item 38). This module is where they now take effect, so
the decision is testable without a frame:

* ``braille_use_form_feeds`` / ``braille_calculate_pages`` choose how the page
  map finds page boundaries (:func:`page_break_mode`).
* ``braille_auto_announce_page_changes``,
  ``braille_auto_announce_print_page_changes`` and
  ``braille_auto_announce_line_overflow`` turn caret movement into short spoken
  cues, said only when something actually changed (:func:`movement_cues`).
* ``braille_include_proofing_status`` gets real data to include from the
  proofing companion file (:func:`proofing_status_from_sidecar`); the switch
  itself is honoured in :func:`quill.core.braille_status.detailed_status`, as
  is ``braille_include_continuation``.

wx-free, strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.braille_position import BraillePosition
from quill.core.braille_status import ProofingStatus
from quill.core.brf_page_detection import PageChangeIndicator
from quill.core.brf_page_map import PageBreakMode
from quill.core.brf_sidecar import BRFSidecar

__all__ = [
    "CaretSnapshot",
    "already_said",
    "line_cell_length",
    "movement_cues",
    "page_break_mode",
    "print_page_at",
    "proofing_status_from_sidecar",
    "snapshot",
]


def _setting(settings: object, name: str, default: bool) -> bool:
    value = getattr(settings, name, default)
    return value if isinstance(value, bool) else default


def page_break_mode(settings: object) -> PageBreakMode:
    """How the page map should find pages, from the two Braille Mode switches.

    Both on (the defaults) is the long-standing hybrid: page-break characters
    when the file has them, otherwise pages worked out from the page size.
    Calculate off means a file with no page breaks is one long page; form
    feeds off means the page size alone decides. Both off would leave nothing
    to find a page with, so it keeps the hybrid rather than inventing a third
    behaviour.
    """
    form_feeds = _setting(settings, "braille_use_form_feeds", True)
    calculate = _setting(settings, "braille_calculate_pages", True)
    if form_feeds and not calculate:
        return "form_feed"
    if calculate and not form_feeds:
        return "calculated"
    return "hybrid"


def print_page_at(indicators: list[PageChangeIndicator], braille_page: int) -> int | None:
    """The print page in force on *braille_page*, or None when none is known."""
    number: int | None = None
    for indicator in indicators:
        if indicator.braille_page > braille_page:
            break
        if indicator.detected_print_page is not None:
            number = indicator.detected_print_page
    return number


def line_cell_length(text: str, position: BraillePosition) -> int:
    """How many cells the caret's line holds, without its line ending."""
    start = position.line_offset
    end = start
    length = len(text)
    while end < length and text[end] not in "\r\n\x0c":
        end += 1
    return end - start


@dataclass(frozen=True, slots=True)
class CaretSnapshot:
    """Where the caret is, in the terms the movement cues compare."""

    page: int
    print_page: int | None
    line_offset: int
    line_cells: int
    cell_width: int

    @property
    def overflowing(self) -> bool:
        return self.cell_width > 0 and self.line_cells > self.cell_width


def snapshot(
    text: str,
    position: BraillePosition,
    print_page: int | None = None,
) -> CaretSnapshot:
    """A :class:`CaretSnapshot` for *position* in *text*."""
    return CaretSnapshot(
        page=position.page,
        print_page=print_page,
        line_offset=position.line_offset,
        line_cells=line_cell_length(text, position),
        cell_width=position.cell_width,
    )


def movement_cues(
    previous: CaretSnapshot | None,
    current: CaretSnapshot,
    settings: object,
) -> list[str]:
    """The short things to say because the caret moved from *previous*.

    Nothing is said for the first position (opening a file is announced on
    its own), and each cue is said once per crossing -- a new page, a new print
    page, a new long line, or a line typed past the limit -- never for every
    arrow key.
    """
    if previous is None:
        return []
    cues: list[str] = []
    if (
        _setting(settings, "braille_auto_announce_page_changes", False)
        and current.page != previous.page
    ):
        cues.append(f"Braille page {current.page}.")
    if (
        _setting(settings, "braille_auto_announce_print_page_changes", False)
        and current.print_page is not None
        and current.print_page != previous.print_page
    ):
        cues.append(f"Print page {current.print_page}.")
    if (
        _setting(settings, "braille_auto_announce_line_overflow", False)
        and current.overflowing
        # Arriving on a long line, or typing a line past the limit -- once.
        and (current.line_offset != previous.line_offset or not previous.overflowing)
    ):
        cues.append(f"Line too long: {current.line_cells} cells, limit {current.cell_width}.")
    return cues


def already_said(last_message: str, cue: str) -> bool:
    """True when *last_message* already told the user what *cue* would.

    Next Braille Page and Go to Braille Page say "Braille page 5 of 87."
    themselves; the cue arriving a moment later would only repeat it.
    """
    stem = cue.rstrip(".")
    return re.match(rf"{re.escape(stem)}(?![0-9])", last_message or "") is not None


def proofing_status_from_sidecar(sidecar: BRFSidecar | None, page_count: int) -> ProofingStatus:
    """The proofing state the detailed status reports, from the companion file."""
    if sidecar is None:
        return ProofingStatus(total_pages=page_count)
    proofing = sidecar.proofing
    last = proofing.last_proofed_braille_page
    return ProofingStatus(
        last_proofed_page=last if last > 0 else None,
        pages_needing_review=len(set(proofing.pages_needing_review)),
        total_pages=page_count,
    )
