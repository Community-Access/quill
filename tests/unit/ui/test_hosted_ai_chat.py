"""The AI Conversation window, and the two doors into it.

Focus lives in the message box; each reply is added to the transcript and read
aloud, because the transcript does not have focus. On the free service the
history sent is trimmed to the ordinary limit, and the window says so -- once --
when a long conversation starts forgetting its beginning.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.ai.gateway_client import GatewayLimits  # noqa: E402
from quill.core.ai.hosted_chat import Conversation  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


class _Service:
    def __init__(self, *, own_key: bool = False, dropped: int = 0, max_input: int = 3000) -> None:
        self.own_key_active = own_key
        self.limits = GatewayLimits(max_input_tokens=max_input)
        self.sent: list[tuple[str, list[str], list[dict[str, str]]]] = []
        self.dropped = dropped
        self.reason = ""

    def unavailable_reason(self, _feature: str = "") -> str:
        return self.reason

    def converse(self, prompt, chunks, history, *, on_done, on_error) -> None:  # noqa: ANN001
        self.sent.append((prompt, chunks, history))
        on_done(f"Reply to {prompt}", SimpleNamespace(monthly_cap=90, daily_cap=19), self.dropped)


def _frame(service: _Service, said: list[str], **kwargs: Any) -> Any:
    from quill.ui.hosted_ai_chat import AiChatFrame

    return AiChatFrame(None, service, announce=said.append, **kwargs)


def _say(frame: Any, text: str) -> None:
    frame._message.SetValue(text)
    frame._send()


def test_a_message_is_sent_and_the_reply_read_aloud(wx_app) -> None:
    service, said = _Service(), []
    frame = _frame(service, said)
    try:
        _say(frame, "What is a haiku?")
        assert service.sent == [("What is a haiku?", [], [])]
        assert "You: What is a haiku?" in frame._transcript.GetValue()
        assert "AI: Reply to What is a haiku?" in frame._transcript.GetValue()
        assert said[-1] == "Reply to What is a haiku?"
        assert frame._message.GetValue() == ""
        assert "Used 1 request" in frame._status.GetValue()
    finally:
        frame.Destroy()


def test_the_next_message_carries_the_conversation_so_far(wx_app) -> None:
    service, said = _Service(), []
    frame = _frame(service, said)
    try:
        _say(frame, "First.")
        _say(frame, "Second.")
        _prompt, _chunks, history = service.sent[-1]
        assert [turn["content"] for turn in history] == ["First.", "Reply to First."]
    finally:
        frame.Destroy()


def test_forgetting_the_beginning_is_said_once(wx_app) -> None:
    service, said = _Service(dropped=2), []
    frame = _frame(service, said)
    try:
        _say(frame, "One.")
        _say(frame, "Two.")
        told = [line for line in said if "no longer sent" in line]
        assert len(told) == 1
        assert "free limit" in told[0]
    finally:
        frame.Destroy()


def test_an_empty_message_sends_nothing(wx_app) -> None:
    service, said = _Service(), []
    frame = _frame(service, said)
    try:
        _say(frame, "   ")
        assert service.sent == []
        assert said[-1] == "Type a message first."
    finally:
        frame.Destroy()


def test_a_message_too_long_on_its_own_is_refused_before_sending(wx_app) -> None:
    service, said = _Service(max_input=100), []
    frame = _frame(service, said)
    try:
        _say(frame, "word " * 500)
        assert service.sent == []
        assert "Nothing was sent" in frame._status.GetValue()
    finally:
        frame.Destroy()


def test_new_conversation_forgets_everything(wx_app) -> None:
    service, said = _Service(), []
    frame = _frame(service, said)
    try:
        _say(frame, "First.")
        frame._start_over()
        _say(frame, "Fresh.")
        assert service.sent[-1][2] == []
        assert frame._transcript.GetValue().startswith("You: Fresh.")
    finally:
        frame.Destroy()


def test_the_last_reply_can_go_into_the_document(wx_app) -> None:
    service, said, inserted = _Service(), [], []
    frame = _frame(service, said, on_insert=inserted.append)
    try:
        frame._insert_last()
        assert inserted == [] and said[-1] == "There is no reply yet."
        _say(frame, "Write a line.")
        frame._insert_last()
        assert inserted == ["Reply to Write a line."]
    finally:
        frame.Destroy()


def test_an_own_key_says_there_is_no_limit(wx_app) -> None:
    service, said = _Service(own_key=True), []
    frame = _frame(service, said)
    try:
        assert "no limits" in frame._about.GetValue()
    finally:
        frame.Destroy()


def test_a_follow_up_keeps_a_document_questions_excerpts() -> None:
    from quill.ui.hosted_ai_chat import follow_up_seed

    seed = follow_up_seed(("document_qna", "Who signs?", ["EXCERPT"]), "The tenant.")
    assert seed.excerpts == ["EXCERPT"]
    assert [turn.text for turn in seed.turns] == ["Who signs?", "The tenant."]
    summary = follow_up_seed(("summarize", "Long text.", None), "Short.")
    assert summary.turns[0].text == "Summarize this:\n\nLong text."
    assert summary.excerpts == []


def test_a_seeded_conversation_sends_its_excerpts_every_time(wx_app) -> None:
    service, said = _Service(), []
    seed = Conversation(excerpts=["EXCERPT"])
    seed.add("user", "Who signs?")
    seed.add("assistant", "The tenant.")
    frame = _frame(service, said, conversation=seed)
    try:
        _say(frame, "And the date?")
        prompt, chunks, history = service.sent[-1]
        assert chunks == ["EXCERPT"] and len(history) == 2
        assert "excerpts" in frame._about.GetValue().lower()
    finally:
        frame.Destroy()


def test_opening_needs_a_connection_or_an_own_key(wx_app, monkeypatch) -> None:
    from quill.ui import hosted_ai_chat

    opened: list[Any] = []
    host = SimpleNamespace(
        _ai_ready=lambda: True,
        _ai_service=lambda: SimpleNamespace(own_key_active=False, signed_in=False),
        _announce=opened.append,
        cmd_ai_sign_in=lambda: opened.append("sign in"),
    )
    hosted_ai_chat.open_for(host)
    assert opened[-1] == "sign in"


# -- the pad's door ---------------------------------------------------------


class _PadService:
    own_key_active = False
    own_key_model = "gpt-6-luna"
    free_limits = GatewayLimits(max_input_tokens=3000)
    limits = free_limits

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, Any, dict[str, Any]]] = []

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""

    def ask(self, feature, prompt, chunks, *, on_done, on_error, **extra) -> None:  # noqa: ANN001
        self.sent.append((feature, prompt, chunks, extra))


def _pad(service: Any, action: str, **kwargs: Any) -> Any:
    from quill.ui.hosted_ai_pad import AiPadFrame

    return AiPadFrame(
        None,
        service,
        document_text="Bonjour tout le monde.",
        selection="Bonjour tout le monde.",
        position=0,
        announce=lambda _text: None,
        on_result=lambda *_args: None,
        initial_action=action,
        **kwargs,
    )


def test_the_pad_opens_a_conversation_with_the_first_message(wx_app) -> None:
    service, opened = _PadService(), []
    pad = _pad(service, "chat", on_chat=opened.append)
    try:
        assert pad._question.IsShown()
        assert "conversation window" in pad._summary.GetValue()
        pad._question.SetValue("Help me plan a talk.")
        pad._on_send(None)
        assert opened == ["Help me plan a talk."]
        assert service.sent == []
    finally:
        if pad:
            pad.Destroy()


def test_translate_asks_for_a_language_and_sends_it(wx_app) -> None:
    from quill.core.ai.writing_tools import LANGUAGES

    service = _PadService()
    pad = _pad(service, "translate")
    try:
        assert pad._language.IsShown()
        pad._language.SetSelection(LANGUAGES.index("English"))
        pad._on_send(None)
        feature, prompt, _chunks, extra = service.sent[-1]
        assert feature == "translate" and prompt == "Bonjour tout le monde."
        assert extra == {"language": "English"}
        assert pad.last_request == ("translate", "Bonjour tout le monde.", None)
    finally:
        pad.Destroy()


def test_other_actions_hide_the_language_and_send_none(wx_app) -> None:
    service = _PadService()
    pad = _pad(service, "shorten")
    try:
        assert not pad._language.IsShown()
        pad._on_send(None)
        assert service.sent[-1][0] == "shorten" and service.sent[-1][3] == {}
    finally:
        pad.Destroy()


def test_the_result_window_offers_follow_up(wx_app) -> None:
    from quill.ui.hosted_ai_pad import AiResultFrame

    followed: list[str] = []
    frame = AiResultFrame(
        None,
        action="shorten",
        text="Short.",
        used="",
        on_replace=None,
        on_insert=None,
        on_again=None,
        announce=lambda _t: None,
        on_follow_up=lambda: followed.append("yes"),
    )
    try:
        labels = [child.GetLabel() for child in frame.GetChildren()[0].GetChildren()]
        assert "Follow &Up" in labels
        assert frame.GetTitle() == "Shorter"
    finally:
        frame.Destroy()
