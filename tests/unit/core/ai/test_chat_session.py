"""Unified ChatSession: turns, events, streaming, compaction, persistence."""

from __future__ import annotations

from quill.core.ai.chat_session import ChatError, ChatSession, ChatTurn
from quill.core.ai.events import AgentEvent, AgentEventKind


class EchoBackend:
    def __init__(self, reply: str = "ok") -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def respond(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


class StreamingBackend(EchoBackend):
    def respond_stream(self, prompt, on_delta):  # type: ignore[no-untyped-def]
        self.prompts.append(prompt)
        for piece in ["Hel", "lo"]:
            on_delta(piece)
        return "Hello"


class BoomBackend:
    def respond(self, prompt: str) -> str:
        raise RuntimeError("provider down")


def test_send_appends_turns_and_returns_reply() -> None:
    s = ChatSession(EchoBackend("hi there"), system_prompt="You are helpful.")
    reply = s.send("hello")
    assert reply == "hi there"
    roles = [t.role for t in s.turns]
    assert roles == ["system", "user", "assistant"]
    assert s.last_reply() == "hi there"


def test_prompt_includes_system_and_user() -> None:
    backend = EchoBackend()
    s = ChatSession(backend, system_prompt="SYSTEM")
    s.send("my question")
    prompt = backend.prompts[-1]
    assert "SYSTEM" in prompt
    assert "User: my question" in prompt
    assert prompt.rstrip().endswith("Assistant:")


def test_send_emits_started_and_completed() -> None:
    events: list[AgentEvent] = []
    s = ChatSession(EchoBackend(), emit=events.append)
    s.send("hi")
    kinds = [e.kind for e in events]
    assert AgentEventKind.AGENT_STARTED in kinds
    assert AgentEventKind.AGENT_COMPLETED in kinds


def test_backend_failure_raises_chat_error_and_emits_error() -> None:
    events: list[AgentEvent] = []
    s = ChatSession(BoomBackend(), emit=events.append)
    try:
        s.send("hi")
    except ChatError as exc:
        assert "provider down" in str(exc)
    else:
        raise AssertionError("expected ChatError")
    assert AgentEventKind.ERROR in [e.kind for e in events]


def test_streaming_delivers_deltas_and_final() -> None:
    deltas: list[str] = []
    s = ChatSession(StreamingBackend())
    reply = s.send_stream("hi", deltas.append)
    assert reply == "Hello"
    assert deltas == ["Hel", "lo"]
    assert s.last_reply() == "Hello"


def test_streaming_falls_back_when_no_stream() -> None:
    deltas: list[str] = []
    s = ChatSession(EchoBackend("whole"))  # no respond_stream
    reply = s.send_stream("hi", deltas.append)
    assert reply == "whole"
    assert deltas == ["whole"]


def test_compaction_summarizes_when_over_budget() -> None:
    # Tiny budget forces compaction; the echo backend doubles as summarizer.
    backend = EchoBackend("SUMMARY OF EARLIER")
    s = ChatSession(backend, token_budget=5, keep_recent=1)
    for i in range(6):
        s.send(f"message number {i} with several words to exceed the budget")
    # After compaction, an "Earlier summary" turn should appear in the prompt and
    # the conversation should not grow without bound.
    assert any(t.role == "summary" for t in s.turns)


def test_persistence_roundtrip() -> None:
    s = ChatSession(EchoBackend("r"), system_prompt="sys")
    s.send("q1")
    data = s.to_dict()
    restored = ChatSession.from_dict(data, EchoBackend())
    assert [(t.role, t.text) for t in restored.turns] == [(t.role, t.text) for t in s.turns]


def test_chatturn_is_a_dataclass() -> None:
    t = ChatTurn("user", "hi")
    assert t.role == "user" and t.text == "hi"
