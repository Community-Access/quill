"""The local argument reader (command-key.md 5.4 and 8.3).

Numbers, durations and sizes are read here, on the computer, before any matcher
sees the sentence: "favourite 3", "skip back 30 seconds", "a lot louder". What
was read is taken out of the words the matcher scores, so "go to line 120" and
"go to line 5" are the same request with a different number.

Nothing read here is ever sent anywhere; an engine is told only whether a
number was found, and its value (section 7.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["ReadArgs", "read_args"]

_ONES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
_UNITS = {
    "hour": 3600,
    "hours": 3600,
    "hr": 3600,
    "hrs": 3600,
    "minute": 60,
    "minutes": 60,
    "min": 60,
    "mins": 60,
    "second": 1,
    "seconds": 1,
    "sec": 1,
    "secs": 1,
}
#: Phrases that say "a small step" or "a big one". Longest first.
_SMALL = ("a little bit", "a tiny bit", "a little", "a bit", "slightly", "a touch", "bit")
_LARGE = ("a whole lot", "a lot", "way more", "much", "really", "very", "way", "loads", "lots")
#: How many steps a large one is.
LARGE_STEPS = 3

_WORD = re.compile(r"[a-z0-9]+(?:st|nd|rd|th)?")


@dataclass(frozen=True, slots=True)
class ReadArgs:
    """What the reader found, and the words left for the matcher."""

    remainder: str
    number: int | None = None
    seconds: int | None = None
    size: str = ""  # "small", "large" or ""

    @property
    def steps(self) -> int:
        """How many times a stepped command runs: three for "a lot", else one."""
        return LARGE_STEPS if self.size == "large" else 1

    def as_dict(self) -> dict[str, object]:
        found: dict[str, object] = {}
        if self.number is not None:
            found["number"] = self.number
        if self.seconds is not None:
            found["seconds"] = self.seconds
        if self.size:
            found["size"] = self.size
        return found


def _number_at(tokens: list[str], index: int) -> tuple[int, int] | None:
    """The number starting at *index*, and how many tokens it used."""
    token = tokens[index]
    ordinal = re.fullmatch(r"(\d+)(st|nd|rd|th)", token)
    if ordinal:
        return int(ordinal.group(1)), 1
    if token.isdigit():
        return int(token), 1
    if token in _ORDINALS:
        return _ORDINALS[token], 1
    if token in _TENS:
        value = _TENS[token]
        if index + 1 < len(tokens) and tokens[index + 1] in _ONES and _ONES[tokens[index + 1]] < 10:
            return value + _ONES[tokens[index + 1]], 2
        return value, 1
    if token in _ONES:
        return _ONES[token], 1
    return None


def _take_size(text: str) -> tuple[str, str]:
    padded = f" {text} "
    for size, phrases in (("small", _SMALL), ("large", _LARGE)):
        for phrase in phrases:
            needle = f" {phrase} "
            if needle in padded:
                return size, " ".join(padded.replace(needle, " ", 1).split())
    return "", text


def read_args(text: str) -> ReadArgs:
    """Read the number, duration and size out of *text* (already normalised)."""
    size, text = _take_size(text)
    tokens = text.replace("-", " ").split()
    kept: list[str] = []
    number: int | None = None
    seconds: int | None = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        # "an hour", "a minute", "half an hour", "an hour and a half"
        if token in {"a", "an"} and index + 1 < len(tokens) and tokens[index + 1] in _UNITS:
            unit = _UNITS[tokens[index + 1]]
            seconds = (seconds or 0) + unit
            index += 2
            if tokens[index : index + 3] == ["and", "a", "half"]:
                seconds += unit // 2
                index += 3
            continue
        if token == "half" and tokens[index + 1 : index + 2] in (["an"], ["a"]):
            if index + 2 < len(tokens) and tokens[index + 2] in _UNITS:
                seconds = (seconds or 0) + _UNITS[tokens[index + 2]] // 2
                index += 3
                continue
        found = _number_at(tokens, index)
        if found is not None:
            value, used = found
            after = index + used
            if after < len(tokens) and tokens[after] in _UNITS:
                seconds = (seconds or 0) + value * _UNITS[tokens[after]]
                index = after + 1
                if tokens[index : index + 3] == ["and", "a", "half"]:
                    seconds += _UNITS[tokens[after]] // 2
                    index += 3
                continue
            if number is None:
                number = value
                index = after
                continue
        kept.append(token)
        index += 1
    return ReadArgs(remainder=" ".join(kept), number=number, seconds=seconds, size=size)
