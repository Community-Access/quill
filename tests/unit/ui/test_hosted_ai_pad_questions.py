"""The AI pad: general questions, and what an own key lifts.

A general question sends the question and nothing from the document. With the
user's own key nothing is refused on size and a question about the document
sends the whole document -- the summary says what that costs instead.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.ai.gateway_client import GatewayLimits  # noqa: E402
from quill.core.ai.own_key import OWN_KEY_LIMITS  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


class _Service:
    def __init__(self, *, own_key: bool) -> None:
        self.own_key_active = own_key
        self.own_key_model = "gpt-6-luna"
        self.free_limits = GatewayLimits(max_input_tokens=3000)
        self.limits = OWN_KEY_LIMITS if own_key else self.free_limits
        self.sent: list[tuple[str, str, list[str] | None]] = []

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""

    def ask(self, feature, prompt, chunks, *, on_done, on_error) -> None:  # noqa: ANN001
        self.sent.append((feature, prompt, chunks))


_DOCUMENT = "# Fruit\n\nApples are red. Pears are green.\n\n# Stones\n\nGranite is hard."


def _pad(service: _Service, action: str, document: str = _DOCUMENT) -> Any:
    from quill.ui.hosted_ai_pad import AiPadFrame

    return AiPadFrame(
        None,
        service,
        document_text=document,
        selection="",
        position=0,
        announce=lambda _text: None,
        on_result=lambda *_args: None,
        initial_action=action,
    )


def _send(pad: Any, question: str) -> None:
    pad._question.SetValue(question)
    pad._on_send(None)


def test_a_general_question_sends_only_the_question(wx_app) -> None:
    service = _Service(own_key=False)
    pad = _pad(service, "ask")
    try:
        assert "Nothing from this document is sent" in pad._summary.GetValue()
        assert pad._question.IsShown()
        _send(pad, "What is a semicolon for?")
        assert service.sent == [("ask", "What is a semicolon for?", None)]
    finally:
        pad.Destroy()


def test_a_general_question_needs_a_question(wx_app) -> None:
    service = _Service(own_key=False)
    pad = _pad(service, "ask")
    try:
        _send(pad, "   ")
        assert service.sent == []
        assert pad._status.GetValue() == "Type a question first."
    finally:
        pad.Destroy()


def test_the_free_service_still_sends_excerpts_for_a_document_question(wx_app) -> None:
    service = _Service(own_key=False)
    pad = _pad(service, "document_qna")
    try:
        _send(pad, "What colour are pears?")
        ((feature, prompt, chunks),) = service.sent
        assert feature == "document_qna"
        assert prompt == "What colour are pears?"
        assert chunks and all(chunk != _DOCUMENT for chunk in chunks)
    finally:
        pad.Destroy()


def test_an_own_key_sends_the_whole_document_and_says_what_it_costs(wx_app) -> None:
    service = _Service(own_key=True)
    pad = _pad(service, "document_qna")
    try:
        summary = pad._summary.GetValue()
        assert "the whole document" in summary
        assert "no limits" in summary
        assert "gpt-6-luna" in summary
        _send(pad, "What colour are pears?")
        assert service.sent == [("document_qna", "What colour are pears?", [_DOCUMENT])]
    finally:
        pad.Destroy()


def test_an_own_key_is_warned_but_never_refused_on_size(wx_app) -> None:
    big = "word " * 20_000
    service = _Service(own_key=True)
    pad = _pad(service, "summarize", document=big)
    try:
        summary = pad._summary.GetValue()
        assert "more than QUILL's free AI would accept" in summary
        pad._on_send(None)
        assert len(service.sent) == 1
    finally:
        pad.Destroy()


def test_the_free_service_refuses_the_same_size(wx_app) -> None:
    big = "word " * 20_000
    service = _Service(own_key=False)
    pad = _pad(service, "summarize", document=big)
    try:
        pad._on_send(None)
        assert service.sent == []
    finally:
        pad.Destroy()
