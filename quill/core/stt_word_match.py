"""Did a speech-to-text engine hear a known phrase well enough? (wx-free).

Used by Download Optional Components' Test button: the engine transcribes a
clip of a fixed phrase, and recognition is never word-perfect, so the check is
how many of the expected words came back rather than an exact match.
"""

from __future__ import annotations

import re


def covers_enough_words(expected: str, heard: str, *, threshold: float = 0.4) -> bool:
    """True when *heard* covers enough of *expected*'s words (STT is imperfect)."""

    def toks(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9']+", text.lower()))

    want = toks(expected)
    if not want:
        return False
    return len(want & toks(heard)) / len(want) >= threshold
