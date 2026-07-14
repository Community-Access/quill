"""Unified chat session core (PRD §2.2, §14) — the innerworkings of every chat UI.

QUILL has several chat surfaces (Ask Quill, Ask AI, Writing Assistant). They
should share one engine: a provider-neutral conversation that holds the turns,
talks to a backend, auto-compacts when the history outgrows the context window,
and emits normalized events for balanced announcements. This is that engine —
wx-free and fully testable with a fake backend; the dialogs become thin views.

A :class:`ChatSession` is constructed with any backend exposing
``respond(prompt) -> str`` (and optionally ``respond_stream``). ``send`` appends
the user turn, compacts the history if needed, calls the model, appends the reply,
and emits ``agent_started`` / ``agent_completed`` (token deltas during streaming
are summarized by the event bridge, never spoken one by one). Sessions serialize
via :meth:`to_dict` / :meth:`from_dict` for persistence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

from quill.core.ai.compaction import SUMMARY_SPEAKER, Message, compact_conversation
from quill.core.ai.events import AgentEvent, AgentEventKind

__all__ = ["ChatTurn", "ChatError", "ChatSession"]

Emit = Callable[[AgentEvent], None]
OnDelta = Callable[[str], None]


class ChatError(RuntimeError):
    """A chat turn could not complete (backend/provider failure)."""


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """One conversation turn. ``role`` is ``system`` / ``user`` / ``assistant``."""

    role: str
    text: str


class ChatSession:
    """A provider-neutral, auto-compacting chat conversation."""

    def __init__(
        self,
        backend: object,
        *,
        token_budget: int = 6000,
        system_prompt: str = "",
        emit: Emit | None = None,
        keep_recent: int = 4,
    ) -> None:
        self._backend = backend
        self._budget = max(1, token_budget)
        self._emit = emit or (lambda _event: None)
        self._keep_recent = keep_recent
        self._turns: list[ChatTurn] = []
        if system_prompt.strip():
            self._turns.append(ChatTurn("system", system_prompt.strip()))

    @property
    def turns(self) -> list[ChatTurn]:
        return list(self._turns)

    def last_reply(self) -> str:
        for turn in reversed(self._turns):
            if turn.role == "assistant":
                return turn.text
        return ""

    # -- sending -----------------------------------------------------------

    def send(self, user_text: str) -> str:
        """Append the user turn, (compact if needed), call the model, return reply."""
        self._turns.append(ChatTurn("user", user_text))
        self._maybe_compact()
        self._emit(AgentEvent(AgentEventKind.AGENT_STARTED, "Thinking."))
        try:
            reply = str(self._backend.respond(self._render_prompt()))  # type: ignore[attr-defined]
        except Exception as exc:  # contained: surface as ChatError + ERROR event
            self._emit(AgentEvent(AgentEventKind.ERROR, "The assistant could not respond."))
            raise ChatError(str(exc)) from exc
        self._turns.append(ChatTurn("assistant", reply))
        self._emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, "Response complete."))
        return reply

    def send_stream(self, user_text: str, on_delta: OnDelta) -> str:
        """Streaming variant; falls back to blocking when the backend can't stream."""
        self._turns.append(ChatTurn("user", user_text))
        self._maybe_compact()
        self._emit(AgentEvent(AgentEventKind.AGENT_STARTED, "Thinking."))

        def delta(fragment: str) -> None:
            on_delta(fragment)
            self._emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, "Writing."))

        try:
            stream = getattr(self._backend, "respond_stream", None)
            if callable(stream):
                reply = str(stream(self._render_prompt(), delta))
            else:
                reply = str(self._backend.respond(self._render_prompt()))  # type: ignore[attr-defined]
                if reply:
                    delta(reply)
        except Exception as exc:
            self._emit(AgentEvent(AgentEventKind.ERROR, "The assistant could not respond."))
            raise ChatError(str(exc)) from exc
        self._turns.append(ChatTurn("assistant", reply))
        self._emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, "Response complete."))
        return reply

    # -- internals ---------------------------------------------------------

    def _render_prompt(self) -> str:
        """Render the conversation into a single prompt for ``respond``."""
        parts: list[str] = []
        for turn in self._turns:
            if turn.role == "system":
                parts.append(turn.text)
            elif turn.role == "user":
                parts.append(f"User: {turn.text}")
            elif turn.role == SUMMARY_SPEAKER.lower() or turn.role == "summary":
                parts.append(f"[Earlier summary] {turn.text}")
            else:
                parts.append(f"Assistant: {turn.text}")
        parts.append("Assistant:")
        return "\n\n".join(parts)

    def _maybe_compact(self) -> None:
        """Summarize the older head of the conversation if over the token budget."""
        system = [t for t in self._turns if t.role == "system"]
        dialog = [t for t in self._turns if t.role != "system"]
        messages = [Message(speaker=t.role, text=t.text) for t in dialog]

        def summarize(prompt: str) -> str:
            return str(self._backend.respond(prompt))  # type: ignore[attr-defined]

        result = compact_conversation(
            messages, token_budget=self._budget, summarize=summarize, keep_recent=self._keep_recent
        )
        if not result.compacted:
            return
        self._emit(AgentEvent(AgentEventKind.AGENT_THINKING_SUMMARY, "Summarized earlier turns."))
        rebuilt = list(system)
        for message in result.messages:
            role = "summary" if message.speaker == SUMMARY_SPEAKER else message.speaker
            rebuilt.append(ChatTurn(role, message.text))
        self._turns = rebuilt

    # -- persistence -------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {"turns": [asdict(t) for t in self._turns]}

    @classmethod
    def from_dict(
        cls, data: dict[str, object], backend: object, *, emit: Emit | None = None
    ) -> ChatSession:
        session = cls(backend, emit=emit)
        session._turns = []
        raw_turns = data.get("turns", [])
        if isinstance(raw_turns, list):
            for item in raw_turns:
                if isinstance(item, dict):
                    session._turns.append(
                        ChatTurn(str(item.get("role", "")), str(item.get("text", "")))
                    )
        return session
