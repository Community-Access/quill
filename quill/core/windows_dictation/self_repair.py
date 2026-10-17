"""Correcting yourself mid-sentence, and the three named dictation styles (D-20).

**Self-repair.** People correct themselves as they talk: "meet on Thursday,
no, Friday", "send it to Ana, I mean Maria". With **Fix it when I correct
myself** on, a repair marker -- "no", "I mean", "sorry", "no I mean", "scratch
that word" -- said *between two things of the same kind* keeps the second and
drops the first and the marker. The kinds are deliberately few and easy to
recognise without a model:

* a day of the week ("Thursday", also "today", "tomorrow", "tonight");
* a month (May and March only with a capital, since "may" and "march" are verbs);
* a number, as digits or one number word ("two", "twenty", "hundred");
* a name from My Words (the Vocabulary list), matched without case.

The rule is conservative on purpose. It only looks at the one word right before
the marker and the one right after; the word before may carry a comma but never
a full stop or a question mark, so a question answered in one breath ("Is it
Thursday? No, Friday.") is left alone. Anything that does not fit is written
exactly as said: "no, I don't think so" has nothing before the marker, and "I
said no, Friday" has a verb before it. Local and deterministic: no model, no
network. Off by default.

**The named styles.** Dictation Settings offers three names for choices that
already exist, so a person can pick a style instead of three check boxes:

* **Verbatim**: every word as said; no filler removal, no repair.
* **Clean**: filler words removed, self-repair on.
* **Polished**: Clean, plus Review Dictation first with "Polish my dictation"
  allowed (D-2 and the opt-in AI pass) -- offered only when AI is on. Nothing is
  ever sent to an AI without the person asking and agreeing.

Any other mix is shown as "Your own mix", and nothing is changed.

Pure and wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from quill.core.windows_dictation.parser import RecognizedPhrase, RecognizedWord

__all__ = [
    "CUSTOM_STYLE",
    "STYLE_CHOICES",
    "STYLE_FIELDS",
    "kind_of",
    "repair_text",
    "self_repair",
    "style_choices",
    "style_of",
]

#: Repair markers, as folded words, longest first so "no i mean" wins over "no".
MARKERS: tuple[tuple[str, ...], ...] = (
    ("scratch", "that", "word"),
    ("no", "i", "mean"),
    ("i", "mean"),
    ("no",),
    ("sorry",),
)

_DAYS = frozenset({
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "today",
    "tomorrow",
    "tonight",
    "yesterday",
})
_MONTHS = frozenset({
    "january",
    "february",
    "april",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
})
#: Months that are also ordinary verbs: a month only when written with a capital.
_VERB_MONTHS = frozenset({"may", "march"})
_NUMBER_WORDS = frozenset({
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
})
_DIGITS = re.compile(r"^\d+(?:[.,:]\d+)?$")
_EDGE = re.compile(r"^[^\w']+|[^\w']+$")
#: What the word before a marker may end with: nothing, or a comma or dash.
_SOFT_ENDS = ("", ",", "-", chr(0x2014), chr(0x2013))


def _core(display: str) -> str:
    return _EDGE.sub("", display)


def kind_of(display: str, names: frozenset[str] = frozenset()) -> str:
    """``day``, ``month``, ``number``, ``name`` or ``""`` for *display*."""
    core = _core(display)
    if not core:
        return ""
    folded = core.lower()
    if folded in _DAYS:
        return "day"
    if folded in _MONTHS or (folded in _VERB_MONTHS and core[:1].isupper()):
        return "month"
    if _DIGITS.match(core) or folded in _NUMBER_WORDS:
        return "number"
    if folded in names:
        return "name"
    return ""


def _trailing(display: str) -> str:
    core = _core(display)
    if not core:
        return display.strip()
    return display[display.rfind(core) + len(core) :].strip()


def _marker_at(folded: list[str], start: int) -> int:
    """How many words the marker at *start* takes; 0 for none."""
    for marker in MARKERS:
        if tuple(folded[start : start + len(marker)]) == marker:
            return len(marker)
    return 0


def _repair_words(
    words: list[RecognizedWord], names: frozenset[str]
) -> list[RecognizedWord] | None:
    """*words* with one repair made, or ``None`` when there was none to make."""
    # Punctuation-only tokens (a comma reported as its own word) are skipped
    # over when looking for the neighbours, and dropped with the marker.
    folded = [_core(word.display).lower() for word in words]
    for index in range(1, len(words)):
        length = _marker_at(folded, index)
        if not length:
            continue
        before = index - 1
        while before >= 0 and not folded[before]:
            if words[before].display.strip() not in _SOFT_ENDS:
                break
            before -= 1
        if before < 0 or not folded[before]:
            continue
        after = index + length
        while after < len(words) and not folded[after]:
            after += 1
        if after >= len(words):
            continue
        first, second = words[before], words[after]
        if _trailing(first.display) not in _SOFT_ENDS:
            continue  # "Thursday? No, Friday." is an answer, not a repair
        # The last marker word must not end a sentence either ("no." then a new one).
        if _trailing(words[index + length - 1].display) not in _SOFT_ENDS:
            continue
        kind = kind_of(first.display, names)
        if not kind or kind != kind_of(second.display, names):
            continue
        kept = second
        if first.display[:1].isupper() and second.display[:1].islower():
            shown = second.display[:1].upper() + second.display[1:]
            kept = RecognizedWord(second.lexical, shown)
        return [*words[:before], kept, *words[after + 1 :]]
    return None


def self_repair(phrase: RecognizedPhrase, names: Iterable[str] = ()) -> RecognizedPhrase:
    """*phrase* with each "X, no, Y" of one kind written as Y. Unchanged otherwise."""
    folded_names = frozenset(" ".join(name.split()).lower() for name in names if name.strip())
    words = list(phrase.words)
    changed = False
    for _attempt in range(8):  # a phrase rarely holds more than one or two
        repaired = _repair_words(words, folded_names)
        if repaired is None:
            break
        words, changed = repaired, True
    if not changed:
        return phrase
    return RecognizedPhrase(
        tuple(words), text=" ".join(word.display for word in words), confidence=phrase.confidence
    )


def repair_text(text: str, names: Iterable[str] = ()) -> str:
    """:func:`self_repair` over plain text, for tests and file transcription."""
    words = tuple(RecognizedWord(word.lower(), word) for word in text.split())
    phrase = RecognizedPhrase(words, text=text)
    repaired = self_repair(phrase, names)
    return text if repaired is phrase else repaired.text


# -- the three named styles ------------------------------------------------- #

CUSTOM_STYLE = "custom"

#: (value, label) for the chooser. "custom" is shown only when the fields match
#: none of the named styles, and choosing it changes nothing.
STYLE_CHOICES: tuple[tuple[str, str], ...] = (
    ("verbatim", "Verbatim: every word as I say it"),
    ("clean", "Clean: no filler words, and my corrections fixed"),
    ("polished", "Polished: Clean, then review, and polish with AI when I ask"),
    (CUSTOM_STYLE, "Your own mix of the settings below"),
)

#: What each named style sets. Polished also sends dictation to review first.
STYLE_FIELDS: dict[str, dict[str, bool]] = {
    "verbatim": {
        "windows_dictation_remove_fillers": False,
        "windows_dictation_self_repair": False,
        "windows_dictation_polish": False,
    },
    "clean": {
        "windows_dictation_remove_fillers": True,
        "windows_dictation_self_repair": True,
        "windows_dictation_polish": False,
    },
    "polished": {
        "windows_dictation_remove_fillers": True,
        "windows_dictation_self_repair": True,
        "windows_dictation_polish": True,
        "windows_dictation_review_first": True,
    },
}


def style_of(values: Mapping[str, object]) -> str:
    """The named style *values* (settings field -> value) amount to, or ``custom``."""
    for style, wanted in STYLE_FIELDS.items():
        if all(bool(values.get(name, False)) == on for name, on in wanted.items()):
            return style
    return CUSTOM_STYLE


def style_choices(*, ai_on: bool) -> tuple[tuple[str, str], ...]:
    """The chooser's rows: Polished only when AI is on."""
    return tuple(row for row in STYLE_CHOICES if ai_on or row[0] != "polished")
