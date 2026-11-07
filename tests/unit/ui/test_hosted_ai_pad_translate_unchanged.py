"""The AI pad says so when Translate hands the text back unchanged (both editors).

Same text back is not a translation, and opening it in the AI Result window as
if it were hides that nothing happened. The pad is shared, so this is QUILL's
and QUILL Lite's behaviour at once.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.core.ai.gateway_client import GatewayLimits  # noqa: E402
from quill.core.ai.translation import HOSTED_UNCHANGED_TRANSLATION_MESSAGE  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    yield shared_wx_app()


class _Service:
    own_key_active = False
    direct = False

    def __init__(self) -> None:
        self.limits = self.free_limits = GatewayLimits(max_input_tokens=3000)
        self.pending: list[Any] = []

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""

    def ask(self, feature, prompt, chunks, *, on_done, on_error, **_kw) -> Any:  # noqa: ANN001
        self.pending.append(on_done)
        return object()


def _pad(service: _Service, said: list[str], results: list[Any]) -> Any:
    from quill.ui.hosted_ai_pad import AiPadFrame

    return AiPadFrame(
        None,
        service,
        document_text="Bonjour tout le monde.",
        selection="Bonjour tout le monde.",
        position=0,
        announce=said.append,
        on_result=lambda *args: results.append(args),
        initial_action="translate",
    )


def test_an_unchanged_translation_is_said_and_not_shown(wx_app) -> None:
    service, said, results = _Service(), [], []
    pad = _pad(service, said, results)
    try:
        pad._on_send(None)
        sent = pad.last_request[1]
        service.pending[-1]("  " + sent.upper() + "\n", None)
        assert results == []
        assert said[-1] == HOSTED_UNCHANGED_TRANSLATION_MESSAGE
    finally:
        pad.Destroy()


def test_a_real_translation_still_reaches_the_result_window(wx_app) -> None:
    service, said, results = _Service(), [], []
    pad = _pad(service, said, results)
    try:
        pad._on_send(None)
        service.pending[-1]("Hello everybody.", None)
        assert results and results[-1][1] == "Hello everybody."
    finally:
        pad.Destroy()
