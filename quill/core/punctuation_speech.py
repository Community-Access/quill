"""Punctuation verbalization for Read Aloud (SET-3).

Screen readers expose a punctuation verbosity level (none / some / most / all)
so a listener can choose how much punctuation is spoken. No SAPI, Edge, or
pyttsx3 voice exposes such a parameter, so QUILL implements it itself: before a
sentence is handed to any TTS engine, the punctuation marks at or below the
chosen level are rewritten into their spoken names. This gives Read Aloud the
same punctuation control a screen reader offers, independent of the engine in
use, and it is the live consumer of the ``announce_punctuation_level`` setting.

The module is pure and wx-free so it can be unit-tested deterministically and
imported from :mod:`quill.core.read_aloud` without any UI dependency.
"""

from __future__ import annotations

PUNCTUATION_LEVELS = ("none", "some", "most", "all")
DEFAULT_PUNCTUATION_LEVEL = "some"

# Spoken name for each supported symbol. The apostrophe is deliberately absent
# so contractions ("don't") and possessives are never broken apart.
_SYMBOL_WORDS: dict[str, str] = {
    "@": "at",
    "#": "number",
    "$": "dollar",
    "%": "percent",
    "&": "and",
    "*": "star",
    "+": "plus",
    "=": "equals",
    "<": "less than",
    ">": "greater than",
    "|": "bar",
    "~": "tilde",
    "^": "caret",
    "`": "backtick",
    "\\": "backslash",
    "/": "slash",
    "(": "left paren",
    ")": "right paren",
    "[": "left bracket",
    "]": "right bracket",
    "{": "left brace",
    "}": "right brace",
    '"': "quote",
    "_": "underscore",
    "-": "dash",
    "\u2013": "en dash",
    "\u2014": "em dash",
    ".": "dot",
    ",": "comma",
    ";": "semicolon",
    ":": "colon",
    "!": "exclamation",
    "?": "question mark",
}

# Technical, currency, and math symbols that change meaning and are easy to miss
# when silent. Spoken from "some" upward, leaving ordinary prose untouched.
_SOME_SYMBOLS = frozenset("@#$%&*+=<>|~^`\\/")
# Brackets, quotes, dashes, and underscores join in at "most".
_MOST_SYMBOLS = _SOME_SYMBOLS | frozenset('()[]{}"_-\u2013\u2014')
# Sentence punctuation joins in only at "all" (NVDA-style full verbosity).
_ALL_SYMBOLS = _MOST_SYMBOLS | frozenset(".,;:!?")

_LEVEL_SYMBOLS: dict[str, frozenset[str]] = {
    "none": frozenset(),
    "some": _SOME_SYMBOLS,
    "most": _MOST_SYMBOLS,
    "all": _ALL_SYMBOLS,
}


def normalize_punctuation_level(level: str) -> str:
    """Coerce arbitrary input to a known level, defaulting to ``some``."""

    candidate = level.strip().lower()
    if candidate in _LEVEL_SYMBOLS:
        return candidate
    return DEFAULT_PUNCTUATION_LEVEL


def verbalize_punctuation(text: str, level: str) -> str:
    """Rewrite punctuation in ``text`` into spoken words for the given level.

    At ``none`` the text is returned unchanged. At higher levels each symbol in
    the active set is replaced by its spoken name surrounded by spaces, then
    runs of whitespace are collapsed so the engine receives clean input.

    Performance notes (#344): the implementation walks the string once and
    builds a list of string pieces before joining.  The per-character
    ``list.append`` is O(1) amortised and the final ``str.split``/``join``
    is O(N) on the rewritten length, so the function is linear in the input
    length.  Sentence-level callers (the primary use case in the read-aloud
    engine) stay well under 1 ms for typical inputs.  Whole-document input
    is theoretically supported but is not on the read-aloud hot path; if a
    future feature needs document-level verbalization, switch to a
    ``str.translate``-based batch rewrite and drop the per-character loop.
    """

    active = _LEVEL_SYMBOLS.get(normalize_punctuation_level(level), _SOME_SYMBOLS)
    if not active:
        return text
    pieces: list[str] = []
    for char in text:
        if char in active:
            pieces.append(" " + _SYMBOL_WORDS[char] + " ")
        else:
            pieces.append(char)
    return " ".join("".join(pieces).split())
