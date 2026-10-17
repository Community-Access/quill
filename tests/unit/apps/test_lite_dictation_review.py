"""Review Dictation in QUILL Lite (D-2), through the handler the menu binds.

The shared review window, the shared controller and QUILL Lite's real document
port; the recogniser is replaced, so no microphone opens, and the AI is a fake.
QUILL reaches the same handler (``test_dictation_parity.py``).
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.windows_dictation import RecognizedPhrase, words_from_text
from quill.ui import dictation_review_frame as frame_module
from quill.ui import windows_dictation_commands as shared
from quill.ui import windows_dictation_review as review
from tests.wx_session import shared_wx_app


class _Recognizer:
    def __init__(self, controller: Any) -> None:
        self.controller = controller

    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass

    def hear(self, text: str) -> None:
        self.controller.on_phrase(RecognizedPhrase(words_from_text(text)))


class _Ai:
    def __init__(self) -> None:
        self.pending: list[Any] = []

    def reason(self) -> str:
        return ""

    def provider(self) -> str:
        return "OpenAI, with your own key"

    def consented(self) -> bool:
        return True

    def agree(self) -> None:
        pass

    def ask(self, prompt: str, on_done: Any, on_error: Any) -> object:
        self.pending.append(on_done)
        return object()

    def cancel(self, request: Any) -> None:
        pass


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app


@pytest.fixture
def window(wx_app, lite_window, monkeypatch: pytest.MonkeyPatch):
    made: list[_Recognizer] = []

    def make(controller: Any, _preferences: Any) -> _Recognizer:
        made.append(_Recognizer(controller))
        return made[-1]

    monkeypatch.setattr(shared, "_make_recognizer", make)
    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    monkeypatch.setattr(review, "_desk", None)
    monkeypatch.setattr(frame_module, "defer", lambda fn, *args: fn(*args))
    monkeypatch.setattr(frame_module, "take_focus", lambda _frame: None)
    win = lite_window("Notes: ", cursor=7)
    focus = {"control": win.control}
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: focus["control"]))
    ai = _Ai()
    win._review_parent = lambda: None
    win._review_ai = lambda: ai
    win.app.settings.windows_dictation_phrase_feedback = "silent"
    yield win, made, ai
    desk = review._desk
    if desk is not None and desk.frame:
        desk.frame.Destroy()


def test_review_dictation_takes_the_last_phrase_and_inserts_once(window) -> None:
    win, made, ai = window
    win.cmd_toggle_dictation()
    made[0].hear("see you next thursday")
    assert win.control.GetValue() == "Notes: see you next thursday"
    win.cmd_dictation_review()
    frame = review._desk.frame
    assert frame is not None
    assert win.control.GetValue() == "Notes: "  # taken back out
    assert frame.text.GetValue() == "see you next thursday"
    made[0].hear("and bring the slides")  # said while reviewing: into the review
    assert win.control.GetValue() == "Notes: "
    assert "bring the slides" in frame.text.GetValue()
    made[0].hear("quill make it shorter")
    ai.pending.pop()("See you Thursday with the slides.")
    assert frame.text.GetValue() == "See you Thursday with the slides."
    assert shared._controller is not None and shared._controller.muted  # the summary is read
    made[0].hear("quill insert it")  # heard while it is read: dropped, never acted on
    assert win.control.GetValue() == "Notes: "
    shared._controller.unmute()  # the reader has finished
    made[0].hear("quill insert it")
    assert win.control.GetValue() == "Notes: See you Thursday with the slides."
    assert "Inserted. Press Control Z to undo." in win.announcements
    win.control.Undo()  # Insert is one undo step
    assert win.control.GetValue() == "Notes: "
    controller = shared._controller
    assert controller is not None
    assert list(controller.recent)[:1] == ["See you Thursday with the slides."]


def test_review_dictation_with_dictation_off_opens_an_empty_review(window) -> None:
    win, _made, _ai = window
    win.cmd_dictation_review()
    frame = review._desk.frame
    assert frame is not None and frame.text.GetValue() == ""
    win.cmd_dictation_review()  # a second press brings the same window forward
    assert review._desk.frame is frame
