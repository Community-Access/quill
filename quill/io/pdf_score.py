"""How readable a page of extracted PDF text is: a bounded 0-100 score.

The PDF reader asks several extractors for the same page and keeps the one a
listener would rather hear (:mod:`quill.io.pdf_select`). It needs a score that
measures *readability*, not quantity: the old score rewarded characters, words
and pages, so a page of replacement characters scored 100 and a short, perfectly
clean title page scored 25.

The score starts at 100 and is multiplied by one factor per kind of damage,
each factor between 0 and 1, so it can never leave 0-100 and no single quirk can
push a clean page below another kind of damage. The factors, with the
constants below:

* **suspicious** -- replacement characters (U+FFFD), private-use codepoints,
  control characters and pdfminer's ``(cid:123)`` placeholders, as a share of
  the visible characters. ``max(0, 1 - 4 x share)``: a quarter junk scores 0.
* **fragmented** -- runs of three or more single Latin letters ("H e l l o"),
  as a share of the words. ``max(0, 1 - 1.5 x share)``.
* **one word per line** -- only on six or more lines, and only when more than
  half the lines are a single alphabetic word. Never below 0.4.
* **implausible joins** -- Latin words of 20 or more letters with no hyphen,
  "wordWord" and "word.Word" seams, and doubled letters ("HHeelllloo") from
  fake-bold printing, beyond a 3 percent allowance for real long words and
  product names. Never below 0.2.
* **coverage** -- this reading's letters and digits against the fullest reading
  of the same page, so a clean reading that lost half the page cannot beat one
  that kept it. ``min(1, coverage / 0.95)``.
* **column order** -- only when the page visibly has two columns: the share of
  column rows this reading ran together side by side. ``1 - 0.5 x share``.

Short text, numbers and non-Latin scripts are not penalized for being short or
non-alphabetic: a one-line title, a column of figures and a page of Greek or
Japanese all score 100 when nothing is wrong with them. Empty text scores 0.

The measured thresholds (fast path, doubtful page) and the latency budget are
in ``docs/design/2026-10-16-pdf-text-reliability.md``.

Pure text in, numbers out: no wx, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "DOUBTFUL_PAGE_SCORE",
    "FAST_PATH_SCORE",
    "SCORE_VERSION",
    "Readability",
    "content_chars",
    "readability",
    "score_text",
    "unreadable_count",
]

#: Bumped when the formula changes, so a stored score can be told from a new one.
SCORE_VERSION = 1

#: A first reading at or above this, on a page with no sign of columns, is kept
#: without asking the other extractors. Measured on the corpus: every clean page
#: scores 100 and every damaged one scores 78 or less (see the design note).
FAST_PATH_SCORE = 90

#: Below this a page is reported as doubtful: "may read poorly".
DOUBTFUL_PAGE_SCORE = 40

_CID = re.compile(r"\(cid:\d+\)")
_EDGE_PUNCTUATION = "\"'()[]{}<>.,;:!?‘’“”…*"
_CAMEL_JOIN = re.compile(r"[a-z]{2,}[A-Z][a-z]{2,}")
_DOT_JOIN = re.compile(r"[a-z]{2,}[.,;:][A-Z][a-z]")
_LONG_WORD = 20
_JOIN_ALLOWANCE = 0.03
_MIN_LINES_FOR_LINE_SHAPE = 6


@dataclass(frozen=True, slots=True)
class Readability:
    """A page's score and the factors that made it, for tests and the report."""

    score: int
    suspicious: float = 1.0
    fragmented: float = 1.0
    one_word_lines: float = 1.0
    joins: float = 1.0
    coverage: float = 1.0
    column_order: float = 1.0


# Replacement character, private use (BMP and planes 15-16), and control
# characters other than tab, newline, carriage return and form feed.
_SUSPICIOUS = re.compile(
    r"[\ufffd\ue000-\uf8ff\U000f0000-\U0010ffff\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]"
)
_ALNUM = re.compile(r"[^\W_]")
_HAS_LETTER = re.compile(r"[^\W\d_]")
# A word whose letters are all Latin, Greek, Cyrillic or Armenian (below U+0530).
_NON_LATIN_LETTER = re.compile(r"[^\W\d_\u0000-\u052f]")


def content_chars(text: str) -> int:
    """Letters and digits a listener would hear, placeholders and junk excluded."""
    return len(_ALNUM.findall(_CID.sub("", text)))


def unreadable_count(text: str) -> int:
    """Characters on the page that could not be read as text.

    Replacement characters, private-use glyphs, stray control characters, and
    each pdfminer ``(cid:N)`` placeholder. A screen reader says nothing useful
    for any of them, so the reader reports the page instead of hiding them.
    """
    return len(_CID.findall(text)) + len(_SUSPICIOUS.findall(_CID.sub("", text)))


def _suspicious_share(text: str) -> float:
    visible = sum(len(token) for token in text.split())
    if not visible:
        return 0.0
    placeholder = sum(len(match) for match in _CID.findall(text))
    junk = len(_SUSPICIOUS.findall(_CID.sub("", text)))
    return min(1.0, (junk + placeholder) / visible)


def _words(text: str) -> list[str]:
    return [token.strip(_EDGE_PUNCTUATION) for token in text.split()]


def _single_latin_letter(word: str) -> bool:
    return len(word) == 1 and word.isalpha() and ord(word) < 0x0530


def _fragmented_share(words: Sequence[str]) -> float:
    alphabetic = [word for word in words if _HAS_LETTER.search(word)]
    if not alphabetic:
        return 0.0
    in_runs = 0
    run = 0
    for word in alphabetic:
        if _single_latin_letter(word):
            run += 1
            continue
        if run >= 3:
            in_runs += run
        run = 0
    if run >= 3:
        in_runs += run
    return in_runs / len(alphabetic)


def _doubled(word: str) -> bool:
    return len(word) >= 4 and len(word) % 2 == 0 and word.isalpha() and word[0::2] == word[1::2]


def _join_share(words: Sequence[str]) -> float:
    counted = 0
    implausible = 0
    for word in words:
        if not word or not _HAS_LETTER.search(word):
            continue  # a number, a date, an identifier
        if not word.isascii() and _NON_LATIN_LETTER.search(word):
            continue  # another script: its word lengths are not ours to judge
        counted += 1
        alphabetic = word.isalpha()
        if (alphabetic and (len(word) >= _LONG_WORD or _doubled(word))) or (
            _CAMEL_JOIN.search(word) or _DOT_JOIN.search(word)
        ):
            implausible += 1
    if not counted:
        return 0.0
    return min(1.0, implausible / counted)


def _one_word_line_share(text: str) -> float:
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if len(lines) < _MIN_LINES_FOR_LINE_SHAPE:
        return 0.0
    single = sum(1 for tokens in lines if len(tokens) == 1 and _HAS_LETTER.search(tokens[0]))
    return single / len(lines)


def _collapsed(text: str) -> str:
    return " ".join(text.split())


def readability(
    text: str,
    *,
    reference_chars: int | None = None,
    column_rows: Sequence[tuple[str, str]] = (),
) -> Readability:
    """Score *text*; see the module docstring for every factor.

    ``reference_chars`` is the content of the fullest reading of the same page
    (:func:`content_chars`), for the coverage factor; ``column_rows`` are the
    ``(left, right)`` halves of the page's two-column rows, when it has them.
    """
    if not text.strip():
        return Readability(score=0)
    suspicious = max(0.0, 1.0 - 4.0 * _suspicious_share(text))
    words = _words(text)
    fragmented = max(0.0, 1.0 - 1.5 * _fragmented_share(words))
    line_share = _one_word_line_share(text)
    one_word_lines = 1.0 - min(0.6, max(0.0, line_share - 0.5) * 1.2)
    joins = max(0.2, 1.0 - 4.0 * max(0.0, _join_share(words) - _JOIN_ALLOWANCE))
    coverage = 1.0
    if reference_chars:
        coverage = min(1.0, content_chars(text) / reference_chars / 0.95)
    column_order = 1.0
    if column_rows:
        flat = _collapsed(text)
        run_together = sum(1 for left, right in column_rows if f"{left} {right}" in flat)
        column_order = 1.0 - 0.5 * run_together / len(column_rows)
    product = suspicious * fragmented * one_word_lines * joins * coverage * column_order
    return Readability(
        score=max(0, min(100, round(100 * product))),
        suspicious=suspicious,
        fragmented=fragmented,
        one_word_lines=one_word_lines,
        joins=joins,
        coverage=coverage,
        column_order=column_order,
    )


def score_text(text: str, *, reference_chars: int | None = None) -> int:
    """Just the 0-100 number."""
    return readability(text, reference_chars=reference_chars).score
