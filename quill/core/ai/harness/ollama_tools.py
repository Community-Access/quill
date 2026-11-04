"""Ollama practice mode: a project or document task on a model on this computer (code.md 3.5).

**Practice, on this computer. Nothing is sent. Slower and less capable.** That
is the whole label, and it is meant: small local models are weak at
multi-file coding and call tools wrongly more often, but nothing leaves the
machine and nobody needs an account, which is what a classroom or a learner
who will not sign in needs. Never the default; reached by choosing Ollama on
this computer in My own key.

The engine is :class:`~quill.core.ai.harness.loop_session.LoopToolSession`
over Ollama's ``/api/chat`` with ``tools`` (docs.ollama.com/api), so every
tool call goes through QUILL's registry exactly as under Copilot. Whether a
model supports tools is per model (``/api/show`` capabilities, already read by
:mod:`quill.core.ai.ollama_capabilities`); a model that does not answers in
text and the task ends with that text.

wx-free, strict-typed; the HTTP call is injectable for tests.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities
from quill.core.ai.harness.loop_session import ChatStep, LoopToolSession

__all__ = ["DEFAULT_OLLAMA_URL", "PRACTICE_LABEL", "OllamaToolHarness", "parse_ollama_reply"]

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
PRACTICE_LABEL = "Practice, on this computer. Nothing is sent. Slower and less capable."

#: ``(url, payload) -> reply``: one POST, JSON in and out.
Post = Callable[[str, dict[str, Any]], dict[str, Any]]


def _post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST to Ollama on this computer only; long timeout, because local models are slow."""
    if not url.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]")):
        raise ValueError("Practice mode talks only to Ollama on this computer.")
    from quill.core.net import context_for

    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    # Loopback is plain HTTP, so the context is None; it goes through net all the same.
    with urllib.request.urlopen(  # noqa: S310 - loopback only
        request, timeout=600, context=context_for(url)
    ) as reply:
        data = json.loads(reply.read())
    return data if isinstance(data, dict) else {}


def parse_ollama_reply(data: dict[str, Any]) -> ChatStep:
    """Ollama's ``message`` -- its content and any ``tool_calls`` -- as a :class:`ChatStep`."""
    message = data.get("message") if isinstance(data.get("message"), dict) else {}
    assert isinstance(message, dict)
    calls: list[tuple[str, str, dict[str, Any]]] = []
    for index, call in enumerate(message.get("tool_calls") or []):
        function = call.get("function", {}) if isinstance(call, dict) else {}
        args = function.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        calls.append((str(call.get("id") or f"call-{index}"), str(function.get("name", "")), args))
    return ChatStep(text=str(message.get("content") or ""), tool_calls=tuple(calls))


def _ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ollama wants tool-call arguments as objects, and tool results by ``tool_name``."""
    out: list[dict[str, Any]] = []
    for message in messages:
        message = dict(message)
        if message.get("tool_calls"):
            message["tool_calls"] = [
                {
                    "function": {
                        "name": call["function"]["name"],
                        "arguments": json.loads(call["function"]["arguments"] or "{}"),
                    }
                }
                for call in message["tool_calls"]
            ]
        if message.get("role") == "tool":
            message = {
                "role": "tool",
                "tool_name": message.get("name", ""),
                "content": message["content"],
            }
        out.append(message)
    return out


class OllamaToolHarness:
    """The practice engine: a local Ollama model, QUILL's tools, nothing sent."""

    def __init__(
        self, model: str, base_url: str = DEFAULT_OLLAMA_URL, post: Post | None = None
    ) -> None:
        self._model = model
        self._url = base_url.rstrip("/")
        self._post = post or _post

    @property
    def id(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return f"Ollama on this computer ({self._model})"

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(streaming=False, local_only=True, app_tools=True)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ChatStep:
        payload = {
            "model": self._model,
            "messages": _ollama_messages(messages),
            "tools": tools,
            "stream": False,
        }
        return parse_ollama_reply(self._post(f"{self._url}/api/chat", payload))

    def start_tool_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        tools: Any,
        approver: Any,
        emit: Any,
        *,
        keep_open: bool = False,
        on_usage: Any = None,
    ) -> LoopToolSession:
        tools.set_emit(emit)
        return LoopToolSession(
            agent=agent,
            ctx=ctx,
            registry=tools,
            approver=approver,
            emit=emit,
            chat=self.chat,
            name="Ollama",
            keep_open=keep_open,
        )
