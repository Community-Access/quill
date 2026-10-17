"""Word errors: how many words were substituted, inserted or deleted.

The one scorer, shared by the benchmark (``scripts/dictbench.py``, B-1) and
QUILL Transcribe's recognition test (D-25, :mod:`quill.core.transcribe.practice`),
so a number somebody reads in the Practice window means what the benchmark's
numbers mean.

Pure and wx-free.
"""

from __future__ import annotations

import re

__all__ = ["score_words", "word_errors"]

_WORDS = re.compile(r"[\w']+")


def score_words(text: str) -> list[str]:
    """*text* as words for scoring: no capitals, no punctuation."""
    return _WORDS.findall(text.lower().replace("_", " "))


def word_errors(reference: list[str], heard: list[str]) -> int:
    """Substitutions, insertions and deletions turning *reference* into *heard*."""
    previous = list(range(len(heard) + 1))
    for i, said in enumerate(reference, 1):
        current = [i]
        for j, got in enumerate(heard, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (said != got))
            )
        previous = current
    return previous[-1]
