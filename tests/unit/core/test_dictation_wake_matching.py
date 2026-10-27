"""The wake phrase as the built-in engines actually write it (2026-10-26).

Reported against QUILL Lite 1.2.0: the chosen engine loads, and "Quill dictate"
is never heard. Twenty samples of "Quill dictate" and "Quill dictate dear Sam",
synthesised with the four Windows voices at two speeds and decoded by the
shipped Moonshine, Whisper and Nemotron models, came back like the strings
below. Nemotron spelled it right every time; Moonshine (the default engine) and
Whisper split or joined it in the wrong places in ten of the twenty -- "Quilt
it take", "Quiltic tape", "Quilty take" -- and the word-by-word matcher refused
every one, so standby ran and nothing ever woke.
"""

from __future__ import annotations

import logging

import pytest

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.command_mode import split_prefix
from quill.core.windows_dictation.wake import (
    DEFAULT_WAKE_PHRASE,
    is_stop_phrase,
    match_wake,
    wake_words,
)

#: (what the engine wrote, how many of its words the wake phrase used).
#: Verbatim engine output from the 2026-10-26 run, plus the spellings the
#: brief names.
HEARD_AS_THE_WAKE_PHRASE = [
    ("Quilt it take dear Sam", 3),  # Whisper and Moonshine
    ("Quilt it Tate", 3),  # Whisper
    ("Quilt it tate", 3),  # Moonshine
    ("Quiltic tape", 2),  # Moonshine
    ("Quilty take deer sim", 2),  # Moonshine
    ("Quilt dictate.", 2),  # Whisper
    ("Quild dictate dear sam", 2),  # Moonshine
    ("Quil dictate Dear Sam.", 2),  # Whisper
    ("Quill dictate.", 2),  # Nemotron
    ("Quilldictate", 1),  # joined into one word
    ("Quill, dictate.", 2),
    ("QUILL DICTATE", 2),
    ("Kill dictate", 2),
    ("Will dictate", 2),
    ("Quail dictate", 2),
    ("Quil dick tate", 3),
]

#: Openings that must not wake anything: ordinary speech near the computer.
NOT_THE_WAKE_PHRASE = [
    "Will it take long",
    "Kill it today",
    "Quickly take it",
    "Quit it",
    "Quilt it is",
    "Quilt it today",
    "Quilting takes time",
    "Quite a tale",
    "Quill the tape",
    "Quilt a cake",
    "Quilted it",
    "Quill",
    "I asked Quill dictate something",
    "what a lovely day it is",
]


@pytest.mark.parametrize(("said", "used"), HEARD_AS_THE_WAKE_PHRASE)
def test_the_engines_spellings_of_the_wake_phrase_are_heard(said: str, used: int) -> None:
    assert match_wake(wake_words(said), DEFAULT_WAKE_PHRASE) == used


@pytest.mark.parametrize("said", NOT_THE_WAKE_PHRASE)
def test_ordinary_openings_do_not_wake(said: str) -> None:
    assert match_wake(wake_words(said), DEFAULT_WAKE_PHRASE) is None


def test_the_english_wake_phrase_is_quill_dictate() -> None:
    preferences = DictationPreferences.from_settings(object())
    assert preferences.wake_phrase == "Quill dictate"


def test_the_command_word_forgives_the_way_the_wake_phrase_does() -> None:
    """command_mode.py matches through match_wake: one rule, not two."""
    assert split_prefix(["quilt", "scratch", "that"], "QUILL") == (True, ("scratch", "that"))
    for common in ("will", "kill", "call"):
        assert split_prefix([common, "scratch", "that"], "QUILL") == (
            False,
            (common, "scratch", "that"),
        )


def test_the_stop_phrase_still_has_to_be_the_whole_phrase() -> None:
    assert is_stop_phrase(wake_words("stop dictation"), "stop dictation")
    assert not is_stop_phrase(wake_words("stop dictation now please"), "stop dictation")


# -- in the controller, standing by ---------------------------------------------- #


class _Recognizer:
    def start(self, microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


class _Document:
    """Appends: enough to see what the wake phrase left to be written."""

    def __init__(self) -> None:
        self.text = ""

    def unavailable_reason(self, *, writing: bool) -> str:
        return ""

    def context(self) -> tuple[str, str]:
        return self.text, ""

    def insert(self, text: str) -> tuple[int, int]:
        start = len(self.text)
        self.text += text
        return start, len(self.text)

    def selection(self) -> tuple[int, int]:
        return len(self.text), len(self.text)


class _Feedback:
    def has_cue(self, moment: object) -> bool:
        return False

    def cue(self, moment: object) -> None:
        pass

    def say(self, text: str) -> None:
        pass

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        pass

    def state_changed(self, state: object) -> None:
        pass


def _standing_by() -> tuple[DictationController, _Document]:
    document = _Document()
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,  # type: ignore[arg-type]
        feedback=_Feedback(),  # type: ignore[arg-type]
        preferences=lambda: DictationPreferences(wake_enabled=True),
    )
    controller.arm()
    assert controller.standing_by
    return controller, document


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text))


def test_moonshines_quilt_it_take_wakes_and_writes_the_rest() -> None:
    controller, document = _standing_by()
    _hear(controller, "Quilt it take dear Sam")
    assert controller.active
    assert document.text == "Dear Sam"


def test_a_hyphenated_wake_phrase_keeps_the_first_dictated_word() -> None:
    """ "Quill-dictate" is one word as written and two as matched: skipping by
    written words threw away "dear"."""
    controller, document = _standing_by()
    _hear(controller, "Quill-dictate dear Sam")
    assert controller.active
    assert document.text == "Dear Sam"


def test_standby_traces_what_it_heard(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """With QUILL_DICTATION_TRACE=1, a wake phrase that is never heard leaves a
    record of what the engine wrote instead -- the one thing a real microphone
    has to tell us."""
    monkeypatch.setenv("QUILL_DICTATION_TRACE", "1")
    controller, _document = _standing_by()
    with caplog.at_level(logging.INFO, logger="quill.core.windows_dictation.controller"):
        _hear(controller, "Will it take long")
    assert "standby: heard 'Will it take long', wake phrase False" in caplog.text
    assert controller.standing_by
