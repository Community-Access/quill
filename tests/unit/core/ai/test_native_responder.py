"""responder_from_backend adapts an AIBackend into the harness Responder."""

from __future__ import annotations

from quill.core.ai.backend import AIBackend
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.harness import AgentSpec, AIContext
from quill.core.ai.harness.native import build_prompt, responder_from_backend


class FakeBackend(AIBackend):
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def is_available(self) -> tuple[bool, str | None]:
        return True, None

    def respond(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "BACKEND REPLY"


def _agent() -> AgentSpec:
    return AgentSpec(
        id="writing-companion",
        display_name="Writing Companion",
        system_prompt="Improve the text.",
        default_scope=ContextScope.SELECTION,
    )


def test_build_prompt_composes_system_prompt_and_context() -> None:
    prompt = build_prompt(_agent(), AIContext(prompt="make it warmer", context_text="hello world"))
    assert "Improve the text." in prompt
    assert "make it warmer" in prompt
    assert "hello world" in prompt


def test_responder_from_backend_calls_respond() -> None:
    backend = FakeBackend()
    responder = responder_from_backend(backend)
    result = responder(_agent(), AIContext(prompt="go", context_text="ctx"))
    assert result == "BACKEND REPLY"
    assert len(backend.prompts) == 1
    assert "Improve the text." in backend.prompts[0]
    assert "ctx" in backend.prompts[0]
