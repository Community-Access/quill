"""The wx-free half of D-9 and D-6 (quill/core/transcribe/talk.py)."""

from __future__ import annotations

from typing import Any

from quill.core.transcribe.talk import KeyHeldGate, standby_wanted, status_sentence


class _Controller:
    def __init__(self) -> None:
        self.got: list[Any] = []
        self.active = True

    def on_phrase(self, phrase: Any) -> None:
        self.got.append(phrase)

    def on_finished(self) -> None:
        self.got.append("finished")


def test_phrases_wait_while_the_key_is_held_and_go_in_order() -> None:
    held = {"down": True}
    controller = _Controller()
    gate = KeyHeldGate(controller, held=lambda: held["down"])
    gate.on_phrase("one")
    gate.on_phrase("two")
    assert controller.got == [] and gate.waiting == 2
    held["down"] = False
    gate.on_phrase("three")  # the waiting ones go first
    assert controller.got == ["one", "two", "three"]


def test_the_last_phrase_waits_for_nothing_before_the_stop() -> None:
    held = {"down": True}
    controller = _Controller()
    gate = KeyHeldGate(controller, held=lambda: held["down"])
    gate.on_phrase("one")
    gate.on_finished()
    assert controller.got == ["one", "finished"]


def test_drop_forgets_and_everything_else_passes_through() -> None:
    controller = _Controller()
    gate = KeyHeldGate(controller, held=lambda: True)
    gate.on_phrase("one")
    gate.drop()
    gate.release()
    assert controller.got == []
    assert gate.active is True


def test_standby_only_when_on_allowed_and_not_refused() -> None:
    assert standby_wanted(wake_enabled=True, refused=False, front_allows=True)
    assert not standby_wanted(wake_enabled=False, refused=False, front_allows=True)
    assert not standby_wanted(wake_enabled=True, refused=True, front_allows=True)
    assert not standby_wanted(wake_enabled=True, refused=False, front_allows=False)


def test_the_status_sentence_is_one_sentence_for_every_state() -> None:
    cases = {
        "Ready": "Dictation is off, using Moonshine Tiny.",
        "Listening": "Dictation is listening in Notepad, using Moonshine Tiny.",
        "Hearing you": "Dictation is hearing you in Notepad, using Moonshine Tiny.",
        "Paused, 2 phrases held": (
            "Dictation is paused in Notepad, using Moonshine Tiny, with 2 phrases held."
        ),
        "Command mode": "Dictation is in command mode in Notepad, using Moonshine Tiny.",
        "Listening for your wake phrase": (
            "Dictation is listening for your wake phrase, using Moonshine Tiny."
        ),
        "Listening. Speech goes to OpenAI.": (
            "Dictation is listening in Notepad, using Moonshine Tiny."
        ),
    }
    for state, expected in cases.items():
        held = 2 if state.startswith("Paused") else 0
        said = status_sentence(state=state, program="Notepad", model="Moonshine Tiny", held=held)
        assert said == expected, state
        assert said.count(".") == 1
