"""GH-R-113 and GH-R-083: Workbench results through the shared action-feedback channels.

A failure gets the error tone and is always said; an action that landed gets
the task-complete tone, and is always said when it carries a number; a bare
acknowledgement follows the setting like the editors' Ctrl+C; everything else
is said with no tone.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.outcome_feedback import Outcome, Plan, classify, plan
from quill.core.sound_events import SoundEvent

PACK = frozenset({str(SoundEvent.ERROR), str(SoundEvent.TASK_COMPLETE)})
DONE = str(SoundEvent.TASK_COMPLETE)
ERROR = str(SoundEvent.ERROR)


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("Could not save: GitHub said 422.", Outcome.FAILURE),
        ("GitHub did not accept it: name taken.", Outcome.FAILURE),
        ("That did not work: timed out.", Outcome.FAILURE),
        ("Saved the title.", Outcome.DONE),
        ("Created bug.", Outcome.DONE),
        ("Watching owner/repo for new releases.", Outcome.DONE),
        ("Watch removed.", Outcome.DONE),
        ("Open a repository first.", Outcome.INFORMATION),
        ("There is nothing to undo.", Outcome.INFORMATION),
        ("GitHub lists no jobs for this run.", Outcome.INFORMATION),
        ("Something nobody planned for", Outcome.INFORMATION),
    ],
)
def test_each_sentence_is_placed_by_how_it_starts(text: str, kind: Outcome) -> None:
    assert classify(text) is kind


def test_a_failure_is_always_said_and_gets_the_error_tone_where_sounds_are_on() -> None:
    text = "Could not create bug: 403."
    assert plan(text, "sound", has_sound=PACK) == Plan(ERROR, True)
    assert plan(text, "both", has_sound=PACK) == Plan(ERROR, True)
    assert plan(text, "speech", has_sound=PACK) == Plan("", True)
    assert plan(text, "silent", has_sound=PACK) == Plan("", True)


def test_a_count_is_always_said() -> None:
    text = "Saved 3 changes to Issue #12."
    assert plan(text, "sound", has_sound=PACK) == Plan(DONE, True)
    assert plan(text, "silent", has_sound=PACK) == Plan("", True)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("sound", Plan(DONE, False)),
        ("speech", Plan("", True)),
        ("both", Plan(DONE, True)),
        ("silent", Plan("", False)),
        ("nonsense", Plan(DONE, False)),
    ],
)
def test_a_bare_acknowledgement_follows_the_setting(mode: str, expected: Plan) -> None:
    assert plan("Saved.", mode, has_sound=PACK) == expected


def test_a_tone_the_pack_lacks_becomes_words() -> None:
    assert plan("Saved.", "sound", has_sound=frozenset()) == Plan("", True)
    assert plan("Could not save.", "sound", has_sound=frozenset()) == Plan("", True)


def test_information_is_said_with_no_tone_in_every_mode() -> None:
    for mode in ("sound", "speech", "both", "silent"):
        assert plan("Open a repository first.", mode, has_sound=PACK) == Plan("", True)


def test_the_workbench_plays_and_says_through_the_frame(monkeypatch) -> None:
    from quill.ui import github_workbench_feedback, sound_manager

    played: list[str] = []
    monkeypatch.setattr(sound_manager, "post_sound", played.append)
    monkeypatch.setattr(sound_manager, "get_loaded_events", lambda: PACK)
    monkeypatch.setattr(sound_manager, "action_feedback_mode", lambda: "sound")

    class Frame:
        def __init__(self) -> None:
            self.said: list[str] = []
            self.last_result = ""

        def _say(self, text: str) -> None:
            self.said.append(text)
            self.last_result = text

    frame = Frame()
    announced: list[Any] = []
    github_workbench_feedback.say_result(frame, announced.append, "Saved.")
    assert (played, frame.said, frame.last_result) == ([DONE], [], "Saved.")
    github_workbench_feedback.say_result(frame, announced.append, "Could not save: 500.")
    assert played[-1] == ERROR and frame.said == ["Could not save: 500."]
    github_workbench_feedback.say_result(None, announced.append, "Open a repository first.")
    assert announced == ["Open a repository first."]


def test_the_sound_manager_keeps_the_setting_it_was_given() -> None:
    from quill.ui import sound_manager

    class Settings:
        action_feedback = "both"
        sound_enabled = False

    manager = object.__new__(sound_manager._SoundManager)

    class Player:
        def set_muted(self, _muted: bool) -> None:
            pass

    manager.player = Player()  # type: ignore[attr-defined]
    manager._set_keepalive = lambda _on: None  # type: ignore[method-assign]
    try:
        manager.apply_settings(Settings())  # type: ignore[arg-type]
        assert sound_manager.action_feedback_mode() == "both"
    finally:
        Settings.action_feedback = "sound"
        manager.apply_settings(Settings())  # type: ignore[arg-type]
