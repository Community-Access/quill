"""The command word, the Command Key and command mode (D-1, 2026-10-15).

Run against the shared controller with fakes: an editor-like document, and the
external document QUILL Transcribe and Inkwell type through, with an injector
that fails the test if a command is ever typed. Nothing here needs a microphone;
the live checks in Notepad, Word and Edge are listed in the dictation design
record, section 18.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.command_mode import (
    COMMAND_MODE_SAID,
    DEFAULT_COMMAND_PREFIX,
    DICTATION_MODE_SAID,
    coerce_timeout,
    command_prefix_problem,
    escape_literal_prefix,
    not_a_command,
    split_prefix,
)
from quill.core.windows_dictation.command_mode_mixin import PAUSED_REFUSAL
from quill.core.windows_dictation.ports import DictationState, Moment
from quill.core.windows_dictation.settings_fields import DictationSettings, load_fields
from quill.ui.windows_dictation_external import ExternalDocument

# -- the stand-ins --------------------------------------------------------------- #


class _Document:
    def __init__(self) -> None:
        self.text = ""
        self.inserted: list[str] = []
        self.reason = ""

    def unavailable_reason(self, *, writing: bool) -> str:
        return self.reason if writing else ""

    def context(self) -> tuple[str, str]:
        return self.text, ""

    def selection(self) -> tuple[int, int]:
        return len(self.text), len(self.text)

    def select(self, start: int, end: int) -> None:
        pass

    def insert(self, text: str) -> tuple[int, int]:
        self.inserted.append(text)
        start = len(self.text)
        self.text += text
        return start, len(self.text)

    def text_between(self, start: int, end: int) -> str:
        return self.text[start:end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.text = self.text[:start] + text + self.text[end:]
        return start, start + len(text)

    def line_bounds(self) -> tuple[int, int]:
        return 0, len(self.text)

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        return False


class _Handle:
    def __init__(self, seconds: float, callback: Callable[[], None]) -> None:
        self.seconds = seconds
        self.callback = callback
        self.stopped = False

    def Stop(self) -> None:  # noqa: N802 - wx.CallLater's shape
        self.stopped = True


class _Feedback:
    def __init__(self, *, clip: bool = True, timers: bool = True) -> None:
        self.clip = clip
        self.cues: list[Moment] = []
        self.said: list[str] = []
        self.shown: list[str] = []
        self.states = 0
        self.pending: list[_Handle] = []
        if not timers:
            self.call_later = None  # type: ignore[assignment]

    def has_cue(self, moment: Moment) -> bool:
        return self.clip

    def cue(self, moment: Moment) -> None:
        self.cues.append(moment)

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        self.shown.append(text)

    def state_changed(self, state: Any) -> None:
        self.states += 1

    def show_commands(self) -> None:
        self.said.append("(the commands list)")

    def call_later(self, seconds: float, callback: Callable[[], None]) -> _Handle:
        handle = _Handle(seconds, callback)
        self.pending.append(handle)
        return handle

    def fire(self) -> None:
        """Every timer still running goes off."""
        pending, self.pending = self.pending, []
        for handle in pending:
            if not handle.stopped:
                handle.callback()


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _controller(
    document: Any = None, *, feedback: _Feedback | None = None, **preferences: Any
) -> tuple[DictationController, Any, _Feedback, _Clock]:
    document = document if document is not None else _Document()
    feedback = feedback or _Feedback()
    settings = DictationPreferences(phrase_feedback="silent", announce=False, **preferences)
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: settings,
    )
    clock = _Clock()
    controller._clock = clock
    controller.start()
    feedback.cues.clear()
    feedback.said.clear()
    return controller, document, feedback, clock


def _say(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text))


# -- the rules ---------------------------------------------------------------------- #


def test_the_command_word_is_matched_forgivingly_and_only_first() -> None:
    assert split_prefix(["QUILL", "scratch", "that"], "QUILL") == (True, ("scratch", "that"))
    assert split_prefix(["quil,", "scratch", "that"], "QUILL") == (True, ("scratch", "that"))
    assert split_prefix(["quills", "undo"], "QUILL")[0] is True
    assert split_prefix(["i", "told", "quill", "about", "it"], "QUILL")[0] is False
    assert split_prefix(["kill", "the", "lights"], "QUILL")[0] is False
    assert split_prefix(["will", "you"], "QUILL")[0] is False
    assert split_prefix(["quill", "undo"], "")[0] is False  # no command word at all


def test_a_poor_command_word_is_refused_with_a_reason() -> None:
    assert command_prefix_problem(DEFAULT_COMMAND_PREFIX) == ""
    assert command_prefix_problem("") == ""  # none: the Command Key only
    assert command_prefix_problem("Jarvis") == ""
    assert "ordinary sentences" in command_prefix_problem("there")
    assert "ordinary sentences" in command_prefix_problem("scratch")  # a command word
    assert "ordinary sentences" in command_prefix_problem("computer")
    assert "longer" in command_prefix_problem("Bo")
    assert "two at most" in command_prefix_problem("hey there my quill")
    assert "My Words" in command_prefix_problem("Kubernetes", ["kubernetes"])


def test_the_timeout_is_held_between_five_and_thirty_seconds() -> None:
    assert coerce_timeout(8) == 8
    assert coerce_timeout(2) == 5
    assert coerce_timeout(90) == 30
    assert coerce_timeout("twelve") == 8
    assert (
        load_fields({"windows_dictation_command_timeout": 1})["windows_dictation_command_timeout"]
        == 5
    )
    fields = load_fields({})
    assert fields["windows_dictation_command_prefix"] == "QUILL"
    assert fields["windows_dictation_command_prefix_required"] is False
    assert DictationSettings().windows_dictation_command_timeout == 8


def test_literal_before_the_command_word_writes_it() -> None:
    phrase = RecognizedPhrase(words_from_text("literal quill is my editor"))
    escaped = escape_literal_prefix(phrase, "QUILL")
    assert [word.display for word in escaped.words] == ["QUILL", "is", "my", "editor"]


# -- the command word in a session --------------------------------------------------- #


def test_quill_scratch_that_takes_the_last_phrase_back() -> None:
    controller, document, feedback, _clock = _controller()
    _say(controller, "hello world")
    _say(controller, "quill scratch that")
    assert document.text == ""
    assert feedback.cues == [Moment.COMMAND_ON]  # the tone; the result is what is said
    assert "quill" not in "".join(document.inserted).lower()


def test_bare_commands_work_with_strict_mode_off() -> None:
    controller, document, _feedback, _clock = _controller()
    _say(controller, "hello world")
    _say(controller, "scratch that")
    assert document.text == ""


def test_strict_mode_types_a_bare_command_as_words() -> None:
    controller, document, _feedback, _clock = _controller(command_prefix_required=True)
    _say(controller, "hello")
    _say(controller, "scratch that")
    assert "scratch that" in document.text.lower()
    _say(controller, "quill scratch that")
    assert "scratch that" not in document.text.lower()


def test_strict_mode_still_stops_and_still_leaves_spelling() -> None:
    controller, _document, _feedback, _clock = _controller(command_prefix_required=True)
    _say(controller, "quill start spelling")
    assert controller.spelling
    _say(controller, "stop spelling")
    assert not controller.spelling
    _say(controller, "stop dictation")
    assert not controller.active


def test_not_a_command_types_nothing_and_type_that_writes_it() -> None:
    controller, document, feedback, _clock = _controller()
    _say(controller, "quill pancakes for breakfast")
    assert document.inserted == []
    assert Moment.ERROR in feedback.cues
    assert feedback.said == [not_a_command("QUILL")]
    assert "say QUILL type that" in feedback.said[0]
    _say(controller, "quill type that")
    assert document.text.strip().lower().startswith("pancakes for breakfast")
    feedback.said.clear()
    _say(controller, "quill type that")  # once only
    assert feedback.said == ["Nothing to type. Say it again first."]


def test_the_name_mid_phrase_is_dictated() -> None:
    controller, document, _feedback, _clock = _controller(command_prefix_required=True)
    _say(controller, "I told Quill about it")
    assert "Quill about it" in document.text


def test_literal_quill_is_written_in_a_session() -> None:
    controller, document, feedback, _clock = _controller()
    _say(controller, "literal quill is open")
    assert document.text.startswith("QUILL is open")
    assert feedback.said == []


def test_a_search_that_finds_nothing_writes_nothing_after_the_word() -> None:
    controller, document, feedback, _clock = _controller()
    _say(controller, "quill select the elephant")
    assert document.inserted == []
    assert "Not found." in feedback.said
    _say(controller, "select the elephant")  # without the word: written, as before
    assert "elephant" in document.text


def test_the_command_word_alone_waits_for_one_command() -> None:
    controller, document, feedback, _clock = _controller()
    _say(controller, "hello there")
    _say(controller, "quill")
    assert controller.command_mode_text == "Waiting for a command"
    assert feedback.cues == [Moment.COMMAND_ON]
    _say(controller, "scratch that")
    assert document.text == ""
    assert controller.command_mode_text == ""
    _say(controller, "scratch that")  # one command only: now it is the bare command
    assert document.text == ""


# -- command mode -------------------------------------------------------------------- #


def test_command_mode_takes_commands_without_the_word_until_dictation_mode() -> None:
    controller, document, feedback, _clock = _controller()
    _say(controller, "one")
    _say(controller, "two")
    _say(controller, "quill command mode")
    assert controller.command_mode_text == "Command mode"
    assert feedback.said == [COMMAND_MODE_SAID]
    assert feedback.cues == [Moment.COMMAND_ON]
    _say(controller, "scratch that")
    _say(controller, "scratch that")
    assert document.text == ""
    _say(controller, "not a command at all")
    assert document.inserted == ["One", " two"]  # nothing more was typed
    _say(controller, "dictation mode")
    assert controller.command_mode_text == ""
    assert feedback.said[-1] == DICTATION_MODE_SAID
    _say(controller, "three")
    assert "Three" in document.text or "three" in document.text


def test_command_mode_times_out_with_a_tone_and_no_words() -> None:
    controller, document, feedback, _clock = _controller(command_timeout=8)
    _say(controller, "quill command mode")
    assert feedback.pending and feedback.pending[-1].seconds == 8
    feedback.said.clear()
    feedback.cues.clear()
    feedback.fire()
    assert feedback.cues == [Moment.COMMAND_OFF]
    assert feedback.said == []
    assert controller.command_mode_text == ""
    _say(controller, "scratch that idea")
    assert "scratch that idea" in document.text.lower()


def test_without_a_timer_the_next_phrase_notices_the_timeout() -> None:
    controller, document, feedback, clock = _controller(feedback=_Feedback(timers=False))
    _say(controller, "quill command mode")
    clock.now += 9
    _say(controller, "pancakes")
    assert Moment.COMMAND_OFF in feedback.cues
    assert "Pancakes" in document.text or "pancakes" in document.text


def test_a_command_keeps_command_mode_open() -> None:
    controller, _document, feedback, clock = _controller(feedback=_Feedback(timers=False))
    _say(controller, "quill command mode")
    clock.now += 6
    _say(controller, "caps on")
    clock.now += 6
    assert controller.command_mode
    _say(controller, "caps off")
    assert controller.command_mode
    assert Moment.COMMAND_OFF not in feedback.cues


def test_no_tone_in_the_pack_says_the_words_instead() -> None:
    controller, _document, feedback, _clock = _controller(feedback=_Feedback(clip=False))
    controller.command_key()
    assert feedback.said == ["Say a command."]
    feedback.fire()
    assert feedback.said[-1] == DICTATION_MODE_SAID


# -- the Command Key ------------------------------------------------------------------ #


def test_the_command_key_once_twice_and_again() -> None:
    controller, document, feedback, _clock = _controller()
    _say(controller, "hello")
    controller.command_key()
    assert controller.command_mode_text == "Waiting for a command"
    controller.command_key()
    assert controller.command_mode_text == "Command mode"
    assert COMMAND_MODE_SAID in feedback.said
    controller.command_key()
    assert controller.command_mode_text == ""
    assert feedback.said[-1] == DICTATION_MODE_SAID
    assert Moment.COMMAND_OFF in feedback.cues
    controller.command_key()
    _say(controller, "scratch that")
    assert document.text == ""


def test_the_command_key_does_nothing_while_dictation_is_off() -> None:
    controller, _document, feedback, _clock = _controller()
    controller.stop()
    feedback.cues.clear()
    controller.command_key()
    assert controller.command_mode_text == ""
    assert feedback.cues == []


def test_stopping_ends_command_mode_and_a_new_session_starts_clean() -> None:
    controller, _document, _feedback, _clock = _controller()
    _say(controller, "quill command mode")
    _say(controller, "stop dictation")
    assert controller.command_mode_text == ""
    controller.start()
    assert controller.command_mode_text == ""


def test_the_status_follows_command_mode() -> None:
    controller, _document, feedback, _clock = _controller()
    before = feedback.states
    _say(controller, "quill command mode")
    assert feedback.states > before


# -- never typed ---------------------------------------------------------------------- #


def _notepad(**preferences: Any) -> tuple[DictationController, list[str], list[int], _Feedback]:
    typed: list[str] = []
    erased: list[int] = []
    forbidden = {"on": False}

    def type_text(text: str, *_args: Any) -> bool:
        assert not forbidden["on"], f"a command was typed: {text!r}"
        typed.append(text)
        return True

    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: ("notepad", 1, "edit"),
        type_text=type_text,
        backspace=lambda count: erased.append(count) or True,
    )
    controller, _doc, feedback, _clock = _controller(document, **preferences)
    _say(controller, "dear Sam")
    forbidden["on"] = True  # from here on, the injector fails the test if called
    return controller, typed, erased, feedback


@pytest.mark.parametrize(
    "said",
    [
        "quill caps on",
        "quill pancakes for breakfast",
        "quill select the cat",
        "quill copy all",
        "quill",
        "quill command mode",
        "quill dictation mode",
        "quill what can I say",
        "quill no space on",
        "quill read that",
        "quill type that",
    ],
)
def test_a_command_utterance_never_reaches_the_injector(said: str) -> None:
    controller, typed, _erased, _feedback = _notepad(command_prefix_required=True)
    _say(controller, said)
    assert typed == ["Dear Sam"]


def test_quill_scratch_that_in_notepad_only_erases() -> None:
    controller, typed, erased, _feedback = _notepad(command_prefix_required=True)
    _say(controller, "quill scratch that")
    assert typed == ["Dear Sam"] and erased == [len("Dear Sam")]


def test_bare_scratch_that_in_notepad_with_strict_mode_is_typed() -> None:
    typed: list[str] = []
    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: ("notepad", 1, "edit"),
        type_text=lambda text, *_a: typed.append(text) or True,
        backspace=lambda count: True,
    )
    controller, _doc, _feedback, _clock = _controller(document, command_prefix_required=True)
    _say(controller, "scratch that")
    assert typed == ["Scratch that"]


def test_command_mode_in_notepad_types_nothing() -> None:
    controller, typed, _erased, _feedback = _notepad()
    _say(controller, "quill command mode")
    for said in ("caps on", "pancakes", "select the cat", "caps off"):
        _say(controller, said)
    assert typed == ["Dear Sam"]


# -- paused for its field ------------------------------------------------------------ #


class _Holding(_Document):
    holds_phrases = True
    pause_advice = ""


def test_a_command_word_while_paused_is_answered_and_never_held() -> None:
    document = _Holding()
    controller, _doc, feedback, _clock = _controller(document)
    document.reason = "The field changed."
    _say(controller, "first words")
    assert controller.state is DictationState.PAUSED
    held = controller.held_count
    _say(controller, "quill pancakes")
    assert controller.held_count == held
    assert feedback.said[-1] == PAUSED_REFUSAL
    _say(controller, "quill scratch that")
    assert controller.held_count == held - 1


def test_transcribe_turns_strict_mode_on_and_the_editors_leave_it_off() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings
    from quill.core.transcribe.settings import TRANSCRIBE_DICTATION_DEFAULTS
    from quill.core.windows_dictation.anywhere import settings_from

    assert QuillSettings().windows_dictation_command_prefix_required is False
    assert LiteSettings().windows_dictation_command_prefix_required is False
    transcribe = settings_from(dict(TRANSCRIBE_DICTATION_DEFAULTS))
    assert transcribe.windows_dictation_command_prefix_required is True
    preferences = DictationPreferences.from_settings(transcribe)
    assert preferences.command_prefix == "QUILL" and preferences.command_prefix_required
    assert replace(preferences, command_timeout=12).command_timeout == 12
