"""QUILL Transcribe's target lock: words go into the field dictation started in.

The shared controller, the shared external document and the lock, with every
platform call faked -- nothing is typed for real. The rules under test are the
spec's (sections 7.2, 7.7, 12.2 and 15.1): a focus change pauses, nothing is
written elsewhere, held phrases wait for an explicit resume, and "resume in
this field" checks the new field like a new session.
"""

from __future__ import annotations

from typing import Any

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.ports import DictationState
from quill.core.windows_dictation.target_hold import MAX_HELD, WRITE_FAILED
from quill.core.windows_dictation.target_lock import MOVED, LockedTarget
from quill.ui.windows_dictation_external import ExternalDocument


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.shown: list[str] = []
        self.states: list[Any] = []

    def has_cue(self, moment: Any) -> bool:
        return False

    def cue(self, moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        self.shown.append(text)

    def state_changed(self, state: Any) -> None:
        self.states.append(state)

    def show_commands(self) -> None:
        pass


class _Recognizer:
    def __init__(self) -> None:
        self.stopped = False

    def start(self, microphone: str) -> None:
        pass

    def stop(self) -> None:
        self.stopped = True


class _World:
    """The fake desktop: which field has the focus, and what is unsafe."""

    def __init__(self) -> None:
        self.field: Any = ("notepad", 1, "edit-1")
        self.problem = ""
        self.typed: list[str] = []
        self.accept = True

    def type_text(self, text: str) -> bool:
        if not self.accept:
            return False
        self.typed.append(f"{self.field[2]}:{text}")
        return True

    def backspace(self, count: int) -> bool:
        self.typed.append(f"{self.field[2]}:<{count}>")
        return True


def _session(*, start: bool = True) -> tuple[DictationController, _World, _Feedback, LockedTarget]:
    world = _World()
    inner = ExternalDocument(
        problem=lambda: world.problem,
        where=lambda: world.field,
        type_text=world.type_text,
        backspace=world.backspace,
    )
    document = LockedTarget(inner, where=lambda: world.field, advice="Use Resume.")
    feedback = _Feedback()
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: DictationPreferences(phrase_feedback="silent"),
    )
    if start:
        controller.start()
    return controller, world, feedback, document


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


def test_words_go_into_the_field_the_session_started_in() -> None:
    controller, world, _feedback, document = _session()
    assert document.locked
    _hear(controller, "hello world")
    assert world.typed == ["edit-1:Hello world"]


def test_a_focus_change_pauses_and_types_nothing_anywhere() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "secret plans")
    assert world.typed == []
    assert controller.state is DictationState.PAUSED
    assert controller.active  # paused is still on: the microphone is still open
    assert controller.paused_for_target and controller.held_count == 1
    assert any(MOVED in line and "Use Resume." in line for line in feedback.said)


def test_a_different_control_in_the_same_window_is_a_different_field() -> None:
    controller, world, _feedback, _document = _session()
    world.field = ("notepad", 1, "edit-2")
    _hear(controller, "wrong box")
    assert world.typed == []
    assert controller.paused_for_target


def test_phrases_said_while_paused_are_held_in_order_and_said_once() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    _hear(controller, "two")
    _hear(controller, "three")
    assert controller.held_count == 3
    assert sum("paused" in line.lower() for line in feedback.said) == 1
    assert world.typed == []


def test_resume_back_in_the_first_field_writes_the_held_phrases_there() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    _hear(controller, "two")
    world.field = ("notepad", 1, "edit-1")
    assert controller.resume_held()
    assert world.typed == ["edit-1:One", "edit-1: two"]
    assert controller.state is DictationState.LISTENING
    assert not controller.paused_for_target
    assert feedback.said[-1] == "Resumed. 2 phrases written."


def test_resume_refuses_while_the_focus_is_still_somewhere_else() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    assert not controller.resume_held()
    assert world.typed == []
    assert controller.paused_for_target and controller.held_count == 1
    assert "Resume in This Field" in feedback.said[-1]


def test_resume_in_this_field_moves_the_session_on_purpose() -> None:
    controller, world, feedback, document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    assert controller.resume_held(here=True)
    assert world.typed == ["edit-9:One"]
    assert feedback.said[-1] == "Resumed in this field. 1 phrase written."
    _hear(controller, "two")
    assert world.typed[-1] == "edit-9: two"
    assert document.on_locked_field()


def test_resume_in_this_field_checks_the_new_field_like_a_new_session() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("bank", 3, "password")
    _hear(controller, "one")
    world.problem = "That is a password field, so nothing is typed there."
    assert not controller.resume_held(here=True)
    assert world.typed == []
    assert feedback.said[-1] == "That is a password field, so nothing is typed there."
    assert controller.paused_for_target


def test_a_field_that_becomes_unsafe_pauses_rather_than_typing() -> None:
    controller, world, _feedback, _document = _session()
    world.problem = "That program is running as administrator."
    _hear(controller, "one")
    assert world.typed == []
    assert controller.paused_for_target
    assert "administrator" in controller.hold_reason


def test_discard_drops_the_held_phrases_and_stays_paused() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    _hear(controller, "two")
    assert controller.discard_held() == 2
    assert controller.held_count == 0
    assert controller.paused_for_target
    assert feedback.said[-1].startswith("Discarded 2 phrases.")
    world.field = ("notepad", 1, "edit-1")
    assert controller.resume_held()
    assert world.typed == []


def test_scratch_that_while_paused_takes_back_the_last_held_phrase() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    _hear(controller, "two")
    _hear(controller, "scratch that")
    assert controller.held_count == 1
    assert world.typed == []
    assert feedback.said[-1].startswith("Took back the last held phrase.")


def test_stopping_while_paused_says_what_was_never_written() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    _hear(controller, "two")
    controller.stop()
    assert not controller.active
    assert controller.held_count == 0 and not controller.paused_for_target
    assert "2 phrases held while paused were not written" in feedback.said[-1]
    assert world.typed == []


def test_saying_stop_dictation_while_paused_stops() -> None:
    controller, world, _feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    _hear(controller, "stop dictation")
    assert not controller.active
    assert world.typed == []


def test_other_commands_while_paused_are_answered_not_obeyed() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    _hear(controller, "new paragraph")
    assert world.typed == []
    assert controller.held_count in (1, 2)  # a layout word is words, not a command


def test_the_microphone_coming_back_never_resumes_a_field_pause() -> None:
    controller, world, _feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    controller.on_microphone_back()
    assert controller.state is DictationState.PAUSED
    assert controller.paused_for_target


def test_held_phrases_have_a_ceiling() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    for _ in range(MAX_HELD + 5):
        _hear(controller, "word")
    assert controller.held_count == MAX_HELD
    assert any("no more are kept" in line for line in feedback.shown)


def test_shut_down_drops_held_phrases_silently() -> None:
    controller, world, feedback, _document = _session()
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "one")
    said = len(feedback.said)
    controller.shut_down()
    assert controller.held_count == 0 and not controller.paused_for_target
    assert len(feedback.said) == said
    assert not controller.microphone_open


def test_a_partial_typing_is_never_reported_as_written() -> None:
    controller, world, feedback, document = _session()
    document.write_failure = "Part of that phrase may be missing."  # type: ignore[attr-defined]
    world.accept = False
    _hear(controller, "one")
    assert not controller.active
    assert feedback.said[-1] == "Part of that phrase may be missing."


def test_without_a_document_message_the_old_sentence_is_kept() -> None:
    controller, world, feedback, _document = _session()
    world.accept = False
    _hear(controller, "one")
    assert feedback.said[-1] == WRITE_FAILED


def test_scratch_that_never_erases_in_another_field() -> None:
    controller, world, _feedback, _document = _session()
    _hear(controller, "first try")
    world.field = ("mail", 2, "edit-9")
    _hear(controller, "scratch that")
    assert not any(":<" in line for line in world.typed)


def test_a_session_locks_afresh_each_time_it_starts() -> None:
    controller, world, _feedback, document = _session()
    controller.stop()
    world.field = ("mail", 2, "edit-9")
    controller.start()
    _hear(controller, "hello")
    assert world.typed == ["edit-9:Hello"]
    assert document.on_locked_field()


def test_resume_when_not_paused_says_so() -> None:
    controller, _world, feedback, _document = _session()
    assert not controller.resume_held()
    assert feedback.said[-1] == "Dictation is not paused."


def test_an_editor_document_still_ends_the_session_as_before() -> None:
    """Only a document that asks for holding gets it: the editors are unchanged."""
    world = _World()
    document = ExternalDocument(
        problem=lambda: world.problem,
        where=lambda: world.field,
        type_text=world.type_text,
        backspace=world.backspace,
    )
    feedback = _Feedback()
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: DictationPreferences(phrase_feedback="silent"),
    )
    controller.start()
    world.problem = "That is a password field."
    _hear(controller, "one")
    assert not controller.active
    assert not controller.paused_for_target


def test_a_where_that_fails_is_never_the_same_field() -> None:
    world = _World()
    inner = ExternalDocument(
        problem=lambda: "", where=lambda: world.field, type_text=world.type_text
    )

    def broken() -> Any:
        raise RuntimeError("UI Automation is gone")

    document = LockedTarget(inner, where=broken)
    assert document.unavailable_reason(writing=False)  # cannot tell: refused
    assert not document.locked
