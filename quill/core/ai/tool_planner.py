"""Provider-neutral prompt-based tool-calling planner (PRD §8.1).

The native :func:`~quill.core.ai.tool_loop.run_tool_loop` needs a
:class:`~quill.core.ai.tool_loop.ToolPlanner` that decides the next step. Cloud
providers expose function-calling, but QUILL's backends only need to produce text
(`respond(prompt) -> str`). This planner is the lowest common denominator: it asks
any text model, in a strict JSON protocol, for the next tool call or the final
answer — so the *same* agentic loop drives OpenAI, Claude, Ollama, or a local
model, and stays fully testable with a scripted responder.

The model is told the available tools and the running transcript, and must reply
with exactly one JSON object: ``{"action": "tool", "tool": ..., "args": {...}}`` or
``{"action": "final", "final_text": ...}``. Parsing is forgiving — malformed output
degrades to a final answer carrying the raw text, never a crash. Every tool the
model picks still goes through the gateway + broker, so the protocol can only
*request* actions; QUILL decides whether they happen.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from quill.core.ai.agent_tools import TOOL_DESCRIPTORS
from quill.core.ai.harness import AgentSpec, AIContext
from quill.core.ai.tool_loop import ToolResult, ToolStep

__all__ = ["ModelResponder", "PromptToolPlanner", "model_responder_from_backend"]

# A raw prompt -> raw text completion. Wraps any backend's blocking respond().
ModelResponder = Callable[[str], str]


def _tool_help_lines() -> str:
    """Render the shared tool descriptors for the model prompt (single source)."""
    lines: list[str] = []
    for tool in TOOL_DESCRIPTORS:
        args = (
            "; args " + ", ".join(f"{k} ({v})" for k, v in tool.parameters.items())
            if tool.parameters
            else "; no args"
        )
        lines.append(f"- {tool.name}: {tool.description}{args}")
    return "\n".join(lines)


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class PromptToolPlanner:
    """Drive the native tool loop by prompting a text model for JSON steps."""

    def __init__(self, responder: ModelResponder, *, max_context_chars: int = 6000) -> None:
        self._responder = responder
        self._max_context_chars = max_context_chars

    def next_step(
        self, agent: AgentSpec, ctx: AIContext, transcript: tuple[ToolResult, ...]
    ) -> ToolStep:
        raw = self._responder(self._build_prompt(agent, ctx, transcript))
        return self._parse(raw)

    # -- prompt + parsing --------------------------------------------------

    def _build_prompt(
        self, agent: AgentSpec, ctx: AIContext, transcript: tuple[ToolResult, ...]
    ) -> str:
        tools = _tool_help_lines()
        context = ctx.context_text[: self._max_context_chars]
        history = (
            "\n".join(
                f"- {r.tool}: {'ok' if r.ok else 'denied/failed'}: {r.output[:400]}"
                for r in transcript
            )
            or "(no steps yet)"
        )
        return (
            f"{agent.system_prompt}\n\n"
            f"Task: {ctx.prompt}\n\n"
            f"You are working on the user's document. Available tools:\n{tools}\n\n"
            f"Document context:\n{context}\n\n"
            f"Steps so far:\n{history}\n\n"
            "Decide the single next step. Make at most one edit: if an edit step "
            "above already succeeded, do NOT edit again — reply with the final answer "
            "describing what you changed. Reply with ONE JSON object and nothing "
            'else. To use a tool: {"action": "tool", "tool": "<name>", "args": {...}}. '
            'When the task is complete: {"action": "final", "final_text": "<answer>"}.'
        )

    def _parse(self, raw: str) -> ToolStep:
        match = _JSON_OBJECT.search(raw or "")
        if match is None:
            # No JSON: treat the whole reply as the final answer.
            return ToolStep("final", final_text=(raw or "").strip())
        try:
            data = json.loads(match.group(0))
        except (ValueError, TypeError):
            return ToolStep("final", final_text=(raw or "").strip())
        if not isinstance(data, dict):
            return ToolStep("final", final_text=(raw or "").strip())

        # Resolve the tool name, tolerating common model deviations from the
        # protocol: the strict {"action":"tool","tool":X,"args":{...}}, a bare
        # {"tool":X,...}, or {"action":X,...} where X is itself a tool name (some
        # mid-size models emit the tool name as the action and put the arguments at
        # the top level instead of under "args").
        from quill.core.ai.agent_tools import tool_names

        known = set(tool_names())
        action = str(data.get("action", "")).strip()
        tool_field = str(data.get("tool", "")).strip()
        chosen = ""
        if action.lower() == "tool" and tool_field:
            chosen = tool_field
        elif action in known:
            chosen = action
        elif tool_field in known:
            chosen = tool_field

        if chosen:
            raw_args = data.get("args", {})
            if isinstance(raw_args, dict) and raw_args:
                args = {str(k): str(v) for k, v in raw_args.items()}
            else:
                # Top-level keys as arguments (minus the protocol keys).
                args = {
                    str(k): str(v)
                    for k, v in data.items()
                    if k not in {"action", "tool", "args", "final_text"}
                }
            return ToolStep("tool", tool=chosen, args=args)
        # action == "final" or anything unrecognized -> final.
        return ToolStep("final", final_text=str(data.get("final_text", (raw or "").strip())))


def model_responder_from_backend(backend: object) -> ModelResponder:
    """Adapt any object with ``respond(prompt) -> str`` into a :data:`ModelResponder`."""

    def respond(prompt: str) -> str:
        return str(backend.respond(prompt))  # type: ignore[attr-defined]

    return respond
