"""The windows 2026-10-15 changed, built in memory with no real input.

The conversation window saves as it goes and opens a saved conversation again;
Saved AI Conversations lists, opens and deletes; the pad offers where the
answer goes and the Chat Key's focus; the result window offers Review Changes;
the Prompt Library, run on the free AI, fills the prompt and closes rather than
sending anything itself. Every control these added has its F1 sentence.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.core.ai import sessions  # noqa: E402
from quill.core.ai.gateway_client import GatewayLimits  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    from quill.ui.app_context_help import ensure_help_provider

    app = shared_wx_app()
    # SetHelpText stores nothing without a help provider; the apps install one
    # at activation, and so must a test that reads the sentences back.
    ensure_help_provider()
    yield app


class _ChatService:
    own_key_active = False
    limits = GatewayLimits(max_input_tokens=3000)

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""

    def converse(self, prompt, chunks, history, *, on_done, on_error) -> None:  # noqa: ANN001
        on_done(f"Reply to {prompt}", SimpleNamespace(monthly_cap=90, daily_cap=19), 0)


def _chat(store, said: list[str], **kwargs: Any) -> Any:
    from quill.ui.hosted_ai_chat import AiChatFrame

    return AiChatFrame(None, _ChatService(), announce=said.append, store=store, **kwargs)


def _send(frame: Any, text: str) -> None:
    frame._message.SetValue(text)
    frame._send()


def _labels(window: Any) -> list[str]:
    found: list[str] = []
    for child in window.GetChildren():
        if isinstance(child, wx.Button):
            found.append(child.GetLabel())
        found.extend(_labels(child))
    return found


# --------------------------------------------------------------------------- #
# Saved conversations
# --------------------------------------------------------------------------- #


def test_the_conversation_is_saved_as_it_goes(wx_app, tmp_path) -> None:
    said: list[str] = []
    frame = _chat(tmp_path, said)
    try:
        _send(frame, "What is a haiku?")
        _send(frame, "And a tanka?")
        listed = sessions.list_sessions(directory=tmp_path)
        assert len(listed) == 1
        assert listed[0].title == "What is a haiku?"
        assert listed[0].turn_count == 4
        assert "Saved Con&versations..." in _labels(frame)
        assert "saved on this computer" in frame._about.GetValue()
    finally:
        frame.Destroy()


def test_a_follow_up_saves_the_answer_it_started_from(wx_app, tmp_path) -> None:
    from quill.core.ai.hosted_chat import Conversation

    seed = Conversation()
    seed.add("user", "Summarize this: a long passage")
    seed.add("assistant", "A summary.")
    frame = _chat(tmp_path, [], conversation=seed)
    try:
        _send(frame, "Shorter?")
        listed = sessions.list_sessions(directory=tmp_path)
        assert listed[0].turn_count == 4
    finally:
        frame.Destroy()


def test_new_conversation_starts_a_new_saved_one(wx_app, tmp_path) -> None:
    frame = _chat(tmp_path, [])
    try:
        _send(frame, "First?")
        frame._start_over()
        _send(frame, "Second?")
        assert len(sessions.list_sessions(directory=tmp_path)) == 2
    finally:
        frame.Destroy()


def test_a_saved_conversation_opens_and_carries_on(wx_app, tmp_path) -> None:
    saved = sessions.record_exchange(None, "Old question?", "Old answer.", directory=tmp_path)
    said: list[str] = []
    frame = _chat(tmp_path, said)
    try:
        frame.load_session(saved)
        assert "You: Old question?" in frame._transcript.GetValue()
        assert said[-1].startswith("Opened Old question?, 2 messages.")
        _send(frame, "New question?")
        # Added to the same saved conversation, not a new one.
        listed = sessions.list_sessions(directory=tmp_path)
        assert len(listed) == 1 and listed[0].turn_count == 4
    finally:
        frame.Destroy()


def test_without_a_store_nothing_is_saved_and_no_button(wx_app, tmp_path) -> None:
    frame = _chat(None, [])
    try:
        _send(frame, "Hello?")
        assert "Saved Con&versations..." not in _labels(frame)
    finally:
        frame.Destroy()


def test_the_saved_list_opens_and_deletes(wx_app, tmp_path, monkeypatch) -> None:
    from quill.ui import hosted_ai_saved_chats as saved

    first = sessions.record_exchange(None, "One?", "1.", directory=tmp_path)
    sessions.record_exchange(None, "Two?", "2.", directory=tmp_path)
    said: list[str] = []
    dialog = saved.SavedConversationsDialog(None, tmp_path, said.append)
    try:
        assert dialog._list.GetCount() == 2
        assert dialog._list.GetHelpText()
        # Delete the row for "One?" after a yes.
        index = [row.session_id for row in dialog._rows].index(first.session_id)
        dialog._list.SetSelection(index)
        monkeypatch.setattr(saved, "show_modal_dialog", lambda *_a, **_k: wx.ID_YES)
        dialog._on_delete()
        assert [row.title for row in dialog._rows] == ["Two?"]
        assert said[-1] == "Deleted."
        # Open what is left.
        monkeypatch.setattr(dialog, "EndModal", lambda code: None)
        dialog._on_open()
        assert dialog.chosen is not None and dialog.chosen.title == "Two?"
    finally:
        dialog.Destroy()


def test_the_empty_list_says_so_and_offers_nothing(wx_app, tmp_path) -> None:
    from quill.ui.hosted_ai_saved_chats import SavedConversationsDialog

    dialog = SavedConversationsDialog(None, tmp_path, lambda _t: None)
    try:
        assert dialog._list.GetString(0) == "No saved conversations yet."
        assert not dialog._open.IsEnabled()
        dialog._on_open()
        assert dialog.chosen is None
    finally:
        dialog.Destroy()


# --------------------------------------------------------------------------- #
# The pad and the result window
# --------------------------------------------------------------------------- #


class _PadService:
    own_key_active = False
    direct = False
    limits = GatewayLimits(max_input_tokens=3000)

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""


def _pad(**kwargs: Any) -> Any:
    from quill.ui.hosted_ai_pad import AiPadFrame

    return AiPadFrame(
        None,
        _PadService(),
        document_text="Some text.",
        selection="",
        position=0,
        announce=lambda _t: None,
        on_result=lambda *_a: None,
        **kwargs,
    )


def test_the_pad_offers_where_the_answer_goes_and_remembers_it(wx_app) -> None:
    chosen: list[str] = []
    pad = _pad(delivery="clipboard", on_delivery=chosen.append)
    try:
        assert pad._delivery is not None
        assert pad._delivery.GetStringSelection() == "The clipboard"
        assert pad._delivery.GetHelpText()
        pad._delivery.SetSelection(1)
        pad._delivery.ProcessWindowEvent(wx.CommandEvent(wx.wxEVT_CHOICE, pad._delivery.GetId()))
        assert chosen == ["cursor"]
    finally:
        pad.Destroy()


def test_a_host_with_nowhere_to_keep_it_gets_no_chooser(wx_app) -> None:
    pad = _pad()
    try:
        assert pad._delivery is None
    finally:
        pad.Destroy()


def test_the_chat_key_opens_on_a_general_question(wx_app) -> None:
    pad = _pad(initial_action="ask", focus_prompt=True)
    try:
        assert pad._action_id == "ask"
        assert pad._question.IsShown()
    finally:
        pad.Destroy()


def test_the_result_window_offers_review_changes(wx_app) -> None:
    from quill.ui.hosted_ai_pad import AiResultFrame

    reviewed: list[str] = []
    frame = AiResultFrame(
        None,
        action="rewrite",
        text="Better.",
        used="",
        on_replace=lambda _t: None,
        on_insert=None,
        on_again=None,
        announce=lambda _t: None,
        on_review=reviewed.append,
    )
    try:
        assert "Re&view Changes..." in _labels(frame)
        button = next(
            child
            for child in frame.GetChildren()[0].GetChildren()
            if isinstance(child, wx.Button) and child.GetLabel() == "Re&view Changes..."
        )
        assert button.GetHelpText()
        button.ProcessWindowEvent(wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId()))
        assert reviewed == ["Better."]
    finally:
        frame.Destroy()


# --------------------------------------------------------------------------- #
# Review AI Changes and the Prompt Library
# --------------------------------------------------------------------------- #


def test_the_review_window_has_help_on_every_control(wx_app) -> None:
    from quill.ui.ai_diff_review_dialog import DiffReviewDialog

    review = DiffReviewDialog(
        None,
        title="Review AI Changes",
        original_text="The quick brown fox.\nSecond line.",
        revised_text="The fast brown fox.\nSecond line changed.",
        on_apply=lambda _t: None,
    )
    try:
        assert review.hunk_list.GetHelpText()
        assert review.details.GetHelpText()
        assert review.apply_button.GetHelpText()
    finally:
        review.dialog.Destroy()


def test_the_library_on_the_free_ai_fills_and_closes(wx_app, tmp_path, monkeypatch) -> None:
    from quill.core.prompt_library import PromptLibrary
    from quill.core.settings import Settings
    from quill.ui.prompt_library_dialog import PromptLibraryDialog

    library = PromptLibrary(tmp_path / "prompts.json")
    dialog = PromptLibraryDialog(None, library, Settings(), selection="hello there", hosted=True)
    ended: list[int] = []
    monkeypatch.setattr(dialog.dialog, "EndModal", ended.append)
    try:
        # No "no model configured" warning: the free AI chooses its own.
        assert dialog._status.GetLabel() == ""
        dialog._listbox.SetSelection(0)
        dialog._on_run(None)
        name, text = dialog.chosen
        assert name == dialog._prompts[0].name
        assert "hello there" in text and "{selection}" not in text
        assert ended == [wx.ID_OK]
        assert dialog._btn_run.GetHelpText()
    finally:
        dialog.close()
