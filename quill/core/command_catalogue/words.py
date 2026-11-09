"""Words, as the Command Key's matcher reads them (command-key.md 6.3, tier 2).

Normalising, filler words, a small stemmer, a synonym table and a forgiving
word comparison. Everything here is offline and deterministic, so the same
sentence always matches the same way and a corpus row that passes today still
passes tomorrow.
"""

from __future__ import annotations

import re
from functools import lru_cache

__all__ = [
    "FILLER",
    "content_words",
    "normalize",
    "similar",
    "stem",
]

_WORD = re.compile(r"[a-z0-9]+")

#: Words that say how politely something was asked, not what was asked for.
FILLER = frozenset({
    "a",
    "an",
    "and",
    "any",
    "are",
    "be",
    "can",
    "could",
    "do",
    "for",
    "get",
    "give",
    "go",
    "hey",
    "i",
    "id",
    "im",
    "is",
    "it",
    "its",
    "just",
    "kindly",
    "let",
    "like",
    "make",
    "me",
    "my",
    "now",
    "of",
    "ok",
    "okay",
    "please",
    "put",
    "quill",
    "right",
    "so",
    "some",
    "take",
    "that",
    "the",
    "then",
    "there",
    "thing",
    "this",
    "to",
    "try",
    "want",
    "wanna",
    "would",
    "you",
    "your",
})

#: One spelling, or one word, for each idea. Applied after stemming.
_SYNONYMS: dict[str, str] = {
    "favorit": "favourit",
    "favourite": "favourit",
    "favorite": "favourit",
    "fave": "favourit",
    "loud": "louder",
    "loudest": "louder",
    "quiet": "quieter",
    "soft": "quieter",
    "softer": "quieter",
    "volum": "volume",
    "sound": "volume",
    "colour": "color",
    "search": "find",
    "locat": "find",
    "lookup": "find",
    "begin": "start",
    "commenc": "start",
    "halt": "stop",
    "end": "stop",
    "quick": "faster",
    "quicker": "faster",
    "fast": "faster",
    "slow": "slower",
    "larger": "bigger",
    "large": "bigger",
    "big": "bigger",
    "huge": "bigger",
    "small": "smaller",
    "tiny": "smaller",
    "tune": "song",
    "track": "song",
    "music": "song",
    "radio": "station",
    "channel": "station",
    "doc": "document",
    "file": "document",
    "page": "document",
    "documents": "document",
    "shut": "close",
    "alarm": "wake",
    "previou": "previous",
    "prior": "previous",
    "last": "previous",
    "nxt": "next",
    "following": "next",
}

#: Common endings, longest first. Deliberately crude: it only has to make
#: "headings" and "heading" the same word, not be a linguist. "-ing" is kept on
#: purpose: "recording" is not "record", and "playing" is not "play".
_SUFFIXES = ("s",)


def normalize(text: str) -> str:
    """Lower-case *text* and keep only its words, apostrophes joined ("what's" -> "whats")."""
    return " ".join(_WORD.findall(text.lower().replace("'", "").replace("’", "")))


@lru_cache(maxsize=4096)
def stem(word: str) -> str:
    """The word, without a common ending, and through the synonym table."""
    base = _SYNONYMS.get(word)
    if base is not None:
        return base
    for suffix in _SUFFIXES:
        if (
            len(word) > len(suffix) + 2
            and word.endswith(suffix)
            and not word.endswith(("ss", "us"))
        ):
            word = word[: -len(suffix)]
            break
    return _SYNONYMS.get(word, word)


class Word(str):
    """A stemmed word that remembers how it was written.

    It compares as its stem, so "favourites" and "favorite" are one word; and
    :func:`similar` also compares the written forms, so a typo of the written
    word ("favouites") still lands even when the synonym table moved the stem.
    """

    __slots__ = ("raw",)
    raw: str

    def __new__(cls, raw: str) -> Word:
        word = super().__new__(cls, stem(raw))
        word.raw = raw
        return word


def content_words(text: str) -> tuple[str, ...]:
    """The words that carry meaning, stemmed, in order, without filler."""
    return tuple(Word(word) for word in normalize(text).split() if word not in FILLER)


def _distance_at_most_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        differences = sum(1 for a, b in zip(left, right, strict=True) if a != b)
        if differences == 1:
            return True
        # One swapped pair: "teh" for "the".
        for index in range(len(left) - 1):
            if (
                left[index] == right[index + 1]
                and left[index + 1] == right[index]
                and left[:index] == right[:index]
                and left[index + 2 :] == right[index + 2 :]
            ):
                return True
        return False
    short, long = (left, right) if len(left) < len(right) else (right, left)
    for index in range(len(long)):
        if long[:index] + long[index + 1 :] == short:
            return True
    return False


def similar(left: str, right: str) -> bool:
    """Whether two stemmed words are the same word, allowing one typo in long words.

    Words of four letters or fewer must match exactly: "mute" and "mike" are one
    letter apart and mean nothing alike, and short words are where a typo is
    most likely to land on another real word.
    """
    if left == right:
        return True
    if _close(left, right):
        return True
    raw_left = getattr(left, "raw", left)
    raw_right = getattr(right, "raw", right)
    return (raw_left, raw_right) != (left, right) and _close(raw_left, raw_right)


def _close(left: str, right: str) -> bool:
    if left == right:
        return True
    if min(len(left), len(right)) <= 4 or left[0] != right[0]:
        return False
    return _distance_at_most_one(str(left), str(right))
