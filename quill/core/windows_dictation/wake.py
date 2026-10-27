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

**Each dictation language has its own defaults** ("Quill dicta" and "deja de
dictar" in Spanish, awaiting native-speaker review): see
:func:`~quill.core.windows_dictation.speech_language.localised_phrase`. Words
are compared without their accents, so "dictá" and "dicta" are one word.

Pure and wx-free.
"""

from __future__ import annotations

from quill.core.speech.vocabulary import levenshtein, soundex
from quill.core.windows_dictation.speech_language import (
    STOP_PHRASES,
    WAKE_PHRASES,
    folded_words,
)

__all__ = [
    "DEFAULT_STOP_PHRASE",
    "DEFAULT_WAKE_PHRASE",
    "is_stop_phrase",
    "match_wake",
    "stop_phrase_problem",
    "wake_phrase_problem",
    "wake_words",
]

DEFAULT_WAKE_PHRASE = WAKE_PHRASES["en"]
DEFAULT_STOP_PHRASE = STOP_PHRASES["en"]


def wake_words(phrase: str) -> list[str]:
    """*phrase*'s words, lower-cased, accents and punctuation taken off."""
    return folded_words(phrase)


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


def _sounds(text: str) -> str:
    """*text*'s letters spelled roughly as they sound, for comparing a phrase
    the recogniser split or joined in the wrong places: "ck", "c" and "qu" as
    the k they say, "d" as "t" (a recogniser hears one for the other at a word
    boundary), "y" as "i", and every doubled letter once."""
    for spelled, said in _SOUNDS:
        text = text.replace(spelled, said)
    collapsed: list[str] = []
    for letter in text:
        if not collapsed or collapsed[-1] != letter:
            collapsed.append(letter)
    return "".join(collapsed)


_SOUNDS = (
    ("ck", "k"),
    ("qu", "kw"),
    ("c", "k"),
    ("ph", "f"),
    ("x", "ks"),
    ("z", "s"),
    ("d", "t"),
    ("y", "i"),
)


def _joined_match(heard: list[str], wanted: list[str]) -> int | None:
    """The words the wake phrase used when the recogniser cut it differently.

    Moonshine and Whisper hear "Quill dictate" said at an ordinary pace as
    "Quilt it take", "Quiltic tape" or "Quilty take" -- every sound there, the
    word boundaries in the wrong places (measured 2026-10-26: ten of twenty
    synthesised samples). A word-by-word match cannot see that. So the start of
    the phrase is compared **as one run of sounds** against the wake phrase's,
    allowing one difference in every five letters, and with the first word
    still having to sound like the wake phrase's first word. "Will it take
    long" and "Kill it today" open the right way and are still too far from
    the rest of it to wake anything. A one-word phrase (the command word) is
    allowed no difference at all here, so "will" and "kill" never become it.
    """
    target = _sounds("".join(wanted))
    limit = len(target) // 5
    first = wanted[0]
    opening = heard[0]
    if not (
        _same_word(opening, first)
        or _same_word(opening[: len(first)], first)
        # "Kill" and "will" for "Quill": one sound apart, where Soundex's first
        # letter and the spelling's two edits both miss it.
        or levenshtein(_sounds(opening), _sounds(first)) <= 1
    ):
        return None
    best: tuple[int, int] | None = None
    for used in range(1, min(len(heard), len(wanted) + 2) + 1):
        distance = levenshtein(_sounds("".join(heard[:used])), target)
        if distance <= limit and (best is None or distance < best[0]):
            best = (distance, used)
    return None if best is None else best[1]


def match_wake(heard: list[str], phrase: str) -> int | None:
    """How many of *heard*'s words the wake phrase used, or ``None`` if absent.

    *heard* is the phrase's words, lower-cased and stripped of punctuation.
    Word by word first, each word forgiven as :func:`_same_word` says; then,
    for a phrase the recogniser split or joined in the wrong places, the
    opening sounds as one run (:func:`_joined_match`). The command word
    (:mod:`~quill.core.windows_dictation.command_mode`) and the stop phrase
    are matched here too, so the three forgive alike.
    """
    wanted = wake_words(phrase)
    if not wanted or not heard:
        return None
    if len(heard) >= len(wanted) and all(
        _same_word(said, want) for said, want in zip(heard, wanted, strict=False)
    ):
        return len(wanted)
    return _joined_match(heard, wanted)


def is_stop_phrase(heard: list[str], phrase: str) -> bool:
    """Whether *heard* is the stop phrase and nothing else."""
    return bool(heard) and match_wake(heard, phrase) == len(heard)
