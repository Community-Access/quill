"""The 2026-10-05 dictation pass in QUILL Lite, through the handlers the menu
binds: hold-to-talk on Ctrl+F11, the live preview in the status cell, talking
to the AI, More Dictation Settings, OpenAI's consent and My Dictation
Instructions. QUILL runs the same mixins (test_dictation_parity.py).
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.apps.lite_window_dictation import dictation_cell
from quill.core.windows_dictation import RecognizedPhrase, words_from_text
from quill.ui import windows_dictation_commands as shared
from quill.ui import windows_dictation_hold as hold_module


class FakeRecognizer:
    def __init__(self, controller: Any) -> None:
        self.controller = controller
        self.stopped = 0
        self.finished = 0

    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        self.stopped += 1

    def finish(self) -> None:
        self.finished += 1

    def discard(self) -> None:
        pass

    def hear(self, text: str) -> None:
        self.controller.on_speech_started()
        self.controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text))


@pytest.fixture
def made(monkeypatch):
    made: list[FakeRecognizer] = []

    def make(controller: Any, _preferences: Any) -> FakeRecognizer:
        made.append(FakeRecognizer(controller))
        return made[-1]

    monkeypatch.setattr(shared, "_make_recognizer", make)
    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    monkeypatch.setattr(hold_module, "_HOLD", hold_module.HoldToTalk())
    return made


@pytest.fixture
def window(lite_window, monkeypatch):
    holder: dict[str, Any] = {}
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: holder["focus"]))
    win = lite_window("", cursor=0)
    holder["focus"] = win.control
    win.focus = holder
    return win


class Keyboard:
    def __init__(self) -> None:
        self.down = False
        self.now = 1000.0


@pytest.fixture
def keyboard(monkeypatch):
    keys = Keyboard()
    monkeypatch.setattr(hold_module.time, "monotonic", lambda: keys.now)
    monkeypatch.setattr(wx, "GetKeyState", lambda _code: keys.down)
    monkeypatch.setattr(wx, "CallLater", lambda *_a, **_k: None)
    return keys


def test_holding_ctrl_f11_talks_until_it_is_let_go(window, made, keyboard):
    keyboard.down = True
    window.cmd_toggle_dictation()
    assert window.dictation_active()
    window.cmd_toggle_dictation()  # Windows repeating the held key
    window.cmd_toggle_dictation()
    assert window.dictation_active() and len(made) == 1
    controller = shared._controller
    keyboard.now += 0.6
    window._dictation_poll(controller)
    controller.on_speech_started()  # still talking as the key comes up
    keyboard.down = False
    window._dictation_poll(controller)
    assert made[0].finished == 1  # the last phrase is kept
    made[0].hear("last words")
    controller.on_finished()
    assert window.control.GetValue() == "Last words"
    assert not window.dictation_active()


def test_a_quick_press_leaves_dictation_on(window, made, keyboard):
    keyboard.down = True
    window.cmd_toggle_dictation()
    keyboard.now += 0.2
    keyboard.down = False
    window._dictation_poll(shared._controller)
    assert window.dictation_active()
    window.cmd_toggle_dictation()  # a second press turns it off
    assert not window.dictation_active()


def test_with_hold_switched_off_letting_go_does_not_stop(window, made, keyboard):
    window.app.settings.windows_dictation_hold_to_talk = False
    keyboard.down = True
    window.cmd_toggle_dictation()
    keyboard.now += 2.0
    keyboard.down = False
    window._dictation_poll(shared._controller)
    assert window.dictation_active()


def test_the_words_heard_so_far_show_in_the_status_cell(window, made, keyboard):
    window.cmd_toggle_dictation()
    controller = shared._controller
    controller.on_speech_started()
    controller.on_partial("Can you send")
    assert window.dictation_state_text() == "Dictation: hearing: Can you send"
    assert dictation_cell(window) == "Hearing: Can you send"  # its capitals kept
    assert window.control.GetValue() == ""
    made[0].hear("can you send it")
    assert window.control.GetValue() == "Can you send it"


def test_talking_to_the_ai_sends_at_the_pause(window, made, keyboard, monkeypatch):
    monkeypatch.setattr(wx, "CallAfter", lambda function, *args: function(*args))
    box = type(window.control)("")  # the fixture's own control, as the AI message box
    sent: list[str] = []
    box._quill_dictation_profile = "ai"
    box._quill_dictation_after_phrase = lambda: sent.append(box.GetValue())
    window.focus["focus"] = box
    window.cmd_dictation_into(box)
    assert shared._controller.preferences.profile == "ai"
    made[0].hear("um what is the weather")
    assert sent == ["What is the weather"]  # fillers gone on the AI profile
    window.app.settings.windows_dictation_ai_send = "enter"
    made[0].hear("and tomorrow")
    assert len(sent) == 1


def test_escape_while_the_reply_is_read_listens_at_once(window, made, keyboard):
    box = type(window.control)("")
    window.focus["focus"] = box
    window.cmd_dictation_into(box)
    window._dictation_mute_for_reply("A reply of a few words.", box)
    assert shared._controller.muted
    assert window._dictation_cancel_phrase()
    assert not shared._controller.muted
    assert "Listening." in window.announcements


def test_more_settings_and_openai_consent_reach_the_settings(window, monkeypatch):
    from quill.ui import windows_dictation_dialog as dialogs

    class Settings:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def apply(self, settings: Any) -> None:
            settings.windows_dictation_engine = "openai"
            settings.windows_dictation_openai_consent = True
            settings.windows_dictation_openai_model = "gpt-transcribe"

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            pass

    monkeypatch.setattr(dialogs, "WindowsDictationDialog", Settings)
    monkeypatch.setattr(shared.WindowsDictationMixin, "_dictation_run_modal", lambda *_a: wx.ID_OK)
    window.cmd_dictation_settings()
    settings = window.app.settings
    assert settings.windows_dictation_engine == "openai"
    assert settings.windows_dictation_openai_model == "gpt-transcribe"


def test_my_dictation_instructions_open_from_settings(window, monkeypatch):
    from quill.ui import windows_dictation_dialog as dialogs

    class Settings:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def apply(self, _settings: Any) -> None:
            pass

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            pass

    monkeypatch.setattr(dialogs, "WindowsDictationDialog", Settings)
    monkeypatch.setattr(
        shared.WindowsDictationMixin,
        "_dictation_run_modal",
        lambda *_a: dialogs.EDIT_INSTRUCTIONS,
    )
    before = window.app.saved_settings
    window.cmd_dictation_settings()
    path = window.app.data_dir / "dictation-instructions.md"
    assert path.exists() and window.app.saved_settings == before + 1
    assert window.app.opened[-1][0][0] == path


def test_tidy_dictated_text_sends_my_instructions(window, monkeypatch):
    path = window.app.data_dir / "dictation-instructions.md"
    path.write_text("- Write numbers as digits.\n", encoding="utf-8")
    sent = window._with_dictation_instructions("we need twelve chairs")
    assert "Write numbers as digits." in sent and "we need twelve chairs" in sent
