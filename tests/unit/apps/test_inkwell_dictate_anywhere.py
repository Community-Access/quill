"""Dictate Anywhere: the shared controller typing into another program, through
the external port, with the platform calls faked (nothing is typed for real)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.expansion.settings import InkwellSettings, load_settings, save_settings
from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.ui.windows_dictation_external import ExternalDocument


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


def _session(problem: str = "") -> tuple[DictationController, list[str], dict[str, Any], Any]:
    typed: list[str] = []
    place = {"where": ("notepad", "Edit")}

    def type_text(text: str) -> bool:
        typed.append(text)
        return True

    def backspace(count: int) -> bool:
        typed.append(f"<{count} backspaces>")
        return True

    document = ExternalDocument(
        problem=lambda: problem,
        where=lambda: place["where"],
        type_text=type_text,
        backspace=backspace,
    )
    feedback = _Feedback()
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: DictationPreferences(phrase_feedback="speech"),
    )
    controller.start()
    return controller, typed, place, feedback


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


def test_each_phrase_is_typed_with_dictations_spacing() -> None:
    controller, typed, _place, _feedback = _session()
    _hear(controller, "hello comma world period")
    _hear(controller, "next sentence")
    assert typed == ["Hello, world.", " Next sentence"]


def test_scratch_that_sends_backspaces_while_the_focus_has_not_moved() -> None:
    controller, typed, place, feedback = _session()
    _hear(controller, "first try")
    _hear(controller, "scratch that")
    assert typed[-1] == "<9 backspaces>"
    _hear(controller, "again")
    place["where"] = ("mail", "Edit")
    _hear(controller, "scratch that")
    assert typed[-1] != "<6 backspaces>"
    assert any("left alone" in line for line in feedback.said)


def test_commands_that_need_to_read_the_text_are_refused() -> None:
    controller, typed, _place, feedback = _session()
    _hear(controller, "select the cat")
    assert typed == []
    assert any("QUILL's own documents" in line for line in feedback.said)


def test_a_password_field_is_refused_before_anything_is_heard() -> None:
    controller, typed, _place, feedback = _session("That is a password field.")
    assert not controller.active
    assert "That is a password field." in feedback.said


def test_inkwell_keeps_its_key_and_its_dictation_settings(tmp_path: Path) -> None:
    settings = InkwellSettings()
    settings.dictate_anywhere_hotkey = "Ctrl+Alt+Shift+F2"
    settings.dictation = {"windows_dictation_engine": "whisper", "unrelated": 1}
    save_settings(tmp_path, settings)
    loaded = load_settings(tmp_path)
    assert loaded.dictate_anywhere_hotkey == "Ctrl+Alt+Shift+F2"
    assert loaded.dictation == {"windows_dictation_engine": "whisper"}
