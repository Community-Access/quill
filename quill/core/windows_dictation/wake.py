"""The wake phrase: "Quill dictate", or whatever the user chose instead.

While the wake phrase is on, the microphone listens with dictation *off*, and
every phrase it hears is checked for the wake phrase at its start. Nothing it
hears is written anywhere, kept, or logged -- a phrase that does not begin with
the wake phrase is dropped the moment it has been checked.

**Matching is forgiving on purpose, and only at the start.** A recogniser that
has never been told a word will spell it the nearest way it knows: "Quill"
comes back "quil", "kill" or "Quill,". So each word of the wake phrase matches
a heard word that is the same, or sounds the same (Soundex), or is one edit away
-- the matcher QUILL already uses to correct the user's own vocabulary
(:mod:`quill.core.speech.vocabulary`). Only at the *start* of a phrase, because
"I told Quill to dictate" in a conversation across the room should not start
anything.

**Anything said after the wake phrase is dictated.** "Quill dictate dear Sam
comma" wakes dictation and writes *Dear Sam,* -- nobody should have to wait for
the start tones before they begin.

A wake phrase of one short common word would fire all day, so
:func:`wake_phrase_problem` refuses anything under two words or under six
letters, and says why.

**The stop phrase is the other end**, and the user chooses it too ("stop
dictation" until they do). It matches with the same forgiveness but only as a
**whole phrase**, said on its own after a pause -- a stop phrase heard in the
middle of a sentence is part of the sentence -- and :func:`stop_phrase_problem`
holds it to the same two-word rule, because a stop that fires by accident loses
the rest of what somebody was saying.

Pure and wx-free.
"""

from __future__ import annotations

import re

from quill.core.speech.vocabulary import levenshtein, soundex

__all__ = [
    "DEFAULT_STOP_PHRASE",
    "DEFAULT_WAKE_PHRASE",
    "is_stop_phrase",
    "match_wake",
    "stop_phrase_problem",
    "wake_phrase_problem",
    "wake_words",
]

DEFAULT_WAKE_PHRASE = "Quill dictate"
DEFAULT_STOP_PHRASE = "stop dictation"

_WORD = re.compile(r"[a-z0-9']+")


def wake_words(phrase: str) -> list[str]:
    return _WORD.findall(phrase.lower())


def wake_phrase_problem(phrase: str) -> str:
    """Why *phrase* would make a poor wake phrase, or ``""`` when it is fine."""
    return _phrase_problem(phrase, "wake phrase", "start")


def stop_phrase_problem(phrase: str) -> str:
    """Why *phrase* would make a poor stop phrase, or ``""`` when it is fine."""
    return _phrase_problem(phrase, "stop phrase", "stop")


def _phrase_problem(phrase: str, name: str, verb: str) -> str:
    words = wake_words(phrase)
    if len(words) < 2:
        return (
            f"Use at least two words for the {name}. A single word is said in "
            f"ordinary conversation too often, and would {verb} dictation by accident."
        )
    if sum(len(word) for word in words) < 6:
        return f"Use a longer {name}: short words are easily heard by mistake."
    return ""


def _same_word(said: str, wanted: str) -> bool:
    if said == wanted:
        return True
    if len(wanted) >= 3 and soundex(said) == soundex(wanted):
        return True
    limit = 1 if len(wanted) <= 5 else 2
    return levenshtein(said, wanted) <= limit


def match_wake(heard: list[str], phrase: str) -> int | None:
    """How many of *heard*'s words the wake phrase used, or ``None`` if absent.

    *heard* is the phrase's words, lower-cased and stripped of punctuation.
    """
    wanted = wake_words(phrase)
    if not wanted or len(heard) < len(wanted):
        return None
    for said, want in zip(heard, wanted, strict=False):
        if not _same_word(said, want):
            return None
    return len(wanted)


def is_stop_phrase(heard: list[str], phrase: str) -> bool:
    """Whether *heard* is the stop phrase and nothing else."""
    return bool(heard) and match_wake(heard, phrase) == len(heard)
