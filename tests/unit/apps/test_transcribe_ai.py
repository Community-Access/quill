"""QUILL Transcribe's AI, in the real window (codex.md Phase 3, decision 2).

Its own "QUILL Transcribe" sign-in replaced the borrowed QUILL one; the AI
menu, Ask about the dictation, Which AI, the AI line and the one-sentence
notice. The AI is a stand-in on the real service, so nothing leaves the machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: Builds a real QUILL Transcribe window, which registers system-wide keys.
pytestmark = pytest.mark.machine_global


class _Account:
    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-transcribe"
        self.web_search = False
        self.ended_by_openai = False


@pytest.fixture
def transcribe(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.transcribe import QuillTranscribeFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = QuillTranscribeFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    service = frame._ai_service()
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame.sent = []

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append((message, list(excerpts), requires))
        on_done("An answer.", None, 0)

    service.converse = converse
    try:
        yield frame
    finally:
        for window in list(getattr(frame, "_ai_windows", {}).values()):
            if window:
                window.Destroy()
        frame._shut_down()
        set_transition_announcement_policy(None)
        frame.frame.Destroy()


def _menu(frame, name: str):
    bar = frame.frame.GetMenuBar()
    return bar.GetMenu(bar.FindMenu(name))


def test_the_ai_menu_sits_before_quillville_on_the_fallback_keys(transcribe) -> None:
    bar = transcribe.frame.GetMenuBar()
    titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
    assert titles.index("&AI") == titles.index("&Options") + 1
    labels = [
        i.GetItemLabel() for i in _menu(transcribe, "AI").GetMenuItems() if not i.IsSeparator()
    ]
    assert labels == [
        "&Ask...\tCtrl+Shift+8",
        "&Which AI Am I Using\tCtrl+F8",
        "&Choose Your AI...\tCtrl+Shift+F8",
        "Use My Chat&GPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "AI U&sage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tAlt+Shift+F2",
    ]
    assert transcribe.commands.get("tools.hosted_ai_choose") is not None


def test_transcribe_signs_in_as_itself_and_never_reads_quills_sign_in(transcribe) -> None:
    service = transcribe._ai_service()
    assert service._app.ai_agent_name == "QUILL Transcribe"
    assert service.chatgpt.agent_name == "QUILL Transcribe"


def test_the_migration_sees_only_transcribes_own_sign_in(transcribe) -> None:
    transcribe._settings.ai_connection = ""
    service = transcribe._ai_service()
    service._chatgpt = _Account(signed_in=False)  # QUILL's may be signed in; not ours
    assert service.connection == "free"
    service2 = transcribe._ai_service()
    transcribe._settings.ai_connection = ""
    service2._chatgpt = _Account(signed_in=True)
    assert service2.connection == "chatgpt"
    assert transcribe._settings.ai_connection == "chatgpt"


def test_the_own_key_names_are_copied_from_quill_once(transcribe, quill_data_dir) -> None:
    from quill.core.settings import settings_path

    settings_path().write_text(
        json.dumps({"ai_own_key_provider": "gemini", "ai_own_key_model": "gemini-x"}),
        encoding="utf-8",
    )
    transcribe._settings.ai_seeded = False
    transcribe._settings.ai_own_key_model = ""
    settings = transcribe._ai_host().settings
    assert (settings.ai_own_key_provider, settings.ai_own_key_model) == ("gemini", "gemini-x")
    assert settings.ai_seeded is True


def test_ask_sends_the_last_reviewed_transcript(transcribe) -> None:
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    transcribe._ai_service()._chatgpt = _Account(signed_in=True)
    transcribe._settings.ai_connection = "chatgpt"
    transcribe._last_transcript = ("Board meeting", "Ann: We agreed.\nBo: Yes, Friday.")
    transcribe.cmd_ai_chat_key()
    frame = transcribe._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about your dictation.")
    frame._message.SetValue("What was decided?")
    frame._send()
    facts = transcribe.sent[0][1][0]
    assert "Transcript title: Board meeting" in facts
    assert "We agreed." in facts and "Speakers: Ann, Bo" in facts


def test_ask_falls_back_to_this_sessions_phrases(transcribe) -> None:
    from types import SimpleNamespace

    real = getattr(transcribe, "_dictation", None)
    transcribe._dictation = SimpleNamespace(recent=["newest phrase", "older phrase"], active=False)
    try:
        facts = transcribe._transcribe_ask_facts("", "")
    finally:
        transcribe._dictation = real
    named = {fact.name: fact.value for fact in facts.facts}
    assert named["Transcript title"] == "This session's dictation"
    assert named["Transcript"] == "older phrase\nnewest phrase"


def test_safe_mode_refuses_every_ai_command(transcribe) -> None:
    transcribe._safe_mode = True
    for command in (
        transcribe.cmd_ai_chat_key,
        transcribe.cmd_ai_which,
        transcribe.cmd_ai_choose,
        transcribe.cmd_ai_usage,
        transcribe.cmd_ai_chatgpt,
    ):
        transcribe.said.clear()
        command()
        assert transcribe.said == ["AI is off in Safe Mode."], command.__name__
    assert transcribe.sent == []


def test_the_ai_line_says_which_ai_and_enter_opens_choose(transcribe, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(transcribe), "cmd_ai_choose", lambda self: opened.append("x"))
    assert transcribe._ai_text.GetValue().startswith("AI")
    assert "Choose Your AI" in transcribe._ai_text.GetHelpText()
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_RETURN)
    transcribe._on_ai_line_key(event)
    assert opened == ["x"]


def test_review_says_once_that_transcribe_signs_in_on_its_own(transcribe) -> None:
    from quill.ui.windows_dictation_review import NO_DIRECT_ROUTE

    transcribe._settings.ai_connection = "free"
    transcribe._settings.ai_sign_in_noticed = False
    assert transcribe._review_ai_on() is False  # Dictation Settings: no sentence spent
    assert transcribe._settings.ai_sign_in_noticed is False
    first = transcribe._review_ai().reason()
    assert first.startswith("QUILL Transcribe now signs in to your AI on its own")
    assert "press Ctrl+Shift+F8" in first and first.endswith(NO_DIRECT_ROUTE)
    spoken = [line for line in transcribe.said if line.startswith("QUILL Transcribe now signs")]
    assert len(spoken) == 1  # said, not only written into the Status line
    assert transcribe._review_ai().reason() == NO_DIRECT_ROUTE
    assert len([line for line in transcribe.said if line.startswith("QUILL Transcribe now")]) == 1


def test_the_adapter_has_no_command_of_its_own() -> None:
    from quill.apps.transcribe_ai import TranscribeAiHost, TranscribeAiMixin

    assert [name for name in vars(TranscribeAiMixin) if name.startswith("cmd_")] == []
    assert [name for name in vars(TranscribeAiHost) if name.startswith("cmd_")] == []
