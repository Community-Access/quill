"""The five finer dictation choices: pause, fillers, punctuation, silence, mic test."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from quill.core.windows_dictation.controller import DictationPreferences, DictationState
from quill.core.windows_dictation.options import (
    clean_phrase,
    coerce_pause,
    coerce_silence,
    level_sentence,
    silence_expired,
)
from quill.core.windows_dictation.parser import RecognizedPhrase, words_from_text


def _phrase(text: str) -> RecognizedPhrase:
    return RecognizedPhrase(words_from_text(text), text=text)


def _text(phrase: RecognizedPhrase) -> str:
    return " ".join(word.display for word in phrase.words)


# -- fillers ------------------------------------------------------------------------ #


def test_fillers_go_and_real_words_and_their_punctuation_stay() -> None:
    cleaned = clean_phrase(
        _phrase("Um, I think, uh, we should erm go."),
        remove_fillers=True,
        strip_punctuation=False,
        language="en",
    )
    assert _text(cleaned) == "I think, we should go."


def test_fillers_stay_when_the_choice_is_off() -> None:
    phrase = _phrase("Um, yes.")
    assert clean_phrase(phrase, remove_fillers=False, strip_punctuation=False) is phrase


# -- automatic punctuation off ------------------------------------------------------ #


def test_the_engines_marks_go_and_the_capitals_they_earned_go_with_them() -> None:
    cleaned = clean_phrase(
        _phrase("Hello there. How are you? I'm fine, and I think Sam is too."),
        remove_fillers=False,
        strip_punctuation=True,
    )
    assert _text(cleaned) == "Hello there how are you I'm fine and I think Sam is too"


def test_numbers_and_contractions_survive_the_stripping() -> None:
    cleaned = clean_phrase(
        _phrase("It costs 3.5 dollars, doesn't it?"), remove_fillers=False, strip_punctuation=True
    )
    assert _text(cleaned) == "It costs 3.5 dollars doesn't it"


def test_preferences_strip_only_for_the_engines_that_punctuate() -> None:
    off = DictationPreferences(engine="moonshine", auto_punctuation=False)
    assert off.strips_punctuation and not off.engine_punctuates
    windows = DictationPreferences(engine="windows", auto_punctuation=False)
    assert not windows.strips_punctuation and not windows.engine_punctuates
    assert DictationPreferences(engine="whisper").engine_punctuates


# -- through the controller --------------------------------------------------------- #


def test_a_dictated_phrase_loses_its_fillers_and_engine_marks() -> None:
    from tests.unit.core.test_windows_dictation import _controller, _hear

    controller, _r, document, _f = _controller(
        preferences=DictationPreferences(remove_fillers=True, auto_punctuation=False)
    )
    controller.start()
    _hear(controller, "Um, hello there. How are you")
    assert document.text == "Hello there how are you"


# -- just write what I say ------------------------------------------------------------ #


def _flowing(*phrases: str, **preferences: Any):
    from tests.unit.core.test_windows_dictation import _controller, _hear

    controller, recognizer, document, feedback = _controller(
        preferences=DictationPreferences(continuous=True, **preferences)
    )
    controller.start()
    for phrase in phrases:
        _hear(controller, phrase)
    return controller, recognizer, document, feedback


def test_a_pause_puts_in_no_full_stop_and_the_sentence_runs_on() -> None:
    _c, _r, document, _f = _flowing("I was thinking.", "That we should go.")
    assert document.text == "I was thinking that we should go"


def test_a_pause_plays_nothing_and_reads_nothing_back() -> None:
    from tests.unit.core.test_windows_dictation import Moment

    _c, _r, _d, feedback = _flowing("Hello there.", "And more.")
    assert Moment.PHRASE not in feedback.cues
    assert not any("Hello" in said for said in feedback.said)


def test_commands_are_words_but_the_stop_phrase_still_stops() -> None:
    controller, _r, document, _f = _flowing("I said.", "Scratch that.")
    assert document.text == "I said scratch that"
    from tests.unit.core.test_windows_dictation import _hear

    _hear(controller, "stop dictation")
    assert controller.state is DictationState.OFF


def test_spoken_marks_still_work_and_i_keeps_its_capital() -> None:
    _c, _r, document, _f = _flowing("Well comma", "I think so period")
    assert document.text == "Well, I think so."


def test_the_choice_round_trips() -> None:
    from quill.core.windows_dictation.settings_fields import load_fields

    assert load_fields({})["windows_dictation_continuous"] is False

    class Settings:
        windows_dictation_continuous = True

    assert DictationPreferences.from_settings(Settings()).continuous is True


# -- pause ---------------------------------------------------------------------------- #


def test_pause_lengths_and_their_fallback() -> None:
    assert DictationPreferences(pause="long").pause_seconds > DictationPreferences().pause_seconds
    assert DictationPreferences(pause="short").pause_seconds < DictationPreferences().pause_seconds
    assert coerce_pause("sideways") == "normal"


def test_the_built_in_engines_are_handed_the_pause() -> None:
    from quill.core.windows_dictation import local_recognizer

    recognizer = local_recognizer.LocalDictationRecognizer(
        object(), "moonshine", post=lambda *_a: None, pause_seconds=1.4
    )
    assert recognizer._pause == 1.4


# -- silence -------------------------------------------------------------------------- #


def test_silence_expires_only_when_chosen_and_only_once_the_time_has_passed() -> None:
    assert not silence_expired(0.0, 10_000.0, 0)
    assert not silence_expired(0.0, 299.0, 5)
    assert silence_expired(0.0, 300.0, 5)
    assert coerce_silence("7") == 0 and coerce_silence(5) == 5


def test_the_silence_watch_stops_dictation_and_says_why(monkeypatch) -> None:
    pytest.importorskip("wx")
    from quill.ui import windows_dictation_silence as silence

    class Controller:
        state = DictationState.LISTENING
        preferences = DictationPreferences(silence_minutes=1)

        def __init__(self) -> None:
            self.stopped: list[str] = []

        def stop(self, message: str) -> None:
            self.stopped.append(message)

    monkeypatch.setattr(silence, "_last_heard", 0.0)
    controller = Controller()
    assert not silence.check_silence(controller, 59.0)
    assert silence.check_silence(controller, 61.0)
    assert controller.stopped == ["Dictation off after 1 minute of silence."]


def test_the_silence_watch_leaves_a_phrase_being_written_alone(monkeypatch) -> None:
    pytest.importorskip("wx")
    from quill.ui import windows_dictation_silence as silence

    class Controller:
        state = DictationState.PROCESSING
        preferences = DictationPreferences(silence_minutes=1)

    monkeypatch.setattr(silence, "_last_heard", 0.0)
    assert not silence.check_silence(Controller(), 1_000.0)


# -- microphone test ------------------------------------------------------------------ #


def test_level_sentences_cover_silent_quiet_good_and_loud() -> None:
    assert "almost nothing" in level_sentence(0.0)
    assert "quiet" in level_sentence(0.05)
    assert level_sentence(0.5) == "The microphone is working: sound reached 50 percent."
    assert "very loud" in level_sentence(0.99)


def test_the_microphone_test_records_and_asks_the_engine(monkeypatch) -> None:
    np = pytest.importorskip("numpy")
    from quill.core.windows_dictation import local_recognizer

    fake: Any = types.ModuleType("sounddevice")
    fake.rec = lambda frames, **_kwargs: np.full((frames, 1), 0.4, dtype=np.float32)
    fake.wait = lambda: None
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    monkeypatch.setattr(local_recognizer, "input_device_for", lambda _name: None)
    monkeypatch.setattr(
        local_recognizer, "transcribe", lambda engine, _samples: f"heard by {engine}"
    )

    peak, heard = local_recognizer.record_and_hear("", "moonshine", seconds=0.1)
    assert peak == pytest.approx(0.4) and heard == "heard by moonshine"
    assert local_recognizer.record_and_hear("", "windows", seconds=0.1)[1] == ""


def test_the_five_choices_round_trip_through_saved_settings() -> None:
    from quill.core.windows_dictation.settings_fields import load_fields

    defaults = load_fields({})
    assert defaults["windows_dictation_pause"] == "normal"
    assert defaults["windows_dictation_remove_fillers"] is False
    assert defaults["windows_dictation_auto_punctuation"] is True
    assert defaults["windows_dictation_silence_minutes"] == 0

    class Settings:
        windows_dictation_pause = "long"
        windows_dictation_remove_fillers = True
        windows_dictation_auto_punctuation = False
        windows_dictation_silence_minutes = 10

    preferences = DictationPreferences.from_settings(Settings())
    assert (preferences.pause, preferences.remove_fillers) == ("long", True)
    assert (preferences.auto_punctuation, preferences.silence_minutes) == (False, 10)
