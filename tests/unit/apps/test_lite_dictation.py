"""Tools > Dictation in QUILL Lite, through the handlers the menu binds.

The recogniser is replaced: nothing here opens a microphone. What is exercised
is everything after Windows hands over a phrase -- the shared controller, the
real composer, the document port writing into the window's control, and the
cues and speech the window actually makes.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.sound_events import SoundEvent
from quill.core.windows_dictation import RecognizedPhrase, words_from_text
from quill.core.windows_dictation.controller import DictationStartError
from quill.ui import windows_dictation_commands as shared


class FakeRecognizer:
    def __init__(self, controller: Any, *, fail: str = "") -> None:
        self.controller = controller
        self.fail = fail
        self.microphone: str | None = None
        self.stopped = 0

    def start(self, microphone: str) -> None:
        if self.fail:
            raise DictationStartError(self.fail)
        self.microphone = microphone

    def stop(self) -> None:
        self.stopped += 1

    def hear(self, text: str) -> None:
        self.controller.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture
def recognizers(monkeypatch):
    made: list[FakeRecognizer] = []
    made_preferences: list[Any] = []
    failure = {"message": ""}

    def make(controller: Any, preferences: Any) -> FakeRecognizer:
        made_preferences.append(preferences)
        recognizer = FakeRecognizer(controller, fail=failure["message"])
        made.append(recognizer)
        return recognizer

    monkeypatch.setattr(shared, "_make_recognizer", make)
    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    made_failure = failure
    return made, made_failure


@pytest.fixture
def focused(monkeypatch):
    """Put the focus on whichever control the test names."""
    holder: dict[str, Any] = {"control": None}
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: holder["control"]))
    return holder


def _window(lite_window, focused, text: str = "", cursor: int | None = None):
    win = lite_window(text, cursor=len(text) if cursor is None else cursor)
    win.available_sounds = frozenset(str(event) for event in shared.DICTATION_CUES.values())
    focused["control"] = win.control
    return win


def test_dictation_on_writes_each_phrase_and_reads_it_back(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_phrase_feedback = "both"

    win.cmd_toggle_dictation()

    assert win.dictation_active()
    assert SoundEvent.WINDOWS_DICTATION_ON in win.cues
    assert "Dictation on." in win.announcements
    made[0].hear("hello everyone period new paragraph welcome back")
    assert win.control.GetValue() == "Hello everyone.\n\nWelcome back"
    assert SoundEvent.WINDOWS_DICTATION_PHRASE in win.cues
    # The read-back: the words that went in, not a count and not "inserted".
    assert "Hello everyone. Welcome back" in win.announcements


def test_the_next_phrase_joins_the_last_with_one_space(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused, "Dear Sam")
    win.cmd_toggle_dictation()
    made[0].hear("comma")
    made[0].hear("thank you for the letter period")
    assert win.control.GetValue() == "Dear Sam, thank you for the letter."


def test_sound_only_feedback_does_not_read_back(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_phrase_feedback = "sound"
    win.cmd_toggle_dictation()
    made[0].hear("quiet words")
    assert "Quiet words" not in win.announcements
    assert SoundEvent.WINDOWS_DICTATION_PHRASE in win.cues


def test_scratch_that_removes_exactly_the_last_phrase(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused, "Kept.")
    win.cmd_toggle_dictation()
    made[0].hear("first try")
    made[0].hear("scratch that")
    assert win.control.GetValue() == "Kept."
    assert any(line.startswith("Scratched") for line in win.announcements)


def test_pressing_it_again_stops_and_closes_the_recogniser(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    win.cmd_toggle_dictation()
    assert not win.dictation_active()
    assert made[0].stopped == 1
    assert SoundEvent.WINDOWS_DICTATION_OFF in win.cues
    assert "Dictation off." in win.announcements


def test_the_chosen_microphone_is_the_one_opened(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_microphone = "token-for-headset"
    win.cmd_toggle_dictation()
    assert made[0].microphone == "token-for-headset"


def test_a_start_failure_is_spoken_and_leaves_it_off(lite_window, recognizers, focused):
    _, failure = recognizers
    failure["message"] = "No microphone was found. Connect one and try again."
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    assert not win.dictation_active()
    assert "No microphone was found. Connect one and try again." in win.announcements
    assert SoundEvent.WINDOWS_DICTATION_ERROR in win.cues


def test_a_phrase_heard_after_focus_left_is_not_written(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused, "Safe.")
    win.cmd_toggle_dictation()
    focused["control"] = object()  # a dialog, another window, another program
    made[0].hear("this must go nowhere")
    assert win.control.GetValue() == "Safe."
    assert not win.dictation_active()
    assert made[0].stopped == 1
    assert any("no longer has the focus" in line for line in win.announcements)


class _FakeSettingsDialog:
    answer = wx.ID_CANCEL

    def __init__(self, parent: Any, settings: Any, announce: Any = None) -> None:
        self.settings = settings
        self.destroyed = False

    def apply(self, settings: Any) -> None:
        settings.windows_dictation_microphone = "chosen"
        settings.windows_dictation_phrase_feedback = "speech"

    def Destroy(self) -> None:  # noqa: N802 - wx API shape
        self.destroyed = True


@pytest.fixture
def settings_dialog(monkeypatch):
    from quill.ui import windows_dictation_dialog

    monkeypatch.setattr(windows_dictation_dialog, "WindowsDictationDialog", _FakeSettingsDialog)
    monkeypatch.setattr(
        shared.WindowsDictationMixin,
        "_dictation_run_modal",
        lambda self, dialog, label: _FakeSettingsDialog.answer,
    )
    return _FakeSettingsDialog


def test_dictation_settings_saves_what_ok_chose(lite_window, settings_dialog, focused):
    settings_dialog.answer = wx.ID_OK
    win = _window(lite_window, focused)
    before = win.app.saved_settings
    win.cmd_dictation_settings()
    assert win.app.settings.windows_dictation_microphone == "chosen"
    assert win.app.settings.windows_dictation_phrase_feedback == "speech"
    assert win.app.saved_settings == before + 1


def test_dictation_settings_cancel_changes_nothing(lite_window, settings_dialog, focused):
    settings_dialog.answer = wx.ID_CANCEL
    win = _window(lite_window, focused)
    before = win.app.saved_settings
    win.cmd_dictation_settings()
    assert win.app.settings.windows_dictation_microphone == ""
    assert win.app.saved_settings == before


def test_the_commands_button_opens_the_list(lite_window, settings_dialog, focused, monkeypatch):
    from quill.ui import windows_dictation_dialog as dialogs

    shown: list[str] = []

    class FakeList:
        def __init__(self, _parent: Any, body: str) -> None:
            shown.append(body)

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            pass

    monkeypatch.setattr(dialogs, "DictationCommandsDialog", FakeList)
    settings_dialog.answer = dialogs.SHOW_COMMANDS
    win = _window(lite_window, focused)
    win.cmd_dictation_settings()
    assert shown and "scratch that" in shown[0]


def test_edit_my_words_saves_and_opens_the_file(lite_window, settings_dialog, focused):
    from quill.ui import windows_dictation_dialog as dialogs

    settings_dialog.answer = dialogs.EDIT_WORDS
    win = _window(lite_window, focused)
    before = win.app.saved_settings
    win.cmd_dictation_settings()
    assert win.app.saved_settings == before + 1
    path = win.app.data_dir / "dictation.md"
    assert path.is_file() and "## Replacements" in path.read_text(encoding="utf-8")
    assert win.app.opened[-1][0][0] == path


def test_windows_voice_typing_hands_over_and_opens_no_microphone(
    lite_window, recognizers, focused, monkeypatch
):
    import quill.platform.windows.dictation as windows_dictation

    made, _ = recognizers
    launched: list[bool] = []
    monkeypatch.setattr(
        windows_dictation, "launch_windows_dictation", lambda: launched.append(True)
    )
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_engine = "voice_typing"
    win.cmd_toggle_dictation()
    assert launched == [True]
    assert made == []


def test_the_status_cell_follows_the_state(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    assert win.dictation_state_text() == ""
    win.cmd_toggle_dictation()
    assert win.dictation_state_text() == "Dictation: listening"
    made[0].hear("start spelling")
    assert win.dictation_state_text() == "Dictation: spelling"


def test_my_own_phrases_are_used_while_dictating(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    (win.app.data_dir / "dictation.md").write_text(
        "## Replacements" + chr(10) + "my town => Tucson, Arizona" + chr(10), encoding="utf-8"
    )
    win.cmd_toggle_dictation()
    made[0].hear("I live in my town")
    assert win.control.GetValue() == "I live in Tucson, Arizona"
