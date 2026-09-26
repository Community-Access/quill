"""The five finer dictation choices: how long a pause ends a phrase, whether
hesitations are dropped, whether the engine punctuates, when silence stops
dictation, and what a microphone test reports.

Kept out of the controller so each is a small pure function a test can hold
still, and so the controller stays the one place that decides *when* they
apply.

* **Pause before writing.** How long a silence ends a phrase. The built-in
  engines hand it to the voice detector; Windows speech recognition is asked
  for the same length through its ``ComplexResponseSpeed`` property. Slow,
  thoughtful speakers were being cut off mid-thought at the fixed 0.8 seconds.
* **Remove filler words.** "Um", "uh", "erm" dropped before anything is written,
  using the same lists QUILL's other dictation uses
  (:mod:`quill.core.speech.fillers`). Dropped word by word, so a filler never
  takes a real word's punctuation with it.
* **Automatic punctuation.** Moonshine and Whisper punctuate on their own; with
  this off their marks are removed and a sentence runs on until the user says a
  mark, exactly as with Windows speech recognition. A word the engine had
  capitalised only because it followed a removed full stop goes back to lower
  case; "I" and its contractions stay.
* **Stop after silence.** Dictation that has heard nothing for this long stops,
  so a microphone is not left writing in an empty room. Off unless chosen.
* **Just write what I say.** For somebody who talks in one long run -- a rant, a
  story, thinking aloud -- and pauses wherever thought pauses. A pause then does
  nothing at all: no full stop is put in because of it (:func:`flow_on`), no
  tone, no read-back, and no voice command, so "scratch that" said on its own is
  written as words. Only the stop phrase is still obeyed, because there has to
  be a way out by voice. Marks the person says still work.

Pure and wx-free.
"""

from __future__ import annotations

import re

from quill.core.windows_dictation.parser import RecognizedPhrase, RecognizedWord

__all__ = [
    "PAUSE_CHOICES",
    "PAUSE_SECONDS",
    "SILENCE_CHOICES",
    "clean_phrase",
    "coerce_pause",
    "coerce_silence",
    "drop_fillers",
    "drop_punctuation",
    "flow_on",
    "level_sentence",
    "silence_expired",
]

#: (value, label) for the chooser, shortest first.
PAUSE_CHOICES: tuple[tuple[str, str], ...] = (
    ("short", "Short (half a second)"),
    ("normal", "Normal (under a second)"),
    ("long", "Long (about a second and a half)"),
)
PAUSE_SECONDS: dict[str, float] = {"short": 0.5, "normal": 0.8, "long": 1.4}

#: (minutes, label); 0 is never.
SILENCE_CHOICES: tuple[tuple[int, str], ...] = (
    (0, "Never"),
    (1, "After 1 minute"),
    (5, "After 5 minutes"),
    (10, "After 10 minutes"),
)

_ENGINE_MARKS = ".,?!;:" + chr(0x2026)
_SENTENCE_END = (".", "?", "!", chr(0x2026))
_CORE = re.compile(r"[^\w'-]+")


def coerce_pause(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in PAUSE_SECONDS else "normal"


def coerce_silence(value: object) -> int:
    try:
        minutes = int(str(value or 0))
    except ValueError:
        return 0
    return minutes if minutes in dict(SILENCE_CHOICES) else 0


def _phrase(words: list[RecognizedWord], original: RecognizedPhrase) -> RecognizedPhrase:
    return RecognizedPhrase(
        tuple(words), text=" ".join(word.display for word in words), confidence=original.confidence
    )


def drop_fillers(phrase: RecognizedPhrase, fillers: frozenset[str]) -> RecognizedPhrase:
    """*phrase* without its hesitations, word by word."""
    kept = [
        word
        for word in phrase.words
        if _CORE.sub("", (word.lexical or word.display).lower()) not in fillers
    ]
    return phrase if len(kept) == len(phrase.words) else _phrase(kept, phrase)


def drop_punctuation(phrase: RecognizedPhrase) -> RecognizedPhrase:
    """*phrase* without the marks the engine added, and without the capitals
    those marks alone had earned."""
    words: list[RecognizedWord] = []
    after_stop = False
    for word in phrase.words:
        display = word.display.strip(_ENGINE_MARKS)
        if not display:
            after_stop = True
            continue
        keeps_capital = display == "I" or display.startswith(("I'", "I" + chr(0x2019)))
        if after_stop and display[:1].isupper() and not keeps_capital:
            display = display[:1].lower() + display[1:]
        after_stop = word.display.rstrip().endswith(_SENTENCE_END)
        words.append(RecognizedWord(display.lower(), display))
    return _phrase(words, phrase)


def flow_on(phrase: RecognizedPhrase, *, strip_period: bool) -> RecognizedPhrase:
    """*phrase* as the next part of whatever came before it.

    The full stop an engine puts at every pause is taken off the end
    (*strip_period*; a question or exclamation mark is kept, since those are
    rarely a guess), and the capital it gave the phrase's first word only
    because a pause came before it goes too. "I" keeps its capital, and so does
    a word in capitals throughout. At a real sentence start the composer puts a
    capital back.
    """
    words = list(phrase.words)
    if not words:
        return phrase
    if strip_period:
        last = words[-1]
        display = last.display
        if display.endswith(".") and not display.endswith(".."):
            display = display[:-1]
            words[-1] = RecognizedWord(display.lower(), display) if display else last
            if not display:
                words.pop()
    if words:
        first = words[0].display
        keeps = first == "I" or first.startswith(("I'", "I" + chr(0x2019))) or first.isupper()
        if first[:1].isupper() and not keeps:
            lowered = first[:1].lower() + first[1:]
            words[0] = RecognizedWord(lowered.lower(), lowered)
    return _phrase(words, phrase)


def clean_phrase(
    phrase: RecognizedPhrase,
    *,
    remove_fillers: bool,
    strip_punctuation: bool,
    language: str = "",
) -> RecognizedPhrase:
    """Apply the two text choices to *phrase*, fillers first."""
    if remove_fillers:
        from quill.core.speech.fillers import (
            UNIVERSAL_FILLER_WORDS,
            gated_filler_words_for_language,
        )

        fillers = UNIVERSAL_FILLER_WORDS | gated_filler_words_for_language(language)
        phrase = drop_fillers(phrase, fillers)
    if strip_punctuation:
        phrase = drop_punctuation(phrase)
    return phrase


def silence_expired(last_heard: float, now: float, minutes: int) -> bool:
    """Whether *minutes* of silence have passed since *last_heard* (seconds)."""
    return minutes > 0 and now - last_heard >= minutes * 60


def level_sentence(peak: float) -> str:
    """How loud a microphone test was, in words: *peak* is 0.0 to 1.0."""
    percent = round(max(0.0, min(1.0, peak)) * 100)
    if percent < 2:
        return (
            "The microphone heard almost nothing. Check that it is the right one, "
            "that it is not muted, and that Windows lets desktop apps use it."
        )
    if percent < 10:
        return (
            f"The microphone is working but quiet: sound reached {percent} percent. "
            "Speak closer to it."
        )
    if percent > 95:
        return (
            f"The microphone is working but very loud: sound reached {percent} percent. "
            "It may distort."
        )
    return f"The microphone is working: sound reached {percent} percent."
