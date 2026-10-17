"""Choosing each page's text from several readings of it (extraction phase 1).

A PDF stores glyphs and positions, and every extractor turns them back into
text by its own rules. On most pages the rules agree and the first reading is
fine; on some they disagree badly -- one extractor spells a widely spaced line
out letter by letter while another reads it whole, or one runs two columns
together row by row while another follows them down the page. The old reader
kept the first reading that was not empty, so a bad first answer hid a good
second one.

This module holds the decision, kept apart from the I/O in :mod:`quill.io.pdf`
so it can be tested with plain strings:

* :func:`fast_choice` -- a first reading that already scores at or above
  :data:`~quill.io.pdf_score.FAST_PATH_SCORE` is kept as it is, so a clean page
  pays for one extractor, not three.
* :func:`choose_page` -- otherwise every reading is repaired
  (:func:`quill.io.pdf_repair.repair_extracted_text`), scored before *and*
  after the repair (:mod:`quill.io.pdf_score`), and the best one wins; a tie
  goes to the earlier engine in :data:`ROSTER`. A repair that would lower a
  reading's score is not applied to it.
* :func:`column_rows` and :func:`column_ordered` -- the evidence that a page
  has two columns, read from pypdf's layout mode (which keeps the gap between
  them as spaces), and a reading that follows each column down the page.

Readable text only: nothing here makes headings, table cells or any other
structure.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from quill.io.pdf_repair import repair_extracted_text
from quill.io.pdf_score import FAST_PATH_SCORE, content_chars, readability

__all__ = [
    "ENGINE_COLUMNS",
    "ENGINE_MARKITDOWN",
    "ENGINE_PDFPLUMBER",
    "ENGINE_PDFPLUMBER_DEDUPE",
    "ENGINE_PYPDF",
    "ENGINE_PYPDF_LAYOUT",
    "PAGE_BLANK",
    "PAGE_FAILED",
    "PAGE_IMAGE_ONLY",
    "ROSTER",
    "Candidate",
    "PageChoice",
    "choose_page",
    "column_ordered",
    "column_rows",
    "fast_choice",
    "has_doubled_letters",
    "tidy_layout",
]

#: pdfplumber's ordinary reading (pdfminer underneath): the first one tried.
ENGINE_PDFPLUMBER = "pdfplumber"
#: pdfplumber again with overprinted duplicate characters removed (fake bold).
ENGINE_PDFPLUMBER_DEDUPE = "pdfplumber-dedupe"
#: pypdf's plain reading, which follows the order the page was drawn in.
ENGINE_PYPDF = "pypdf"
#: pypdf's layout reading, which keeps horizontal gaps as spaces.
ENGINE_PYPDF_LAYOUT = "pypdf-layout"
#: pypdf's layout reading, split at the column gap and read column by column.
ENGINE_COLUMNS = "pypdf-columns"
#: MarkItDown's reading, used only page by page when it scores clearly better.
ENGINE_MARKITDOWN = "markitdown"

#: Every reading, in tie-break order.
ROSTER = (
    ENGINE_PDFPLUMBER,
    ENGINE_PDFPLUMBER_DEDUPE,
    ENGINE_PYPDF,
    ENGINE_PYPDF_LAYOUT,
    ENGINE_COLUMNS,
    ENGINE_MARKITDOWN,
)

#: A page with nothing on it at all.
PAGE_BLANK = "blank"
#: A page with a picture and no text: perhaps a scan, worth OCR.
PAGE_IMAGE_ONLY = "image-only"
#: Every extractor failed on this page.
PAGE_FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Candidate:
    """One extractor's reading of one page, before any repair."""

    engine: str
    raw: str


@dataclass(frozen=True, slots=True)
class PageChoice:
    """The reading kept for a page, and how it scored."""

    engine: str
    text: str
    score: int
    #: The kept reading's score before repair.
    raw_score: int
    #: How many readings were compared (1 on the fast path).
    compared: int = 1


def _settle(
    raw: str,
    fixed: str,
    *,
    reference: int | None,
    rows: Sequence[tuple[str, str]],
    before: int | None = None,
) -> tuple[str, int, int]:
    """``(text, score, raw_score)``: the repaired text unless repair scored worse."""
    if before is None:
        before = readability(raw, reference_chars=reference, column_rows=rows).score
    if fixed == raw:
        return raw, before, before
    after = readability(fixed, reference_chars=reference, column_rows=rows).score
    if after >= before:
        return fixed, after, before
    return raw, before, before


def fast_choice(engine: str, raw: str) -> PageChoice | None:
    """Keep a first reading that is already clean; ``None`` when it is doubtful."""
    if not raw.strip():
        return None
    raw = raw.strip()
    first = readability(raw).score
    if first < FAST_PATH_SCORE:
        return None
    text, score, raw_score = _settle(
        raw, repair_extracted_text(raw), reference=None, rows=(), before=first
    )
    return PageChoice(engine=engine, text=text, score=score, raw_score=raw_score)


def choose_page(
    candidates: Sequence[Candidate], *, rows: Sequence[tuple[str, str]] = ()
) -> PageChoice | None:
    """The best of *candidates* by readability; ``None`` when all are empty.

    Coverage is measured against the fullest reading of the page, so a reading
    that is clean because it lost half the page does not win.
    """
    present = [candidate for candidate in candidates if candidate.raw.strip()]
    if not present:
        return None
    readings = [
        (candidate, raw, repair_extracted_text(raw))
        for candidate in sorted(present, key=_roster_index)
        for raw in (candidate.raw.strip(),)
    ]
    fullest = max(max(content_chars(raw), content_chars(fixed)) for _, raw, fixed in readings)
    reference: int | None = fullest or None
    best: PageChoice | None = None
    for candidate, raw, fixed in readings:
        text, score, raw_score = _settle(raw, fixed, reference=reference, rows=rows)
        if best is None or score > best.score:
            best = PageChoice(
                engine=candidate.engine,
                text=text,
                score=score,
                raw_score=raw_score,
                compared=len(present),
            )
    return best


def _roster_index(candidate: Candidate) -> int:
    try:
        return ROSTER.index(candidate.engine)
    except ValueError:
        return len(ROSTER)


def has_doubled_letters(text: str) -> bool:
    """Whether a reading shows fake-bold doubling ("HHeelllloo")."""
    for token in text.split()[:400]:
        if len(token) >= 6 and len(token) % 2 == 0 and token.isalpha():
            if token[0::2] == token[1::2]:
                return True
    return False


# -- layout readings ------------------------------------------------------------ #

_SPACE_RUN = re.compile(r" {3,}")
_GAP = re.compile(r"(?<=\S) {4,}(?=\S)")


def tidy_layout(text: str) -> str:
    """pypdf's layout reading, made listenable without changing any word.

    Leading indentation and trailing spaces go, runs of blank lines become one,
    and a wide horizontal gap becomes exactly three spaces -- enough for the
    repair step to see a column-spaced row and leave it alone.
    """
    lines: list[str] = []
    for line in text.splitlines():
        cleaned = _SPACE_RUN.sub("   ", line.strip())
        if not cleaned and (not lines or not lines[-1]):
            continue
        lines.append(cleaned)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _prose(segment: str) -> bool:
    """A run of words that reads as a sentence fragment, not a table cell."""
    if "    " in segment:
        return False  # a second gap inside: a row of cells
    words = segment.split()
    alphabetic = [word for word in words if sum(c.isalpha() for c in word) >= 2]
    return len(words) >= 3 and len(alphabetic) >= 0.6 * len(words) and len(segment) >= 15


def _gutter(lines: Sequence[str]) -> int | None:
    """The character column most two-column rows have their gap across."""
    covering: Counter[int] = Counter()
    for line in lines:
        for gap in _GAP.finditer(line):
            covering.update(range(gap.start(), gap.end()))
    if not covering:
        return None
    position, count = covering.most_common(1)[0]
    reaching = sum(1 for line in lines if len(line) > position)
    if count < 3 or count < 0.5 * reaching:
        return None
    return position


def column_rows(layout: str) -> tuple[int | None, list[tuple[str, str]]]:
    """``(gutter, rows)`` for a two-column page; ``(None, [])`` otherwise.

    *layout* is pypdf's layout reading, untidied. A row is a line with prose on
    both sides of the gutter; three or more of them, making up at least half of
    the lines that reach the gutter, mean two columns. A table's rows do not
    qualify: their cells are short and their right half has gaps of its own.
    """
    lines = [line.rstrip() for line in layout.splitlines() if line.strip()]
    if len(lines) < 3:
        return None, []
    position = _gutter(lines)
    if position is None:
        return None, []
    rows: list[tuple[str, str]] = []
    for line in lines:
        gap = next((g for g in _GAP.finditer(line) if g.start() <= position < g.end()), None)
        if gap is None:
            continue
        left, right = line[: gap.start()].strip(), line[gap.end() :].strip()
        if _prose(left) and _prose(right):
            rows.append((" ".join(left.split()), " ".join(right.split())))
    reaching = sum(1 for line in lines if len(line) > position)
    if len(rows) < 3 or len(rows) < 0.5 * reaching:
        return None, []
    return position, rows


def column_ordered(layout: str, gutter: int) -> str:
    """The layout reading with each column read down the page in turn.

    A line wholly left or right of the gutter joins that column; a line that
    spans it (a title across both columns) ends the columns above it, which are
    written out left then right, and then stands on its own.
    """
    out: list[str] = []
    left: list[str] = []
    right: list[str] = []

    def flush() -> None:
        out.extend(left)
        out.extend(right)
        left.clear()
        right.clear()

    for line in layout.splitlines():
        if not line.strip():
            continue
        gap = next((g for g in _GAP.finditer(line) if g.start() <= gutter < g.end()), None)
        start = len(line) - len(line.lstrip())
        if gap is not None:
            left.append(line[: gap.start()].strip())
            right.append(line[gap.end() :].strip())
        elif len(line.rstrip()) <= gutter:
            left.append(line.strip())
        elif start >= gutter:
            right.append(line.strip())
        else:
            flush()
            out.append(line.strip())
    flush()
    return "\n".join(_SPACE_RUN.sub("   ", line) for line in out)
