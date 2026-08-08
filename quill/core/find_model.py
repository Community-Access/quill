"""Core model for the unified Find dialog (issue #1327, phase F1).

Document-scope find/replace with two text modes: **normal** (the query is
literal text) and **extended** (the query may contain Notepad++-style escapes
such as ``\\t``, ``\\n``, ``\\x41``, ``\\u2014``, and ``\\N{EM DASH}``).
:data:`NAMED_CHARACTERS` backs the special-character picker with plain-English
names for characters that are hard to type or impossible to see.

A :class:`FindQuery` compiles to a :class:`CompiledQuery`; the matching and
replacement functions all take the compiled form plus the document text, and
return :class:`FindMatch` values carrying 1-based line and column so results
can be spoken ("line 40, column 12"). :func:`context_sentence` produces the
sentence around a match for announcements.

Pure, wx-free, strict-typed, no I/O. Raises :class:`FindModelError` (coded)
on a bad escape, with a plain-language message suitable to speak.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from quill.core.error_codes import CodedError


class FindModelError(CodedError):
    """The search text could not be interpreted (bad extended escape)."""

    code = "QUILL-CORE-FIND-BAD-ESCAPE"


# -- special characters -------------------------------------------------------

#: Plain-English name -> character for the special-character picker, ordered
#: by group: whitespace, dashes and hyphens, quotes, invisible and control,
#: typography. Names are what the picker shows and the screen reader speaks.
NAMED_CHARACTERS: dict[str, str] = {
    # Whitespace
    "Tab": "\t",
    "Line break": "\n",
    "Carriage return": "\r",
    "Page break (form feed)": "\f",
    "Non-breaking space": " ",
    "Narrow no-break space": " ",
    "Thin space": " ",
    "Hair space": " ",
    "Figure space": " ",
    "Em space": " ",
    "En space": " ",
    # Dashes and hyphens
    "Em dash": "—",
    "En dash": "–",
    "Soft hyphen": "­",
    "Non-breaking hyphen": "‑",
    "Minus sign": "−",
    # Quotes
    "Left double curly quote": "“",
    "Right double curly quote": "”",
    "Left single curly quote": "‘",
    "Right single curly quote": "’",
    "Straight double quote": '"',
    "Straight single quote (apostrophe)": "'",
    "Double angle quote, opening": "«",
    "Double angle quote, closing": "»",
    "Single angle quote, opening": "‹",
    "Single angle quote, closing": "›",
    # Invisible and control
    "Zero-width space": "​",
    "Zero-width non-joiner": "‌",
    "Zero-width joiner": "‍",
    "Word joiner": "⁠",
    "Byte order mark": "﻿",
    "Object replacement character": "￼",
    # Typography
    "Ellipsis": "…",
    "Bullet": "•",
    "Middle dot": "·",
    "Degree sign": "°",
    "Section sign": "§",
    "Pilcrow (paragraph mark)": "¶",
    "Dagger": "†",
    "Double dagger": "‡",
}


# -- extended mode ------------------------------------------------------------

_SIMPLE_ESCAPES: dict[str, str] = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "f": "\f",
    "0": "\0",
    "\\": "\\",
}

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def translate_extended(text: str) -> str:
    """Interpret extended-mode escapes and return the literal text they mean.

    Understands ``\\n`` ``\\t`` ``\\r`` ``\\f`` ``\\0`` ``\\\\``, ``\\xNN``,
    ``\\uNNNN``, and ``\\N{UNICODE NAME}``. An unknown single escape passes
    through literally as backslash-plus-character (forgiving, like Notepad++),
    as do a trailing backslash and a ``\\x``/``\\u`` without enough hex
    digits. An unknown or unfinished ``\\N{...}`` name raises
    :class:`FindModelError` naming the bad name and its position.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= n:
            # Trailing backslash: keep it literally.
            out.append("\\")
            break
        kind = text[i + 1]
        if kind in _SIMPLE_ESCAPES:
            out.append(_SIMPLE_ESCAPES[kind])
            i += 2
            continue
        if kind in ("x", "u"):
            width = 2 if kind == "x" else 4
            digits = text[i + 2 : i + 2 + width]
            if len(digits) == width and all(d in _HEX_DIGITS for d in digits):
                out.append(chr(int(digits, 16)))
                i += 2 + width
            else:
                # Not enough hex digits: keep the escape literally.
                out.append("\\" + kind)
                i += 2
            continue
        if kind == "N" and i + 2 < n and text[i + 2] == "{":
            close = text.find("}", i + 3)
            if close == -1:
                raise FindModelError(
                    f"The character name at position {i + 1} is missing its "
                    'closing brace. Write it as \\N{NAME}, for example "\\N{EM DASH}".'
                )
            name = text[i + 3 : close]
            try:
                out.append(unicodedata.lookup(name))
            except KeyError:
                raise FindModelError(
                    f"'{name}' at position {i + 1} is not a known character "
                    "name. Use a Unicode name such as EM DASH or BULLET."
                ) from None
            i = close + 1
            continue
        # Unknown escape: keep it literally (forgiving).
        out.append("\\" + kind)
        i += 2
    return "".join(out)


# -- query and compilation ----------------------------------------------------

Mode = Literal["normal", "extended"]


@dataclass(frozen=True)
class FindQuery:
    """What the user asked to find, before compilation."""

    text: str
    mode: Mode = "normal"
    case_sensitive: bool = False
    whole_word: bool = False
    wrap: bool = True


@dataclass(frozen=True)
class CompiledQuery:
    """A :class:`FindQuery` compiled for matching.

    ``pattern`` is ``None`` when the query text is empty; every matching
    function then yields no matches rather than raising.
    """

    query: FindQuery
    pattern: re.Pattern[str] | None


def _is_word_char(ch: str) -> bool:
    return re.match(r"\w", ch) is not None


def compile_query(query: FindQuery) -> CompiledQuery:
    """Compile ``query`` into the form the matching functions take.

    Normal mode treats the text as a literal; extended mode first interprets
    escapes with :func:`translate_extended`. Whole-word adds a word-boundary
    guard at each end only when that end is a word character, so a whole-word
    search for ``C++`` still works.
    """
    literal = translate_extended(query.text) if query.mode == "extended" else query.text
    if not literal:
        return CompiledQuery(query=query, pattern=None)
    pattern_text = re.escape(literal)
    if query.whole_word:
        if _is_word_char(literal[0]):
            pattern_text = r"\b" + pattern_text
        if _is_word_char(literal[-1]):
            pattern_text = pattern_text + r"\b"
    flags = 0 if query.case_sensitive else re.IGNORECASE
    return CompiledQuery(query=query, pattern=re.compile(pattern_text, flags))


# -- matching -----------------------------------------------------------------


@dataclass(frozen=True)
class FindMatch:
    """One match in the document; ``line`` and ``column`` are 1-based."""

    start: int
    end: int
    text: str
    line: int
    column: int


def _locate(text: str, start: int) -> tuple[int, int]:
    line = text.count("\n", 0, start) + 1
    line_start = text.rfind("\n", 0, start) + 1
    return line, start - line_start + 1


def _to_match(text: str, start: int, end: int) -> FindMatch:
    line, column = _locate(text, start)
    return FindMatch(start=start, end=end, text=text[start:end], line=line, column=column)


def _iter_raw(pattern: re.Pattern[str], text: str) -> Iterator[re.Match[str]]:
    """All matches left to right, advancing past zero-width matches safely."""
    pos = 0
    limit = len(text)
    while pos <= limit:
        found = pattern.search(text, pos)
        if found is None:
            return
        yield found
        pos = found.end() + 1 if found.end() == found.start() else found.end()


def count_matches(
    compiled: CompiledQuery, text: str, *, max_count: int = 10_000
) -> tuple[int, bool]:
    """Count matches, stopping at ``max_count``; returns ``(count, truncated)``."""
    if compiled.pattern is None:
        return 0, False
    count = 0
    for _ in _iter_raw(compiled.pattern, text):
        count += 1
        if count > max_count:
            return max_count, True
    return count, False


def _search_forward(pattern: re.Pattern[str], text: str, pos: int) -> re.Match[str] | None:
    found = pattern.search(text, pos)
    if found is not None and found.start() == found.end() == pos:
        # Never return the zero-width match at ``pos`` itself, so a repeated
        # find from the returned position always advances.
        found = pattern.search(text, pos + 1) if pos < len(text) else None
    return found


def find_next(
    compiled: CompiledQuery, text: str, *, from_pos: int, backwards: bool = False
) -> tuple[FindMatch | None, bool]:
    """The next match from ``from_pos``; returns ``(match, wrapped)``.

    Forwards: the first match starting at or after ``from_pos``, wrapping to
    the start when the query allows it. Backwards: the last match ending at or
    before ``from_pos``, wrapping to the end. The zero-width match sitting
    exactly at ``from_pos`` is never returned, so repeated calls advance.
    """
    if compiled.pattern is None:
        return None, False
    pos = max(0, min(from_pos, len(text)))
    if backwards:
        return _find_previous(compiled, text, pos)
    found = _search_forward(compiled.pattern, text, pos)
    if found is not None:
        return _to_match(text, found.start(), found.end()), False
    if not compiled.query.wrap or pos == 0:
        return None, False
    found = _search_forward(compiled.pattern, text, 0)
    if found is None or found.start() == found.end() == pos:
        return None, False
    return _to_match(text, found.start(), found.end()), True


def _find_previous(compiled: CompiledQuery, text: str, pos: int) -> tuple[FindMatch | None, bool]:
    assert compiled.pattern is not None
    last_before: re.Match[str] | None = None
    last_any: re.Match[str] | None = None
    for found in _iter_raw(compiled.pattern, text):
        if found.end() <= pos and not (found.start() == found.end() == pos):
            last_before = found
        last_any = found
    if last_before is not None:
        return _to_match(text, last_before.start(), last_before.end()), False
    if not compiled.query.wrap or last_any is None:
        return None, False
    if last_any.start() == last_any.end() == pos:
        return None, False
    return _to_match(text, last_any.start(), last_any.end()), True


def all_matches(
    compiled: CompiledQuery, text: str, *, max_matches: int = 5_000
) -> tuple[tuple[FindMatch, ...], bool]:
    """All matches left to right, capped; returns ``(matches, truncated)``."""
    if compiled.pattern is None:
        return (), False
    matches: list[FindMatch] = []
    for found in _iter_raw(compiled.pattern, text):
        if len(matches) >= max_matches:
            return tuple(matches), True
        matches.append(_to_match(text, found.start(), found.end()))
    return tuple(matches), False


_SENTENCE_BOUNDARIES = ".!?"


def _collapse(fragment: str) -> str:
    return re.sub(r"\s+", " ", fragment).strip()


def context_sentence(text: str, match: FindMatch, *, max_chars: int = 120) -> str:
    """The sentence around ``match``, whitespace-collapsed, for announcements.

    A sentence runs between ``.``, ``!``, ``?``, or newline boundaries. When
    the sentence is longer than ``max_chars`` the result is a window of that
    size centered on the match, with a leading/trailing ellipsis where text
    was cut.
    """
    sent_start = 0
    for i in range(match.start - 1, -1, -1):
        if text[i] in _SENTENCE_BOUNDARIES or text[i] == "\n":
            sent_start = i + 1
            break
    sent_end = len(text)
    for j in range(match.end, len(text)):
        if text[j] in _SENTENCE_BOUNDARIES:
            sent_end = j + 1
            break
        if text[j] == "\n":
            sent_end = j
            break
    sentence = _collapse(text[sent_start:sent_end])
    if not sentence:
        # The surrounding "sentence" was whitespace only -- searching for a
        # space or a tab on an otherwise blank line. Returning "" would make
        # the caller announce nothing at all, and a silent success is an
        # accessibility failure (the acceptance book's own rubric): the
        # listener cannot tell a found match from a failed search. Fall back
        # to the position, which is always speakable.
        return f"line {match.line}, column {match.column}"
    if len(sentence) <= max_chars:
        return sentence
    center = (match.start + match.end) // 2
    window_start = max(0, center - max_chars // 2)
    window_end = min(len(text), window_start + max_chars)
    window_start = max(0, window_end - max_chars)
    window = _collapse(text[window_start:window_end])
    prefix = "..." if window_start > 0 else ""
    suffix = "..." if window_end < len(text) else ""
    return f"{prefix}{window}{suffix}"


# -- replace ------------------------------------------------------------------


def replace_next(
    compiled: CompiledQuery, text: str, replacement: str, *, from_pos: int
) -> tuple[str, FindMatch | None, bool]:
    """Replace the next match with the literal ``replacement``.

    Returns ``(new_text, replaced_match, wrapped)``; the text is unchanged
    when there is no match. In extended mode the caller passes the replacement
    through :func:`translate_extended` first -- it is spliced in literally
    here, never treated as a regex template.
    """
    match, wrapped = find_next(compiled, text, from_pos=from_pos)
    if match is None:
        return text, None, False
    new_text = text[: match.start] + replacement + text[match.end :]
    return new_text, match, wrapped


def replace_all(compiled: CompiledQuery, text: str, replacement: str) -> tuple[str, int]:
    """Replace every match with the literal ``replacement`` in a single pass."""
    if compiled.pattern is None:
        return text, 0
    parts: list[str] = []
    last = 0
    count = 0
    for found in _iter_raw(compiled.pattern, text):
        parts.append(text[last : found.start()])
        parts.append(replacement)
        last = found.end()
        count += 1
    if count == 0:
        return text, 0
    parts.append(text[last:])
    return "".join(parts), count


def preview_replacements(
    compiled: CompiledQuery, text: str, replacement: str, *, count: int = 20
) -> tuple[str, ...]:
    """Speakable one-line previews, e.g. ``'colour' to 'color' at line 12``."""
    matches, _truncated = all_matches(compiled, text, max_matches=count)
    return tuple(f"'{match.text}' to '{replacement}' at line {match.line}" for match in matches)
