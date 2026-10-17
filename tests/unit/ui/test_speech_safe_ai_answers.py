"""Spoken AI answers are speech-safe; inserted and shown text is untouched (2026-10-16).

Every test here has an answer full of Markdown and checks both halves: what the
screen reader is handed has no Markdown symbols in it, and what reaches the
document, the clipboard or the transcript is the answer exactly as it came.
Fakes only -- no wx window, no clipboard, no screen reader.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from quill.core.ai.spoken_answer import speakable_answer, speakable_line

ANSWER = (
    "## Summary\n\n**Three** things:\n\n- one\n- two\n\nSee [the guide](https://example.com/guide)."
)
SYMBOLS = ("#", "**", "](", "https://", "\n- ")


def _clean(spoken: str) -> bool:
    return not any(symbol in spoken for symbol in SYMBOLS)


def test_speakable_line_reads_the_words() -> None:
    spoken = speakable_line(ANSWER)
    assert _clean(spoken)
    assert "Summary" in spoken and "Three things" in spoken and "the guide" in spoken
    assert "\n" not in spoken


def test_speakable_answer_keeps_paragraphs_for_a_voice() -> None:
    spoken = speakable_answer(ANSWER)
    assert _clean(spoken)
    assert "\n" in spoken


def test_a_code_block_is_named_not_read() -> None:
    assert speakable_line("Run this:\n```\nrm -rf build\n```") == "Run this: code block"


# -- the free AI's answers, delivered to the cursor or the clipboard ---------- #


class _AnswersHost:
    """The three HostedAiMixin hooks AiAnswersMixin needs, faked."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.said: list[str] = []
        self.inserted: list[str] = []
        self.copied: list[str] = []
        self.control = MagicMock()
        self.control.GetInsertionPoint.return_value = 0

    def _ai_delivery(self) -> str:
        return self.mode

    def _ai_control(self) -> Any:
        return self.control

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _ai_copy_to_clipboard(self, text: str) -> bool:
        self.copied.append(text)
        return True


def _deliver(mode: str, monkeypatch: pytest.MonkeyPatch) -> _AnswersHost:
    import quill.ui.hosted_ai_answers as module

    host = _AnswersHost(mode)
    monkeypatch.setattr(
        module,
        "replace_as_one_undo",
        lambda _control, _start, _end, text: host.inserted.append(text),
    )
    assert module.AiAnswersMixin._deliver_elsewhere(host, ANSWER) is True  # type: ignore[arg-type]
    return host


def test_an_answer_at_the_cursor_is_inserted_as_is_and_spoken_as_words(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.ai.answer_delivery import CURSOR

    host = _deliver(CURSOR, monkeypatch)

    assert host.inserted == [ANSWER]
    assert len(host.said) == 1
    assert host.said[0].startswith("Answer inserted at the cursor. Press Control Z to undo. ")
    assert _clean(host.said[0])


def test_an_answer_on_the_clipboard_is_copied_as_is_and_spoken_as_words(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.ai.answer_delivery import CLIPBOARD

    host = _deliver(CLIPBOARD, monkeypatch)

    assert host.copied == [ANSWER]
    assert host.said[0].startswith("Answer copied to the clipboard. ")
    assert _clean(host.said[0])


# -- a conversation reply -------------------------------------------------------- #


class _ClosedChat:
    """A conversation window closed while the reply was on its way."""

    def __init__(self) -> None:
        self.said: list[str] = []
        self._busy = True

    def __bool__(self) -> bool:
        return False

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_a_reply_to_a_closed_conversation_is_still_said_once_as_words() -> None:
    from quill.ui.hosted_ai_chat import AiChatFrame

    chat = _ClosedChat()
    AiChatFrame._reply(chat, "hi", ANSWER, None, 0)  # type: ignore[arg-type]

    assert len(chat.said) == 1 and _clean(chat.said[0])


def test_a_reply_goes_into_the_transcript_as_is_and_is_spoken_as_words() -> None:
    from quill.core.ai.hosted_chat import Conversation
    from quill.ui.hosted_ai_chat import AiChatFrame

    chat = MagicMock()
    chat.__bool__ = lambda _self: True
    chat._conversation = Conversation()
    chat._told_set_aside = False
    chat._message.GetValue.return_value = "hi"
    said: list[str] = []
    replies: list[str] = []
    chat._announce = said.append
    chat.on_reply = replies.append

    AiChatFrame._reply(chat, "hi", ANSWER, None, 0)

    assert chat._conversation.turns[-1].text == ANSWER
    chat._save_exchange.assert_called_once_with("hi", ANSWER)
    assert said == replies and len(said) == 1
    assert _clean(said[0])


# -- Ask Quill -------------------------------------------------------------------- #


def test_ask_quill_announcements_are_speech_safe() -> None:
    from quill.ui.assistant_reply_delivery import AssistantReplyDeliveryMixin

    host = MagicMock()
    said: list[str] = []
    host._announce = said.append
    host._announce_limit.return_value = 0

    AssistantReplyDeliveryMixin._announce_incoming(host, ANSWER, prefix="Quill proposal")

    assert said[0].startswith("Quill proposal: ")
    assert _clean(said[0])


@pytest.mark.parametrize("mode", ["announce", "local_tts"])
def test_ask_quill_replies_are_speech_safe_in_every_spoken_mode(mode: str) -> None:
    from quill.core.ai.voice_reply import plan_voice_reply
    from quill.core.settings import Settings

    plan = plan_voice_reply(
        ANSWER, Settings(ai_voice_reply_mode=mode, ai_voice_reply_announce_limit=0)
    )

    spoken = plan.announce_text or plan.spoken_text
    assert spoken and _clean(spoken)
