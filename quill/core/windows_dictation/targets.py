"""Words as targets: "select the cat", "go after Tuesday", "insert snippet sign off".

dict.md 3.2 and 3.4 (gaps 7 and 5). Everything here is pure: given the
document's text, the cursor, and the words said after a command, where those
words are -- or, for a snippet, a clip slot or an abbreviation, which one was
meant.

**Matching words in the document.** Case, punctuation and accents are ignored,
and numbers match both ways ("two" finds "2" and "2" finds "two"), because what
the engine wrote and what you say back are rarely spelled alike. My Words
corrections have already been applied to what you said before it reaches here
(the controller rewrites every phrase first), so a word the engine always
mishears is found by its corrected form.

**Which match.** The nearest one *before* the cursor first, because the person
is usually fixing what they just said; failing that, the nearest one after.
"select the cat through the hat" selects from the first to the end of the
second.

**Names.** A snippet is matched exactly first, then by a unique start, then by
a unique word it contains; more than one match is reported as a count, never
guessed between.

Pure and wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from quill.core.windows_dictation.speech_language import fold

__all__ = [
    "Target",
    "find_target",
    "line_number",
    "match_names",
    "number_from",
    "paragraph_bounds",
    "unit_bounds",
]

_WORD = re.compile(r"[\w']+")
_NUMBERS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty"
).split()
_NUMBER_WORDS: dict[str, str] = {word: str(value) for value, word in enumerate(_NUMBERS)}
_NUMBER_WORDS.update({"for": "4", "to": "2", "too": "2", "won": "1", "ate": "8"})
#: Words that join the two ends of a range: "select the cat through the hat".
_THROUGH = frozenset({"through", "thru"})


def _normal(word: str) -> str:
    word = fold(word).replace("’", "'").strip("'")
    return _NUMBERS.index(word).__str__() if word in _NUMBERS else word


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(_normal(match.group(0)), match.start(), match.end()) for match in _WORD.finditer(text)]


def _said(words: Iterable[str]) -> list[str]:
    out: list[str] = []
    for word in words:
        out.extend(_normal(part) for part in _WORD.findall(word))
    return [word for word in out if word]


def number_from(words: Sequence[str]) -> int | None:
    """The number *words* say -- "three", "3", "number three" -- or ``None``."""
    said = [fold(word).strip(".") for word in words if fold(word) not in ("number", "slot")]
    if len(said) != 1:
        return None
    word = said[0]
    if word.isdigit():
        return int(word)
    value = _NUMBER_WORDS.get(word)
    return int(value) if value is not None else None


@dataclass(frozen=True, slots=True)
class Target:
    """Where some words are in the document, and every other place they are."""

    start: int
    end: int
    #: Every match of the words, in document order, for "select next".
    matches: tuple[tuple[int, int], ...] = ()
    #: Which of *matches* this is.
    index: int = 0

    def moved(self, step: int) -> Target | None:
        """The next (*step* 1) or previous (-1) match, or ``None`` at the end."""
        index = self.index + step
        if not 0 <= index < len(self.matches):
            return None
        start, end = self.matches[index]
        return Target(start, end, self.matches, index)


def _find_all(tokens: list[tuple[str, int, int]], wanted: list[str]) -> list[tuple[int, int]]:
    if not wanted:
        return []
    found: list[tuple[int, int]] = []
    size = len(wanted)
    for index in range(len(tokens) - size + 1):
        if all(tokens[index + offset][0] == wanted[offset] for offset in range(size)):
            found.append((tokens[index][1], tokens[index + size - 1][2]))
    return found


def _nearest(matches: list[tuple[int, int]], caret: int) -> int | None:
    """The index of the nearest match before *caret* (one the cursor is inside
    counts), else the nearest after."""
    before = [index for index, (start, _end) in enumerate(matches) if start < caret]
    if before:
        return before[-1]
    after = [index for index, (start, _end) in enumerate(matches) if start >= caret]
    if after:
        return after[0]
    return 0 if matches else None


def find_target(text: str, caret: int, words: Sequence[str]) -> Target | None:
    """Where *words* are in *text*, nearest the cursor at *caret*, or ``None``.

    "the cat through the hat" is a range: from the match of the first words
    nearest the cursor, to the end of the first match of the second words that
    comes after it.
    """
    said = _said(words)
    tokens = _tokens(text)
    split = next((index for index, word in enumerate(said) if word in _THROUGH), None)
    if split is not None and 0 < split < len(said) - 1:
        first = _find_all(tokens, said[:split])
        index = _nearest(first, caret)
        if index is None:
            return None
        start = first[index][0]
        ends = [end for begin, end in _find_all(tokens, said[split + 1 :]) if begin >= start]
        if not ends:
            return None
        return Target(start, ends[0], ((start, ends[0]),), 0)
    matches = _find_all(tokens, said)
    index = _nearest(matches, caret)
    if index is None:
        return None
    start, end = matches[index]
    return Target(start, end, tuple(matches), index)


def line_number(text: str, position: int) -> int:
    """The line *position* is on, counting from one."""
    return text.count("\n", 0, max(0, position)) + 1


def paragraph_bounds(text: str, caret: int) -> tuple[int, int]:
    """Where the paragraph the cursor is in starts and ends (blank lines apart)."""
    caret = max(0, min(caret, len(text)))
    start = text.rfind("\n\n", 0, caret)
    start = 0 if start < 0 else start + 2
    end = text.find("\n\n", caret)
    end = len(text) if end < 0 else end
    return start, end


def unit_bounds(text: str, caret: int, unit: str) -> tuple[int, int]:
    """The ``line``, ``sentence`` or ``paragraph`` the cursor is in."""
    caret = max(0, min(caret, len(text)))
    if unit == "paragraph":
        return paragraph_bounds(text, caret)
    if unit == "line":
        start = text.rfind("\n", 0, caret) + 1
        end = text.find("\n", caret)
        return start, len(text) if end < 0 else end
    # A sentence: back to the last ". ", "? ", "! " or line start; on to the
    # next mark that ends one, with it.
    line_start, line_end = unit_bounds(text, caret, "line")
    start = line_start
    for index in range(min(caret, line_end) - 1, line_start - 1, -1):
        if text[index] in ".?!" and index + 1 < caret:
            start = index + 1
            break
    while start < line_end and text[start] == " ":
        start += 1
    end = line_end
    for index in range(max(caret, start), line_end):
        if text[index] in ".?!":
            end = index + 1
            break
    return start, end


def _name_words(name: str) -> list[str]:
    return [fold(word) for word in _WORD.findall(name.replace("_", " ").replace("-", " "))]


def match_names(names: Iterable[str], words: Sequence[str]) -> list[str]:
    """The names *words* pick out: exact, else a unique start, else a unique word.

    Case, punctuation and accents are ignored, so "sign off" finds "Sign-off"
    and ";sig" is found by "sig". The answer is a list: one name is a match,
    several are a question the caller asks, none is a "not found".
    """
    said = [fold(word) for part in words for word in _WORD.findall(part.replace("-", " "))]
    if not said:
        return []
    candidates = list(dict.fromkeys(name for name in names if _name_words(name)))
    # Spaces do not count either: "sig off" is the trigger "sigoff".
    compact = "".join(said)
    exact = [name for name in candidates if "".join(_name_words(name)) == compact]
    if exact:
        return exact[:1] if len(exact) == 1 else exact
    joined = " ".join(said)
    starts = [
        name
        for name in candidates
        if " ".join(_name_words(name)).startswith(joined)
        or "".join(_name_words(name)).startswith(compact)
    ]
    if starts:
        return starts
    return [name for name in candidates if all(word in _name_words(name) for word in said)]
