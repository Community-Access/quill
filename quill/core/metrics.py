from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from quill.core.readability import (
    WORD_RE,
    count_syllables,
    flesch_kincaid_grade,
    grade_phrase,
    split_sentences,
)

#: The reading speed both editors assume: the status bar's reading-time cell
#: and the spoken Document Statistics report use the same figure.
READING_WORDS_PER_MINUTE = 200

#: A sentence longer than this many words is counted as long.
LONG_SENTENCE_WORDS = 30

#: How quickly a second press of Document Statistics must follow the first
#: when the editor has no setting of its own (QUILL uses multi_press_window_ms).
DEFAULT_REPEAT_WINDOW_MS = 400


@dataclass(frozen=True, slots=True)
class DocumentStats:
    characters: int
    words: int
    lines: int


@dataclass(frozen=True, slots=True)
class WritingStats:
    """Document Statistics in full: the three counts plus the writing ones."""

    characters: int
    words: int
    lines: int
    paragraphs: int
    sentences: int
    long_sentences: int
    reading_minutes: int
    #: Flesch-Kincaid grade, or None when there is no text to judge.
    grade: float | None


def compute_document_stats(text: str) -> DocumentStats:
    words = [token for token in text.split() if token]
    lines = 0 if text == "" else text.count("\n") + 1
    return DocumentStats(
        characters=len(text),
        words=len(words),
        lines=lines,
    )


def reading_minutes(words: int) -> int:
    """Whole minutes to read ``words``, rounded up; 0 for no words."""
    if words <= 0:
        return 0
    return (words + READING_WORDS_PER_MINUTE - 1) // READING_WORDS_PER_MINUTE


def count_paragraphs(text: str) -> int:
    """Paragraphs in plain text.

    When the text separates its paragraphs with blank lines (Markdown, and
    anything hard-wrapped), a paragraph is a run of non-blank lines. When it
    never does, each non-blank line is a paragraph, which is how a word
    processor counts a document typed with one Enter between paragraphs.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = 0
    in_block = False
    blank_between = False
    for line in lines:
        if line.strip():
            if not in_block:
                if blocks:
                    blank_between = True
                blocks += 1
                in_block = True
        else:
            in_block = False
    if blank_between:
        return blocks
    return sum(1 for line in lines if line.strip())


def compute_writing_stats(text: str) -> WritingStats:
    """Everything Document Statistics reports, for ``text``."""
    basic = compute_document_stats(text)
    sentences = split_sentences(text.replace("\r\n", "\n"))
    fk_words = 0
    syllables = 0
    long_count = 0
    for sentence, _offset in sentences:
        found = WORD_RE.findall(sentence)
        fk_words += len(found)
        syllables += sum(count_syllables(w) for w in found)
        if len(found) > LONG_SENTENCE_WORDS:
            long_count += 1
    grade = flesch_kincaid_grade(fk_words, len(sentences), syllables) if fk_words else None
    return WritingStats(
        characters=basic.characters,
        words=basic.words,
        lines=basic.lines,
        paragraphs=count_paragraphs(text),
        sentences=len(sentences),
        long_sentences=long_count,
        reading_minutes=reading_minutes(basic.words),
        grade=grade,
    )


def _plural(n: int, one: str, many: str) -> str:
    return f"{n:,} {one if n == 1 else many}"


def describe_counts(stats: DocumentStats | WritingStats, *, selection: bool = False) -> str:
    """The first-press sentence: words, lines and characters."""
    lead = "Selection: " if selection else ""
    return (
        f"{lead}{_plural(stats.words, 'word', 'words')}, "
        f"{_plural(stats.lines, 'line', 'lines')}, "
        f"{_plural(stats.characters, 'character', 'characters')}"
    )


def describe_writing_stats(stats: WritingStats, *, selection: bool = False) -> str:
    """The second-press report, every number in one spoken sentence."""
    if stats.words == 0:
        reading = "no reading time"
    elif stats.words < READING_WORDS_PER_MINUTE:
        reading = "under a minute to read"
    else:
        reading = f"about {_plural(stats.reading_minutes, 'minute', 'minutes')} to read"
    if stats.grade is None:
        grade = "no reading grade, not enough text"
    else:
        grade = f"reading grade {grade_phrase(stats.grade)}"
    long_part = _plural(stats.long_sentences, "long sentence", "long sentences")
    return (
        f"{describe_counts(stats, selection=selection)}, "
        f"{_plural(stats.paragraphs, 'paragraph', 'paragraphs')}, "
        f"{_plural(stats.sentences, 'sentence', 'sentences')}, "
        f"{long_part} over {LONG_SENTENCE_WORDS} words, "
        f"{reading}, {grade}"
    )


def statistics_report(text: str, selected: str = "", *, detailed: bool = False) -> str:
    """What Document Statistics says, in both editors.

    The selection when there is one (said as "Selection: ..."), else the whole
    text; the counts on a first press, the full writing report on a second.
    """
    subject = selected if selected else text
    is_selection = bool(selected)
    if detailed:
        return describe_writing_stats(compute_writing_stats(subject), selection=is_selection)
    return describe_counts(compute_document_stats(subject), selection=is_selection)


class RepeatPress:
    """Tells a first press from a quick second press, without delaying either.

    The first press answers at once; a press within ``window_ms`` of the one
    before counts as the second. The press after a second press is a first
    press again, so pressing on alternates the short answer and the long one.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._last: float | None = None

    def press(self, window_ms: int) -> int:
        """Record a press; return 1 for a first press, 2 for a quick repeat."""
        now = self._clock()
        last = self._last
        if last is not None and (now - last) * 1000 <= window_ms:
            self._last = None
            return 2
        self._last = now
        return 1
