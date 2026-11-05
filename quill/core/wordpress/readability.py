"""A local reading-level line for a WordPress post (wordpress.md 9.11).

"Reading level: about 9th grade, 14 words per sentence" -- the Flesch-Kincaid
grade, worked out here with a vowel-group syllable count, plus the longest
sentences with their offsets so Properties can offer Go to It on each. No AI,
no network, stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

__all__ = [
    "PlainText",
    "ReadingLevel",
    "Sentence",
    "count_syllables",
    "describe",
    "reading_level",
    "strip_html",
]

#: How many of the longest sentences a ReadingLevel carries.
LONGEST_COUNT = 3

_BLOCK_TAGS = frozenset({
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
})
_SKIP_TAGS = frozenset({"script", "style", "template", "noscript"})


@dataclass(frozen=True)
class PlainText:
    """Text with tags removed, and where each character came from.

    ``source_offsets[i]`` is the offset in the original HTML of ``text[i]``
    (for an inserted break, the offset of the tag that caused it).
    """

    text: str
    source_offsets: tuple[int, ...]

    def source_offset(self, index: int) -> int:
        """The HTML offset for plain-text position ``index`` (clamped)."""
        if not self.source_offsets:
            return 0
        return self.source_offsets[max(0, min(index, len(self.source_offsets) - 1))]


class _Stripper(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=False)
        self._html = html
        self._line_starts = [0]
        for index, ch in enumerate(html):
            if ch == "\n":
                self._line_starts.append(index + 1)
        self.chars: list[str] = []
        self.offsets: list[int] = []
        self._skip = 0

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    def _emit(self, text: str, start: int, *, exact: bool) -> None:
        for index, ch in enumerate(text):
            self.chars.append(ch)
            self.offsets.append(start + index if exact else start)

    def _block_break(self) -> None:
        # A paragraph or heading boundary ends a sentence even with no full stop.
        if self.chars and self.chars[-1] != "\n":
            self._emit("\n", self._offset(), exact=False)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self._block_break()

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self._block_break()

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._emit(data, self._offset(), exact=True)

    def handle_entityref(self, name: str) -> None:
        if not self._skip:
            self._emit(unescape(f"&{name};"), self._offset(), exact=False)

    def handle_charref(self, name: str) -> None:
        if not self._skip:
            self._emit(unescape(f"&#{name};"), self._offset(), exact=False)


def strip_html(html: str) -> PlainText:
    """Remove tags, comments (WordPress block markers included), scripts and
    styles; decode entities; put a line break at each block boundary."""
    parser = _Stripper(html)
    parser.feed(html)
    parser.close()
    return PlainText("".join(parser.chars), tuple(parser.offsets))


@dataclass(frozen=True)
class Sentence:
    """One sentence: its text, its offset in the input, and its word count."""

    text: str
    offset: int
    word_count: int


@dataclass(frozen=True)
class ReadingLevel:
    """The result of :func:`reading_level`."""

    grade: float
    words: int
    sentences: int
    syllables: int
    words_per_sentence: float
    longest: tuple[Sentence, ...]


_WORD_RE = re.compile(r"[A-Za-zÀ-ɏ]+(?:['’][A-Za-z]+)*|\d+(?:[.,]\d+)*")
# A sentence ends at terminal punctuation (with any closing quote or bracket)
# followed by space, or at a line break left by a block boundary.
_SENTENCE_END_RE = re.compile(r"[.!?…]+[\"'”’)\]]*(?=\s|$)|\n+")
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


def _split_sentences(text: str) -> list[tuple[str, int]]:
    pieces: list[tuple[str, int]] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        end = match.end()
        pieces.append((text[start:end], start))
        start = end
    pieces.append((text[start:], start))
    result: list[tuple[str, int]] = []
    for piece, offset in pieces:
        stripped = piece.strip()
        if not stripped or not _WORD_RE.search(stripped):
            continue
        lead = len(piece) - len(piece.lstrip())
        result.append((stripped, offset + lead))
    return result


def reading_level(text: str, *, is_html: bool = False) -> ReadingLevel:
    """The Flesch-Kincaid grade of ``text``.

    With ``is_html`` the tags are stripped first (:func:`strip_html`) and each
    sentence offset points into the original HTML, ready for Go to It.
    """
    plain = strip_html(text) if is_html else None
    body = plain.text if plain is not None else text
    sentences: list[Sentence] = []
    total_words = 0
    total_syllables = 0
    for sentence_text, offset in _split_sentences(body):
        words = _WORD_RE.findall(sentence_text)
        total_words += len(words)
        total_syllables += sum(count_syllables(w) for w in words)
        source = plain.source_offset(offset) if plain is not None else offset
        sentences.append(Sentence(" ".join(sentence_text.split()), source, len(words)))
    if not total_words:
        return ReadingLevel(0.0, 0, 0, 0, 0.0, ())
    count = len(sentences)
    per_sentence = total_words / count
    grade = 0.39 * per_sentence + 11.8 * (total_syllables / total_words) - 15.59
    longest = tuple(sorted(sentences, key=lambda s: (-s.word_count, s.offset))[:LONGEST_COUNT])
    return ReadingLevel(
        grade=grade,
        words=total_words,
        sentences=count,
        syllables=total_syllables,
        words_per_sentence=per_sentence,
        longest=longest,
    )


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def describe(level: ReadingLevel) -> str:
    """ "Reading level: about 9th grade, 14 words per sentence"."""
    if not level.words:
        return "Reading level: not enough text to judge"
    grade = round(level.grade)
    if grade >= 13:
        where = "college level"
    else:
        where = f"about {_ordinal(max(1, grade))} grade"
    per = round(level.words_per_sentence)
    unit = "word" if per == 1 else "words"
    return f"Reading level: {where}, {per} {unit} per sentence"
