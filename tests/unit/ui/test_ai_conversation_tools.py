"""Reading back, listing and exporting AI conversations, in both windows
(todo item 44): Ask Quill (QUILL) and the AI Conversation window both editors
open. Fakes only -- no real keystrokes, no real file dialog, no WebView."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.core.ai.gateway_client import GatewayLimits  # noqa: E402
from quill.core.ai.hosted_chat import Conversation  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app


PAIRS = [("You", "Hello"), ("AI", "# Hi\n\nHow can I help?"), ("You", "A table"), ("AI", "Done")]


# -- the recent ten --------------------------------------------------------


def test_the_reader_says_the_conversation_as_it_stands_now() -> None:
    from quill.ui.ai_conversation_tools import RecentMessageReader

    pairs: list[tuple[str, str]] = [("You", "One")]
    said: list[str] = []
    reader = RecentMessageReader(lambda: pairs, said.append)
    reader.read(1)
    pairs.append(("AI", "Two"))
    reader._last = (0, 0.0)
    reader.read(1)
    assert said == ["Newest, Message 1 of 1, You: One", "Newest, Message 2 of 2, AI: Two"]


def test_one_press_seen_twice_is_said_once() -> None:
    from quill.ui.ai_conversation_tools import RecentMessageReader

    said: list[str] = []
    reader = RecentMessageReader(lambda: PAIRS, said.append)
    reader.read(2)
    reader.read(2)
    reader.read(3)
    assert len(said) == 2


def test_alt_digits_are_bound_as_an_accelerator_table(wx_app) -> None:
    from quill.ui.ai_conversation_tools import RecentMessageReader, bind_recent_message_keys

    frame = wx.Frame(None)
    said: list[str] = []
    try:
        ids = bind_recent_message_keys(frame, RecentMessageReader(lambda: PAIRS, said.append))
        assert len(ids) == 10
        event = wx.CommandEvent(wx.wxEVT_MENU, ids[9])  # Alt+0: the tenth newest
        frame.GetEventHandler().ProcessEvent(event)
        assert said == ["There are only 4 messages so far. Alt+4 reads the oldest."]
    finally:
        frame.Destroy()


def test_the_char_hook_reads_alt_and_a_digit_only() -> None:
    from quill.ui.ai_conversation_tools import recent_digit

    def key(code: int, *, alt=True, ctrl=False, shift=False) -> Any:
        return SimpleNamespace(
            AltDown=lambda: alt,
            ControlDown=lambda: ctrl,
            ShiftDown=lambda: shift,
            GetKeyCode=lambda: code,
        )

    assert recent_digit(key(ord("1"))) == 1
    assert recent_digit(key(ord("0"))) == 10
    assert recent_digit(key(wx.WXK_NUMPAD3)) == 3
    assert recent_digit(key(ord("1"), alt=False)) == 0
    assert recent_digit(key(ord("1"), shift=True)) == 0
    assert recent_digit(key(ord("A"))) == 0


@pytest.mark.parametrize(
    "module",
    [
        "quill/ui/hosted_ai_chat.py",
        "quill/ui/assistant_panel.py",
        "quill/ui/assistant_conversation_tools.py",
        "quill/ui/ai_conversation_tools.py",
    ],
)
def test_no_access_key_in_either_window_is_a_digit(module: str) -> None:
    """Collision check: Alt+digit is free in both windows, so the keys can only
    ever mean "read a recent message"."""
    source = (ROOT / module).read_text(encoding="utf-8")
    labels = re.findall(r'label="([^"]*)"', source)
    assert labels
    assert not [label for label in labels if re.search(r"&[0-9]", label)]


# -- Messages... -----------------------------------------------------------


def test_the_list_opens_one_message_and_returns_to_its_row(wx_app) -> None:
    from quill.core.ai.chat_navigation import number_messages
    from quill.ui.ai_conversation_tools import MessageListDialog

    opened: list[str] = []
    dialog = MessageListDialog(
        None,
        number_messages(PAIRS),
        start=1,
        view=lambda _parent, message: opened.append(message.position),
        read=lambda _parent, message: opened.append("text " + message.position),
    )
    try:
        assert dialog.list.GetCount() == 4
        assert dialog.list.GetString(1).startswith("Message 2 of 4, AI: # Hi How can I help?")
        assert dialog.position == 1
        dialog.open_current()
        assert opened == ["Message 2 of 4, AI"]
        assert dialog.position == 1
        dialog.list.SetSelection(3)
        dialog.read_current()
        assert opened[-1] == "text Message 4 of 4, AI" and dialog.position == 3
    finally:
        dialog.Destroy()


def test_the_list_starts_on_the_newest_message_by_default(wx_app) -> None:
    from quill.core.ai.chat_navigation import number_messages
    from quill.ui.ai_conversation_tools import MessageListDialog

    dialog = MessageListDialog(None, number_messages(PAIRS))
    try:
        assert dialog.position == 3
    finally:
        dialog.Destroy()


def test_an_empty_conversation_says_so_instead_of_opening(wx_app) -> None:
    from quill.ui.ai_conversation_tools import show_message_list

    said: list[str] = []
    assert show_message_list(None, [], said.append, start=None) is None
    assert said == ["No messages yet."]


def test_the_list_remembers_its_row_for_next_time(wx_app, monkeypatch) -> None:
    from quill.ui import ai_conversation_tools as tools

    seen: list[int | None] = []

    def fake_modal(dialog, _title) -> int:
        seen.append(dialog.position)
        dialog.list.SetSelection(0)
        return wx.ID_CANCEL

    monkeypatch.setattr(tools, "show_modal_dialog", fake_modal)
    left_on = tools.show_message_list(None, PAIRS, lambda _s: None, start=2)
    assert seen == [2] and left_on == 0


def test_read_as_text_shows_the_message_exactly(wx_app) -> None:
    from quill.core.ai.chat_navigation import number_messages
    from quill.ui.ai_conversation_tools import _MessageTextDialog

    dialog = _MessageTextDialog(None, number_messages(PAIRS)[1])
    try:
        assert dialog.text.GetValue().replace("\r\n", "\n") == "# Hi\n\nHow can I help?"
        assert dialog.GetTitle() == "Message Text"
    finally:
        dialog.Destroy()


# -- Export Conversation... ------------------------------------------------


def test_export_writes_the_chosen_file_and_says_so(wx_app, tmp_path: Path) -> None:
    from quill.ui.ai_conversation_tools import export_conversation_to_file

    said: list[str] = []
    written = export_conversation_to_file(
        None, PAIRS, said.append, choose=lambda _p, _n: tmp_path / "chat.txt"
    )
    assert written == tmp_path / "chat.txt"
    assert "You: Hello" in written.read_text(encoding="utf-8")
    assert said == ["Exported 4 messages to chat.txt."]


def test_cancelling_export_writes_and_says_nothing(wx_app, tmp_path: Path) -> None:
    from quill.ui.ai_conversation_tools import export_conversation_to_file

    said: list[str] = []
    assert export_conversation_to_file(None, PAIRS, said.append, choose=lambda _p, _n: None) is None
    assert said == [] and list(tmp_path.iterdir()) == []


def test_an_export_that_fails_is_said_in_words(wx_app, tmp_path: Path) -> None:
    from quill.ui.ai_conversation_tools import export_conversation_to_file

    said: list[str] = []
    blocked = tmp_path / "chat.txt"
    blocked.mkdir()  # a folder where the file should go: the write cannot land
    assert export_conversation_to_file(None, PAIRS, said.append, choose=lambda *_: blocked) is None
    assert said[-1].startswith("Could not export the conversation.")


def test_nothing_to_export_is_said_before_any_dialog(wx_app) -> None:
    from quill.ui.ai_conversation_tools import export_conversation_to_file

    said: list[str] = []
    asked: list[str] = []
    export_conversation_to_file(None, [], said.append, choose=lambda *_: asked.append("x"))
    assert asked == [] and said == ["There is nothing in this conversation to export yet."]


# -- the AI Conversation window (both editors) -----------------------------


class _Service:
    own_key_active = False

    def __init__(self) -> None:
        self.limits = GatewayLimits(max_input_tokens=3000)

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""

    def converse(self, prompt, chunks, history, *, on_done, on_error) -> None:  # noqa: ANN001
        on_done(f"## Answer\n\nReply to {prompt}", None, 0)


def _chat(said: list[str], **kwargs: Any) -> Any:
    from quill.ui.hosted_ai_chat import AiChatFrame

    return AiChatFrame(None, _Service(), announce=said.append, **kwargs)


def _say(frame: Any, text: str) -> None:
    frame._message.SetValue(text)
    frame._send()


def test_the_window_has_the_buttons_and_says_the_keys(wx_app) -> None:
    said: list[str] = []
    frame = _chat(said)
    try:
        labels = {child.GetLabel() for child in frame.GetChildren()[0].GetChildren()}
        assert {"Messa&ges...", "E&xport Conversation..."} <= labels
        assert "Alt+1 reads the newest message" in frame._about.GetValue()
    finally:
        frame.Destroy()


def test_alt_1_reads_the_newest_reply_without_moving_focus(wx_app) -> None:
    said: list[str] = []
    frame = _chat(said)
    try:
        _say(frame, "First")
        frame.recent.read(1)
        assert said[-1] == "Newest, Message 2 of 2, AI: Answer Reply to First"
        frame.recent.read(2)
        assert said[-1] == "Message 1 of 2, You: First"
        assert frame._message.GetValue() == ""
    finally:
        frame.Destroy()


def test_a_reply_does_not_move_somebody_reading_the_transcript(wx_app, monkeypatch) -> None:
    said: list[str] = []
    frame = _chat(said)
    try:
        _say(frame, "First")
        frame._transcript.SetInsertionPoint(3)
        monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: frame._transcript))
        _say(frame, "Second")
        assert frame._transcript.GetInsertionPoint() == 3
        assert "Reply to Second" in frame._transcript.GetValue()
    finally:
        frame.Destroy()


def test_a_reply_shows_the_end_when_nobody_is_reading(wx_app) -> None:
    said: list[str] = []
    frame = _chat(said)
    try:
        _say(frame, "First")
        end = frame._transcript.GetLastPosition()
        assert frame._transcript.GetInsertionPoint() == end
    finally:
        frame.Destroy()


def test_export_from_the_window_never_touches_the_document(wx_app, monkeypatch, tmp_path) -> None:
    from quill.ui import hosted_ai_chat

    inserted: list[str] = []
    said: list[str] = []
    frame = _chat(said, on_insert=inserted.append)
    exported: list[Any] = []
    monkeypatch.setattr(
        hosted_ai_chat,
        "export_conversation_to_file",
        lambda parent, pairs, announce: exported.append(list(pairs)),
    )
    try:
        _say(frame, "First")
        frame._export()
        assert exported == [[("You", "First"), ("AI", "## Answer\n\nReply to First")]]
        assert inserted == []
    finally:
        frame.Destroy()


def test_new_conversation_forgets_the_list_row(wx_app, monkeypatch) -> None:
    from quill.ui import hosted_ai_chat

    starts: list[Any] = []
    monkeypatch.setattr(
        hosted_ai_chat,
        "show_message_list",
        lambda parent, pairs, announce, *, start: starts.append(start) or 0,
    )
    said: list[str] = []
    frame = _chat(said)
    try:
        _say(frame, "First")
        frame._list_messages()
        frame._list_messages()
        frame._start_over()
        frame._list_messages()
        assert starts == [None, 0, None]
    finally:
        frame.Destroy()


@pytest.mark.parametrize(
    "service",
    [
        SimpleNamespace(direct=False, signed_in=True),  # QUILL's free AI
        SimpleNamespace(direct=True, own_key_active=True, signed_in=False),  # own key
        SimpleNamespace(direct=True, own_key_active=False, signed_in=False),  # ChatGPT plan
    ],
    ids=["free", "own-key", "chatgpt-plan"],
)
def test_every_route_saves_to_the_same_conversation_store(service, tmp_path, monkeypatch) -> None:
    """Saved conversations follow the editor, not the provider route."""
    from quill.ui import hosted_ai_chat

    built: list[dict[str, Any]] = []

    class _Frame:
        def __init__(self, *_args: Any, **kwargs: Any) -> None:
            built.append(kwargs)

    service.refresh_limits = lambda: None
    monkeypatch.setattr(hosted_ai_chat, "AiChatFrame", _Frame)
    monkeypatch.setattr(hosted_ai_chat, "_talk_to_it", lambda *_a: None)
    host = SimpleNamespace(
        _ai_ready=lambda: True,
        _ai_service=lambda: service,
        _ai_parent=lambda: None,
        _ai_host=lambda: SimpleNamespace(data_dir=tmp_path),
        _announce=lambda _t: None,
        _insert_below=lambda _t: None,
        _after_agreement=lambda then: then(),
        _show_ai_window=lambda _f: None,
    )
    hosted_ai_chat.open_for(host, seed=Conversation())
    assert built and built[0]["store"] == tmp_path / "ai-sessions"


# -- Ask Quill --------------------------------------------------------------


class _AskQuill:
    """The mixin on a real window and list, the way Ask Quill's fallback has them."""

    def __init__(self) -> None:
        from quill.ui.assistant_conversation_tools import AssistantConversationToolsMixin

        class _Host(AssistantConversationToolsMixin):
            pass

        self.host = _Host()
        self.host.dialog = wx.Frame(None)
        self.host.messages = wx.ListBox(self.host.dialog)
        self.host._transcript = []
        self.said: list[str] = []
        self.host._announce = self.said.append
        footer = wx.BoxSizer(wx.HORIZONTAL)
        self.host._build_conversation_tools(footer)
        self.host._bind_fallback_list()

    def add(self, speaker: str, text: str) -> None:
        self.host._transcript.append((speaker, text))
        self.host._fallback_show(f"{speaker}: {text}", len(self.host._transcript) - 1)


def test_ask_quill_reads_recent_messages_from_its_key_hook(wx_app) -> None:
    ask = _AskQuill()
    try:
        ask.add("You", "Hi")
        ask.add("Quill", "Hello there.")
        event = SimpleNamespace(
            AltDown=lambda: True,
            ControlDown=lambda: False,
            ShiftDown=lambda: False,
            GetKeyCode=lambda: ord("2"),
        )
        assert ask.host._recent_from_key(event) is True
        assert ask.said[-1] == "Message 1 of 2, You: Hi"
    finally:
        ask.host.dialog.Destroy()


def test_ask_quill_fallback_list_keeps_the_readers_row(wx_app, monkeypatch) -> None:
    ask = _AskQuill()
    try:
        ask.host._fallback_show("Quill: Hi! Ask me.", None)
        ask.add("You", "One")
        assert ask.host.messages.GetSelection() == 1
        ask.host.messages.SetSelection(0)
        monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: ask.host.messages))
        ask.add("Quill", "Two")
        assert ask.host.messages.GetSelection() == 0
        assert ask.host.messages.GetCount() == 3
    finally:
        ask.host.dialog.Destroy()


def test_ask_quill_fallback_enter_opens_that_message(wx_app, monkeypatch) -> None:
    from quill.ui import assistant_conversation_tools as tools

    opened: list[str] = []
    monkeypatch.setattr(tools, "view_message", lambda _p, m: opened.append(m.position))
    ask = _AskQuill()
    try:
        ask.host._fallback_show("Quill: Hi! Ask me.", None)
        ask.add("You", "One")
        ask.add("Quill", "Two")
        ask.host.messages.SetSelection(0)
        ask.host._open_fallback_row()
        assert opened == []  # the greeting is not a message
        ask.host.messages.SetSelection(2)
        ask.host._open_fallback_row()
        assert opened == ["Message 2 of 2, Quill"]
        assert ask.host.messages.GetSelection() == 2
    finally:
        ask.host.dialog.Destroy()


def test_the_webview_bridge_reads_recent_messages() -> None:
    pytest.importorskip("wx_accessible_webview")
    import json

    from quill.ui.accessible_webview import AccessibleWebView

    view = AccessibleWebView.__new__(AccessibleWebView)
    asked: list[int] = []
    view._on_recent = asked.append
    view._on_send = None
    view._on_close = None
    event = SimpleNamespace(GetString=lambda: json.dumps({"type": "recent", "n": 10}))
    view._on_script_message(event)
    view.recent_key("nonsense")
    view.recent_key(11)
    assert asked == [10]


def test_the_webview_nests_reply_headings_under_the_speaker(monkeypatch) -> None:
    pytest.importorskip("wx_accessible_webview")
    from wx_accessible_webview import AccessibleChatView

    from quill.ui.accessible_webview import AccessibleWebView

    sent: list[str] = []
    monkeypatch.setattr(
        AccessibleChatView, "append_message", lambda _s, _sp, body: sent.append(body)
    )
    view = AccessibleWebView.__new__(AccessibleWebView)
    view.append_message("Quill", "# Plan\n\n## Step")
    assert "<h3" in sent[0] and "<h4" in sent[0] and "<h1" not in sent[0]


def test_ask_quill_wires_the_tools_in() -> None:
    source = (ROOT / "quill/ui/assistant_panel.py").read_text(encoding="utf-8")
    for needle in (
        "AssistantConversationToolsMixin",
        "self._build_conversation_tools(footer)",
        "self._recent_from_key(event)",
        "on_recent=lambda n: self._read_recent(n)",
        "self._bind_fallback_list()",
    ):
        assert needle in source
