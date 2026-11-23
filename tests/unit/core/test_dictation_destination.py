"""FUX-07 for dictation: the identity of "the field you started in".

QUILL Transcribe and Quill Inkwell's Dictate Anywhere lock the field a session
starts in (:mod:`quill.core.windows_dictation.target_lock`). The lock is only
as good as the identity it compares, so these pin the identity itself
(:func:`quill.ui.windows_dictation_external.control_identity`) and what the
lock does when the identity changes or cannot be read: another field in the
same window, the same program restarted, and Windows unable to say.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.target_lock import LockedTarget
from quill.ui.windows_dictation_external import ExternalDocument, control_identity


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []

    def has_cue(self, moment: Any) -> bool:
        return False

    def cue(self, moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    read_back = say

    def show(self, text: str) -> None:
        pass

    def state_changed(self, state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass


class _Recognizer:
    def start(self, microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


def _session(place: dict[str, Any]) -> tuple[DictationController, list[str]]:
    typed: list[str] = []

    def type_text(text: str) -> bool:
        typed.append(text)
        return True

    inner = ExternalDocument(
        problem=lambda: "",
        where=lambda: place["now"],
        type_text=type_text,
        backspace=lambda _count: True,
    )
    document = LockedTarget(inner, where=lambda: place["now"])
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=_Feedback(),
        preferences=lambda: DictationPreferences(phrase_feedback="silent"),
    )
    controller.start()
    return controller, typed


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


# -- the identity ------------------------------------------------------------ #


def test_two_edit_boxes_without_automation_are_two_fields() -> None:
    """Until 2026-11-23 the last resort was the class name, shared by both."""
    first = control_identity(None, lambda: 101)
    second = control_identity(None, lambda: 202)
    assert first != second


def test_automation_runtime_id_wins_over_a_window_handle() -> None:
    element = SimpleNamespace(runtime_id=(42, 7), native_window_handle=101)
    assert control_identity(element, lambda: 999) == ("uia", (42, 7))


def test_automation_window_handle_comes_before_the_threads() -> None:
    element = SimpleNamespace(runtime_id=(), native_window_handle=101)
    assert control_identity(element, lambda: 999) == ("hwnd", 101)


# -- what the lock does with it ------------------------------------------------ #


def test_the_same_window_after_its_program_restarted_types_nothing() -> None:
    place = {"now": (11, 22, ("hwnd", 101))}
    controller, typed = _session(place)
    place["now"] = (11, 23, ("hwnd", 101))  # same handle, a new process

    _hear(controller, "dear sam")

    assert typed == []
    assert controller.paused_for_target and controller.held_count == 1


def test_a_field_windows_cannot_name_types_nothing_and_keeps_the_words() -> None:
    place: dict[str, Any] = {"now": (11, 22, ("hwnd", 101))}
    controller, typed = _session(place)
    place["now"] = None  # focus_identity's answer when Windows cannot say

    _hear(controller, "dear sam")

    assert typed == []
    assert controller.held_count == 1


def test_coming_back_and_resuming_types_the_kept_words_there() -> None:
    place: dict[str, Any] = {"now": (11, 22, ("hwnd", 101))}
    controller, typed = _session(place)
    place["now"] = (44, 55, ("hwnd", 303))  # Alt+Tab to another program
    _hear(controller, "dear sam")
    place["now"] = (11, 22, ("hwnd", 101))

    assert controller.resume_held()
    assert typed == ["Dear sam"]
