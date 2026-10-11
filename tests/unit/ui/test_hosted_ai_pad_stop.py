"""The AI pad's Send button is Stop while a request is on its way (qc.md X-07).

Stop calls the service's ``cancel``, puts the button back to Send, and says so:
the status line is not where focus is, so the reader would not read it.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.ai.gateway_client import GatewayLimits  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


class _Service:
    own_key_active = False
    direct = False

    def __init__(self) -> None:
        self.limits = self.free_limits = GatewayLimits(max_input_tokens=3000)
        self.pending: list[Any] = []
        self.cancelled = 0

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""

    def ask(self, feature, prompt, chunks, *, on_done, on_error, **_kw) -> None:  # noqa: ANN001
        self.pending.append((on_done, on_error))
        return self.pending[-1]

    def cancel(self, request) -> bool:  # noqa: ANN001
        self.cancelled += 1
        return request in self.pending


def _pad(service: _Service, said: list[str]) -> Any:
    from quill.ui.hosted_ai_pad import AiPadFrame

    return AiPadFrame(
        None,
        service,
        document_text="Apples are red. Pears are green.",
        selection="Apples are red.",
        position=0,
        announce=said.append,
        on_result=lambda *_args: None,
        initial_action="summarize",
    )


def test_send_becomes_stop_and_stop_cancels(wx_app) -> None:
    service, said = _Service(), []
    pad = _pad(service, said)
    try:
        pad._on_send(None)
        assert len(service.pending) == 1
        assert pad._send.GetLabel() == "&Stop"
        assert said[-1] == "Working. Alt+S stops it."
        pad._on_send(None)  # the same button, now Stop
        assert service.cancelled == 1
        assert pad._send.GetLabel() == "&Send"
        assert said[-1] == "Stopped. The answer will not be shown."
        assert pad._status.GetValue() == said[-1]
    finally:
        pad.Destroy()


def test_an_answer_puts_the_button_back_to_send(wx_app) -> None:
    service, said = _Service(), []
    pad = _pad(service, said)
    try:
        pad._on_send(None)
        on_done, _on_error = service.pending[0]
        on_done("Short.", None)
        assert pad._send.GetLabel() == "&Send"
        assert service.cancelled == 0
    finally:
        pad.Destroy()


def test_a_failure_puts_the_button_back_to_send(wx_app) -> None:
    service, said = _Service(), []
    pad = _pad(service, said)
    try:
        pad._on_send(None)
        _on_done, on_error = service.pending[0]
        on_error("Google Gemini did not accept the saved key.")
        assert pad._send.GetLabel() == "&Send"
    finally:
        pad.Destroy()
