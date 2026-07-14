"""Pure status-string builders for the Braille Mode reader (BR-009).

Produces the spoken / displayed status string at three verbosities
(``brief``, ``normal``, ``detailed``) and dispatches through
:func:`spoken_status` based on the active profile. The module is
deliberately pure: it has no ``wx`` imports, no I/O, and no
announcement side effects. The consumer (the status-bar cell, the
screen-reader bridge, the proofing overlay) calls one of these
functions and decides what to do with the result.

All inputs are plain dataclasses so this module stays trivially
testable. The shape of :class:`BraillePosition` matches
:mod:`quill.core.braille_position`; the other dataclasses are defined
here to keep the public surface self-contained.

Example outputs (per ``docs/planning/planning.md`` under "Feature: Braille Mode"):

* ``brief_status``:
  ``"Page 12. Line 14. Cell 31."``
* ``normal_status``:
  ``"Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7."``
* ``detailed_status``:
  ``"Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7,
  continuation a. Running head: Chapter 2. Last proofed page: 9. Three
  pages marked needs review."``

Variants when the print page is unknown / implied:

* ``"Print page unknown. Braille page 14."``
* ``"Possible implied print page 8."``
"""

from __future__ import annotations

from dataclasses import dataclass

# ``BraillePosition`` is re-exported from ``braille_position`` so callers
# can pass either a real resolver output or one of the local fakes used
# in tests without an import dance.
from quill.core.braille_position import BraillePosition


@dataclass(frozen=True, slots=True)
class ProofingStatus:
    """The proofing state for a braille document.

    Attributes:
        last_proofed_page: 1-based page number of the last page marked
            fully proofed, or ``None`` if no page has been proofed.
        pages_needing_review: number of pages that are not yet proofed.
        total_pages: total number of braille pages in the document.
            Used to spell "all proofed" / "none proofed" without
            recomputing at the call site.
    """

    last_proofed_page: int | None = None
    pages_needing_review: int = 0
    total_pages: int = 0

    @property
    def is_empty(self) -> bool:
        """True when no proofing data is available."""
        return self.last_proofed_page is None and self.pages_needing_review == 0


@dataclass(frozen=True, slots=True)
class ConfidenceLevel:
    """How confident the print-page detector is for the current page.

    ``label`` is one of ``"high"``, ``"medium"``, ``"low"``. ``score`` is
    the raw 0.0-1.0 confidence. The label is the only field used in the
    string output; ``score`` is kept for analytics and tests.
    """

    label: str = "high"
    score: float = 1.0


@dataclass(frozen=True, slots=True)
class PrintPageInfo:
    """The print-page state of the current braille page.

    Attributes:
        number: the detected print page number, ``None`` if unknown.
        is_implied: True when the print page is not explicitly marked
            but inferred from a print-page run (used to phrase the
            "Possible implied print page" branch).
        continuation: the continuation letter (``"a"``, ``"b"`` ...) for
            the current braille page, or ``None`` if there is no
            continuation.
        running_head: the running head text for the current print page,
            or ``None`` if not present.
        confidence: a :class:`ConfidenceLevel`, defaulting to
            ``high`` / 1.0.
    """

    number: int | None = None
    is_implied: bool = False
    continuation: str | None = None
    running_head: str | None = None
    confidence: ConfidenceLevel | None = None

    @property
    def effective_confidence(self) -> ConfidenceLevel:
        if self.confidence is None:
            return ConfidenceLevel()
        return self.confidence


def brief_status(
    position: BraillePosition,
    page_count: int,
    profile: object,
) -> str:
    """Return the brief spoken status: ``"Page 12. Line 14. Cell 31."``

    The verbosity is determined by ``profile``; the call site may pass
    any object that exposes ``braille_status_verbosity`` (the
    :class:`~quill.core.settings.Settings` instance works directly).
    """
    del profile  # verbosity dispatched by spoken_status; this branch is fixed.
    return f"Page {position.page}. Line {position.line}. Cell {position.cell}."


def _line_cell_segment(position: BraillePosition) -> str:
    if position.line_count_in_page > 0:
        lines = f"Line {position.line} of {position.line_count_in_page}"
    else:
        lines = f"Line {position.line}"
    if position.cell_width > 0:
        cells = f"Cell {position.cell} of {position.cell_width}"
    else:
        cells = f"Cell {position.cell}"
    return f"{lines}. {cells}."


def _page_segment(position: BraillePosition) -> str:
    return f"Braille page {position.page} of {position.page_count}."


def _print_page_segment(print_page: PrintPageInfo) -> str:
    """Render the print-page clause, including the unknown / implied variants."""
    if print_page.number is None and not print_page.is_implied:
        return "Print page unknown."
    if print_page.is_implied and print_page.number is not None:
        return f"Possible implied print page {print_page.number}."
    number = print_page.number if print_page.number is not None else 0
    return f"Print page {number}."


def normal_status(
    position: BraillePosition,
    page_count: int,
    print_page: PrintPageInfo,
    profile: object,
) -> str:
    """Return the normal spoken status.

    Example:
        ``"Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7."``
    """
    del page_count
    del profile
    return (
        f"{_page_segment(position)} "
        f"{_line_cell_segment(position)} "
        f"{_print_page_segment(print_page)}"
    )


def _continuation_segment(print_page: PrintPageInfo) -> str:
    if print_page.continuation is None:
        return ""
    return f"continuation {print_page.continuation}"


def _running_head_segment(print_page: PrintPageInfo) -> str:
    if print_page.running_head is None or not print_page.running_head:
        return ""
    return f"Running head: {print_page.running_head}"


def _proofing_segment(proofing: ProofingStatus) -> str:
    if proofing.is_empty:
        return ""
    if proofing.last_proofed_page is None:
        if proofing.pages_needing_review == 0:
            return ""
        return _needs_review_phrase(proofing.pages_needing_review)
    if proofing.pages_needing_review == 0:
        return f"Last proofed page: {proofing.last_proofed_page}. All pages proofed."
    return (
        f"Last proofed page: {proofing.last_proofed_page}. "
        f"{_needs_review_phrase(proofing.pages_needing_review)}"
    )


def _needs_review_phrase(count: int) -> str:
    if count == 1:
        return "One page marked needs review."
    return f"{count} pages marked needs review."


def detailed_status(
    position: BraillePosition,
    page_count: int,
    print_page: PrintPageInfo,
    continuation: str | None,
    running_head: str | None,
    proofing: ProofingStatus,
    confidence: ConfidenceLevel,
    profile: object,
) -> str:
    """Return the full detailed spoken status.

    Includes the continuation letter, running head, last proofed page,
    review queue, and detection confidence. ``continuation`` and
    ``running_head`` may be passed as bare strings for callers that
    have not yet adopted :class:`PrintPageInfo`; they are merged with
    the same-named fields on ``print_page`` (call-site values win).
    """
    del page_count
    del profile
    merged = _merge_print_page(print_page, continuation, running_head)
    prefix = (
        f"{_page_segment(position)} {_line_cell_segment(position)} {_print_page_segment(merged)}"
    )
    tail_parts: list[str] = []
    continuation_clause = _continuation_segment(merged)
    if continuation_clause:
        tail_parts.append(continuation_clause)
    running_head_clause = _running_head_segment(merged)
    if running_head_clause:
        tail_parts.append(running_head_clause)
    proofing_clause = _proofing_segment(proofing)
    if proofing_clause:
        # Normalize "X. Y." phrasing: split into independent clauses.
        clauses = [
            clause.strip().rstrip(".") for clause in proofing_clause.split(". ") if clause.strip()
        ]
        tail_parts.extend(clauses)
    confidence_clause = f"detected with {_confidence_phrase(confidence)} confidence"
    tail_parts.append(confidence_clause)
    body = "; ".join(tail_parts)
    if prefix.endswith("."):
        prefix = prefix[:-1]
    return f"{prefix}. {body}."


def _merge_print_page(
    print_page: PrintPageInfo,
    continuation: str | None,
    running_head: str | None,
) -> PrintPageInfo:
    """Combine bare ``continuation`` / ``running_head`` with ``print_page``.

    Call-site values override the equivalent field on ``print_page`` so
    legacy callers can pass them as separate args without changing the
    shape of the dataclass.
    """
    if continuation is None and running_head is None:
        return print_page
    return PrintPageInfo(
        number=print_page.number,
        is_implied=print_page.is_implied,
        continuation=continuation if continuation is not None else print_page.continuation,
        running_head=running_head if running_head is not None else print_page.running_head,
        confidence=print_page.confidence,
    )


def _confidence_phrase(confidence: ConfidenceLevel) -> str:
    label = (confidence.label or "").strip().lower()
    if label in {"high", "medium", "low"}:
        return label
    return "high"


def spoken_status(
    position: BraillePosition,
    page_count: int,
    print_page: PrintPageInfo,
    profile: object,
    *,
    continuation: str | None = None,
    running_head: str | None = None,
    proofing: ProofingStatus | None = None,
    confidence: ConfidenceLevel | None = None,
) -> str:
    """Dispatch on ``profile.braille_status_verbosity``.

    Falls back to ``"normal"`` for unknown / missing verbosity strings
    so a misconfigured profile never produces a blank status.
    """
    verbosity = _verbosity_of(profile)
    proofing = proofing if proofing is not None else ProofingStatus()
    confidence = confidence if confidence is not None else ConfidenceLevel()
    if verbosity == "brief":
        return brief_status(position, page_count, profile)
    if verbosity == "detailed":
        return detailed_status(
            position,
            page_count,
            print_page,
            continuation,
            running_head,
            proofing,
            confidence,
            profile,
        )
    return normal_status(position, page_count, print_page, profile)


def _verbosity_of(profile: object) -> str:
    value = getattr(profile, "braille_status_verbosity", None)
    if not isinstance(value, str):
        return "normal"
    value = value.strip().lower()
    if value in {"brief", "normal", "detailed"}:
        return value
    return "normal"


__all__ = [
    "BraillePosition",
    "ConfidenceLevel",
    "PrintPageInfo",
    "ProofingStatus",
    "brief_status",
    "detailed_status",
    "normal_status",
    "spoken_status",
]
