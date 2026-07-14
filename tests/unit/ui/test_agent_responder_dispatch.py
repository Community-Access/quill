"""run_agent honors the selected AI engine via _select_responder (slice 3).

The agentic gateway path is experimental/opt-in, but the engine-selection logic
is wx-free and unit-testable: it swaps the produce-text transport based on the
user's chosen engine while preserving the run path's threading.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.ui.agent_editor_host import _select_responder


class _Backend:
    def __init__(self, available: bool, reason: str | None = None) -> None:
        self._available = available
        self._reason = reason

    def is_available(self) -> tuple[bool, str | None]:
        return self._available, self._reason

    def respond(self, prompt: str) -> str:  # pragma: no cover - not called here
        return "native text"


class _Controller:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def _set_status(self, message: str) -> None:
        self.messages.append(message)


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))


def test_auto_uses_native_when_backend_available() -> None:
    responder, name = _select_responder(_Backend(True), _Controller())
    assert callable(responder)
    assert name == "Native (QUILL)"


def test_native_required_but_backend_unavailable_reports_reason() -> None:
    responder, info = _select_responder(_Backend(False, "No provider configured"), _Controller())
    assert responder is None
    assert info == "No provider configured"


def test_unavailable_pack_falls_back_to_native_with_notice() -> None:
    from quill.core.ai.quick_switch import save_preferred_harness_id

    save_preferred_harness_id("copilot")  # not installed in CI
    controller = _Controller()
    responder, name = _select_responder(_Backend(True), controller)
    assert callable(responder) and name == "Native (QUILL)"
    assert any("not set up" in m for m in controller.messages)


def test_available_pack_supplies_its_own_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai.quick_switch import save_preferred_harness_id

    save_preferred_harness_id("openai_agents")

    class _FakePack:
        id = "openai_agents"
        display_name = "OpenAI Agents SDK"

        def is_available(self) -> tuple[bool, str | None]:
            return True, None

        def responder(self):  # type: ignore[no-untyped-def]
            return lambda agent, ctx: "sdk text"

    monkeypatch.setattr("quill.ai_packs.all_packs", lambda: [_FakePack()])
    responder, name = _select_responder(_Backend(True), _Controller())
    assert name == "OpenAI Agents SDK"
    assert responder(object(), object()) == "sdk text"


def test_pack_responder_failure_falls_back_to_native(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai.quick_switch import save_preferred_harness_id

    save_preferred_harness_id("openai_agents")

    class _BoomPack:
        id = "openai_agents"
        display_name = "OpenAI Agents SDK"

        def is_available(self) -> tuple[bool, str | None]:
            return True, None

        def responder(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("sdk import broke")

    monkeypatch.setattr("quill.ai_packs.all_packs", lambda: [_BoomPack()])
    controller = _Controller()
    responder, name = _select_responder(_Backend(True), controller)
    assert name == "Native (QUILL)"
    assert any("could not start" in m for m in controller.messages)
