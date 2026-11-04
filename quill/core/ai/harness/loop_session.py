"""A tool session QUILL drives itself, for engines with no agent runtime of their own.

Copilot and Codex bring their own loop and call QUILL's tools from it. A plain
chat model -- Ollama on this computer, or any provider that does function
calling -- has no loop, so this is one: send the conversation and the tool
list, run each tool call the model asks for through the
:class:`~quill.core.ai.family_tools.FamilyToolRegistry` (the broker, the
approvals and the review all apply, exactly as under Copilot), send the
results back, and stop when the model answers without asking for a tool.

The same :class:`~quill.core.ai.harness.ToolSession` contract as the others:
:meth:`run` blocks on a worker; :meth:`send`, :meth:`cancel` and :meth:`end`
are safe from any thread; Stop takes effect before the next request and
between tool calls. A step cap stops a model that never stops asking.

The model is a :data:`Chat` callable, so the loop is tested with a script and
each provider is a few lines of request and parse. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import AgentSpec, AIContext, HarnessResult
from quill.core.ai.tool_gateway import Emit

__all__ = ["Chat", "ChatStep", "LoopToolSession", "MAX_LOOP_STEPS", "tool_definitions"]

#: Model requests in one turn before the loop gives up.
MAX_LOOP_STEPS = 60


@dataclass(frozen=True, slots=True)
class ChatStep:
    """One model reply: its text, and the tools it wants run (``(id, name, args)``)."""

    text: str = ""
    tool_calls: tuple[tuple[str, str, dict[str, Any]], ...] = ()


#: ``(messages, tool_definitions) -> ChatStep``. Raises to end the turn with an error.
Chat = Callable[[list[dict[str, Any]], list[dict[str, Any]]], ChatStep]


def tool_definitions(registry: Any) -> list[dict[str, Any]]:
    """The registry's tools in the function-calling shape most providers take."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.wire_name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in registry.tools()
    ]


@dataclass
class LoopToolSession:
    """One task's conversation with a chat model, over QUILL's tools."""

    agent: AgentSpec
    ctx: AIContext
    registry: Any
    approver: Any
    emit: Emit
    chat: Chat
    name: str = "The AI"
    keep_open: bool = False
    max_steps: int = MAX_LOOP_STEPS
    _id: str = field(default_factory=lambda: uuid.uuid4().hex, init=False)
    _follow_ups: queue.Queue[str | None] = field(default_factory=queue.Queue, init=False)
    _cancelled: threading.Event = field(default_factory=threading.Event, init=False)

    @property
    def session_id(self) -> str:
        return self._id

    def send(self, follow_up: str) -> None:
        if follow_up.strip():
            self._follow_ups.put(follow_up)

    def end(self) -> None:
        self._follow_ups.put(None)

    def cancel(self) -> None:
        self._cancelled.set()
        self._follow_ups.put(None)

    def _cancelled_result(self) -> HarnessResult:
        self.emit(AgentEvent(AgentEventKind.AGENT_CANCELLED, f"{self.name} stopped."))
        return HarnessResult(status="cancelled")

    def run(self) -> HarnessResult:
        self.registry.gate.begin_task(self.approver)
        try:
            return self._run()
        finally:
            self.registry.gate.end_task()

    def _run(self) -> HarnessResult:
        messages: list[dict[str, Any]] = []
        if self.agent.system_prompt.strip():
            messages.append({"role": "system", "content": self.agent.system_prompt.strip()})
        first = f"{self.ctx.prompt}\n\n{self.ctx.context_text}".strip()
        messages.append({"role": "user", "content": first})
        tools = tool_definitions(self.registry)
        answer = ""
        while True:
            outcome = self._turn(messages, tools)
            if isinstance(outcome, HarnessResult):
                return outcome
            answer = outcome
            follow_up = self._next_follow_up()
            if self._cancelled.is_set():
                return self._cancelled_result()
            if follow_up is None:
                break
            messages.append({"role": "user", "content": follow_up})
        self.emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, f"{self.name} finished."))
        return HarnessResult(status="completed", final_text=answer)

    def _next_follow_up(self) -> str | None:
        if not self.keep_open:
            try:
                return self._follow_ups.get_nowait()
            except queue.Empty:
                return None
        return self._follow_ups.get()

    def _turn(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        """Run until the model answers without a tool call; its text, or a result."""
        for _step in range(self.max_steps):
            if self._cancelled.is_set():
                return self._cancelled_result()
            try:
                step = self.chat(messages, tools)
            except Exception as error:  # noqa: BLE001 - the engine's failure, said plainly
                said = str(error) or f"{self.name} could not answer."
                self.emit(AgentEvent(AgentEventKind.ERROR, said))
                return HarnessResult(status="error", error=said)
            if step.text:
                self.emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, step.text))
            messages.append(_assistant_message(step))
            if not step.tool_calls:
                return step.text
            for call_id, name, args in step.tool_calls:
                if self._cancelled.is_set():
                    return self._cancelled_result()
                result = self.registry.call(name, args, call_id)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": result.text,
                })
        said = f"The task stopped after {self.max_steps} requests to {self.name}."
        self.emit(AgentEvent(AgentEventKind.WARNING, said))
        return HarnessResult(status="error", error=said)


def _assistant_message(step: ChatStep) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": step.text}
    if step.tool_calls:
        message["tool_calls"] = [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
            for call_id, name, args in step.tool_calls
        ]
    return message
