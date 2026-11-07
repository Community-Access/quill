"""Sentences, syllables and the Flesch-Kincaid grade, for any plain text.

Shared by Document Statistics in both editors (:mod:`quill.core.metrics`) and
the WordPress reading-level line (:mod:`quill.core.wordpress.readability`,
which strips the HTML first and then counts with these). No AI, no network,
stdlib only.
"""

from __future__ import annotations

import re

__all__ = [
    "SENTENCE_END_RE",
    "WORD_RE",
    "count_syllables",
    "flesch_kincaid_grade",
    "grade_phrase",
    "split_sentences",
]

WORD_RE = re.compile(r"[A-Za-zÀ-ɏ]+(?:['’][A-Za-z]+)*|\d+(?:[.,]\d+)*")
# A sentence ends at terminal punctuation (with any closing quote or bracket)
# followed by space, or at a line break left by a block boundary.
SENTENCE_END_RE = re.compile(r"[.!?…]+[\"'”’)\]]*(?=\s|$)|\n+")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def count_syllables(word: str) -> int:
    """A vowel-group estimate of a word's syllables (at least 1)."""
    w = word.lower().strip("'’")
    if not w:
        return 0
    if w.isdigit():
        return max(1, len(w))  # numbers are read digit-ish; a rough cost
    if len(w) <= 3:
        return 1
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")):
        w = w[:-1]
    elif w.endswith(("es", "ed")) and not w.endswith((
        "ted",
        "ded",
        "ses",
        "zes",
        "ces",
        "ges",
        "xes",
        "shes",
        "ches",
    )):
        w = w[:-2]
    groups = len(_VOWEL_GROUP_RE.findall(w))
    return max(1, groups)


def split_sentences(text: str) -> list[tuple[str, int]]:
    """``(sentence, offset)`` pairs, stripped, skipping pieces with no word.

    A line break ends a sentence too, so a heading or a list item counts as
    one rather than running into the paragraph after it.
    """
    pieces: list[tuple[str, int]] = []
    start = 0
    for match in SENTENCE_END_RE.finditer(text):
        end = match.end()
        pieces.append((text[start:end], start))
        start = end
    pieces.append((text[start:], start))
    result: list[tuple[str, int]] = []
    for piece, offset in pieces:
        stripped = piece.strip()
        if not stripped or not WORD_RE.search(stripped):
            continue
        lead = len(piece) - len(piece.lstrip())
        result.append((stripped, offset + lead))
    return result


def flesch_kincaid_grade(words: int, sentences: int, syllables: int) -> float:
    """The Flesch-Kincaid grade level; 0.0 when there is nothing to judge."""
    if words <= 0 or sentences <= 0:
        return 0.0
    return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def grade_phrase(grade: float) -> str:
    """``"about 9th grade"``, or ``"college level"`` from grade 13 up."""
    rounded = round(grade)
    if rounded >= 13:
        return "college level"
    return f"about {_ordinal(max(1, rounded))} grade"
