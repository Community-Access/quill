"""Review Dictation's window (D-2): built in memory, driven through its controls.

The host is a stand-in that records what the window asks of it; the AI is a
fake that answers when told. No window is shown to anybody and nothing is sent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.windows_dictation.review_session import load_rescue  # noqa: E402
from quill.core.windows_dictation.vocabulary import Command  # noqa: E402
from quill.ui import dictation_review_frame as frame_module  # noqa: E402
from quill.ui.dictation_review_frame import TITLE, ReviewBoxDocument, ReviewDesk  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    from quill.ui.app_context_help import ensure_help_provider

    app = wx.App()
    ensure_help_provider(wx)  # without it SetHelpText stores nothing
    yield app


class _Ai:
    def __init__(self, reason: str = "") -> None:
        self._reason = reason
        self.prompts: list[str] = []
        self.pending: list[Any] = []

    def reason(self) -> str:
        return self._reason

    def provider(self) -> str:
        return "OpenAI, with your own key"

    def consented(self) -> bool:
        return True

    def agree(self) -> None:
        pass

    def ask(self, prompt: str, on_done: Any, on_error: Any) -> object:
        self.prompts.append(prompt)
        self.pending.append(on_done)
        return object()

    def cancel(self, request: Any) -> None:
        pass


class _Host:
    def __init__(self, tmp_path: Path, ai: _Ai | None) -> None:
        self.ai = ai
        self.said: list[str] = []
        self.targets: list[Any] = []
        self.inserted: list[tuple[str, str]] = []
        self.rescue = tmp_path / "dictation-review.json"
        self.context_on = False

    def _review_parent(self) -> Any:
        return None

    def _review_say(self, text: str) -> None:
        self.said.append(text)

    def _review_ai(self) -> Any:
        return self.ai

    def _review_rescue_path(self) -> Path:
        return self.rescue

    def _review_my_instructions(self) -> str:
        return ""

    def _review_context(self) -> str:
        return "a formal letter"

    def _review_context_offered(self) -> bool:
        return True

    def _review_context_setting(self) -> bool:
        return self.context_on

    def _review_set_context(self, on: bool) -> None:
        self.context_on = on

    def _review_retarget(self, document: Any) -> None:
        self.targets.append(document)

    def _review_insert(self, text: str, original: str) -> None:
        self.inserted.append((text, original))

    def _review_mute(self, seconds: float) -> None:
        pass


@pytest.fixture
def desk(wx_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(frame_module, "defer", lambda fn, *args: fn(*args))
    monkeypatch.setattr(frame_module, "take_focus", lambda _frame: None)
    made = ReviewDesk(_Host(tmp_path, _Ai()))
    yield made
    if made.frame:
        made.frame.Destroy()


def test_the_words_are_in_a_real_editable_multiline_text(desk: ReviewDesk) -> None:
    desk.open("see you next Thursday")
    frame = desk.frame
    assert frame is not None and frame.GetTitle() == TITLE
    assert frame.text.IsMultiLine() and frame.text.IsEditable()
    assert frame.text.GetValue() == "see you next Thursday"
    assert isinstance(desk.host.targets[-1], ReviewBoxDocument)  # dictation goes here now
    assert desk.host.said == []  # GATE-13: the reader says the title and the text
    for control in (frame.text, frame.instruction, frame.send, frame.talk, frame.insert):
        assert control.GetHelpText(), control  # F1


def test_typing_an_instruction_sends_the_words_and_says_what_changed(desk: ReviewDesk) -> None:
    desk.open("um so see you next Thursday")
    frame = desk.frame
    assert frame is not None
    frame.instruction.SetValue("make it shorter")
    frame._send()
    ai = desk.host.ai
    assert "um so see you next Thursday" in ai.prompts[0]
    assert "a formal letter" not in ai.prompts[0]  # context only when turned on
    ai.pending.pop()("See you Thursday.")
    assert frame.text.GetValue() == "See you Thursday."
    assert frame.changes.GetValue() == desk.host.said[-1]
    assert frame.instruction.GetValue() == ""


def test_the_context_goes_only_when_its_box_is_ticked(desk: ReviewDesk) -> None:
    desk.open("hello")
    frame = desk.frame
    assert frame is not None and frame.context is not None
    frame.context.SetValue(True)
    frame.instruction.SetValue("more formal")
    frame._send()
    assert "This document is: a formal letter" in desk.host.ai.prompts[0]


def test_insert_hands_both_texts_to_the_host_and_closes(desk: ReviewDesk) -> None:
    desk.open("see you")
    frame = desk.frame
    assert frame is not None
    frame.text.SetValue("see you soon")  # typed: still what was said, no change yet
    frame._run("insert")
    assert desk.host.inserted == [("see you soon", "see you soon")]
    assert not desk.is_open()
    assert desk.host.targets[-1] is None  # dictation back where it was going
    assert not desk.host.rescue.exists()


def test_voice_commands_reach_the_open_window(desk: ReviewDesk) -> None:
    desk.open("hello there")
    desk.command(Command.REVIEW_READ)
    assert desk.host.said[-1] == "hello there"
    desk.command(Command.REVIEW_INSERT)
    assert desk.host.inserted == [("hello there", "hello there")]


def test_close_keeps_the_words_and_the_next_open_brings_them_back(desk: ReviewDesk) -> None:
    desk.open("keep these words")
    frame = desk.frame
    assert frame is not None
    frame.Close()
    assert not desk.is_open()
    assert "kept" in desk.host.said[-1]
    kept = load_rescue(desk.host.rescue)
    assert kept is not None and kept.current == "keep these words"
    desk.open("")
    assert desk.frame is not None and desk.frame.text.GetValue() == "keep these words"


def test_with_ai_off_the_window_still_edits_and_inserts(
    wx_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(frame_module, "take_focus", lambda _frame: None)
    desk = ReviewDesk(_Host(tmp_path, _Ai("AI help is switched off.")))
    desk.open("hello")
    frame = desk.frame
    assert frame is not None
    try:
        assert not frame.instruction.IsEnabled() and not frame.send.IsEnabled()
        assert frame.text.IsEditable() and frame.insert.IsEnabled()
        assert "switched off" in frame.status.GetValue()
    finally:
        frame.Destroy()


def test_escape_discards_and_nothing_is_inserted(desk: ReviewDesk) -> None:
    desk.open("throw this away")
    frame = desk.frame
    assert frame is not None
    frame._escape()
    assert not desk.is_open()
    assert desk.host.inserted == []
    assert desk.host.said[-1] == "Discarded. Nothing was written."


def test_dictation_into_the_box_is_one_undo_step_a_phrase(desk: ReviewDesk) -> None:
    desk.open("")
    frame = desk.frame
    assert frame is not None
    box = ReviewBoxDocument(frame.text)
    box.insert("Dear Sam")
    assert frame.text.GetValue() == "Dear Sam"
    assert frame.conversation is not None
    assert frame.conversation.session.original == "Dear Sam"  # EVT_TEXT kept it
