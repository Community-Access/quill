"""A conversation with AI help: what has been said, and how much of it to send.

The seventh AI help feature, ``chat``, shared by QUILL and QUILL Lite. Every
other feature is one request and one answer; a conversation remembers, and the
way it remembers is by sending the conversation so far with every new message.
That is what made conversations expensive, and this module is where they stop
being: :meth:`Conversation.history_for` sends only the newest turns that fit the
same input ceiling every other request has, so a turn never costs more than any
other request. The oldest turns are what is left out, never the new message.

Two ceilings, one rule:

* **QUILL's free AI** -- the service's ``max_input_tokens`` (3,000 today). A few
  recent exchanges fit; the service trims again, authoritatively
  (``quill-ai-gateway/app/limits.py::fit_history``), and says how many it
  dropped.
* **The user's own OpenAI key** -- no QUILL limit at all. The whole conversation
  goes, and is only shortened when it outgrows what the model can read at once
  (:data:`quill.core.ai.own_key.CONTEXT_WARNING_TOKENS`).

Either way, :attr:`Conversation.set_aside` counts the turns no longer sent, so
the window can *say* when a conversation starts forgetting its opening instead
of letting somebody discover it from a puzzling answer.

:func:`chat_message` builds the text the model reads. It is the gateway's
``app/prompts.py::chat_message`` word for word -- an own-key conversation is
built here, on the user's computer -- and ``tests/unit/core/ai/test_own_key.py``
fails if the two drift.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from quill.core.ai.gateway_context import estimate_tokens

__all__ = [
    "CHAT_FEATURE",
    "HISTORY_SPEAKERS",
    "TRANSCRIPT_SPEAKERS",
    "Conversation",
    "Turn",
    "chat_message",
]

#: The gateway's id for a conversation.
CHAT_FEATURE = "chat"

#: Who said a turn, as the model reads it. Must match the gateway's.
HISTORY_SPEAKERS: dict[str, str] = {"user": "User", "assistant": "Assistant"}

#: Who said a turn, as a person reads the transcript.
TRANSCRIPT_SPEAKERS: dict[str, str] = {"user": "You", "assistant": "AI"}


@dataclass(frozen=True, slots=True)
class Turn:
    """One message in a conversation."""

    role: str  # "user" or "assistant"
    text: str

    def wire(self) -> dict[str, str]:
        """The shape the gateway accepts in ``history``."""
        return {"role": self.role, "content": self.text}


def chat_message(
    prompt: str, chunks: Sequence[str] | None, history: Sequence[dict[str, str]] | None
) -> str:
    """The user half of a conversation turn: excerpts, the conversation so far,
    then the latest message. The gateway's ``chat_message``, word for word."""
    parts: list[str] = []
    if chunks:
        parts.append("Excerpts from the user's document:\n" + "\n\n---\n\n".join(chunks))
    if history:
        lines = [f"{HISTORY_SPEAKERS[turn['role']]}: {turn['content']}" for turn in history]
        parts.append("The conversation so far:\n" + "\n\n".join(lines))
    parts.append(f"The user's latest message:\n{prompt}")
    return "\n\n".join(parts)


@dataclass
class Conversation:
    """What has been said, plus any document excerpts it is about."""

    #: Excerpts from the document the conversation started from (a follow-up
    #: to a question about the document). Sent with every turn, never trimmed.
    excerpts: list[str] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    #: How many of the oldest turns were left out of the last request.
    set_aside: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.turns

    def add(self, role: str, text: str) -> None:
        if role not in HISTORY_SPEAKERS:
            raise ValueError(f"unknown speaker {role!r}")
        self.turns.append(Turn(role, text.strip()))

    def history_for(self, message: str, max_input_tokens: int) -> list[dict[str, str]]:
        """The newest turns that fit beside *message* and the excerpts.

        Records how many were left out in :attr:`set_aside`. Never trims the
        message or the excerpts: if those alone are too large, that is the
        ordinary size refusal, said before anything is sent.
        """
        kept = [turn.wire() for turn in self.turns]
        while (
            kept and estimate_tokens(chat_message(message, self.excerpts, kept)) > max_input_tokens
        ):
            kept.pop(0)
        self.set_aside = len(self.turns) - len(kept)
        return kept

    def fits(self, message: str, max_input_tokens: int) -> bool:
        """Whether *message* and the excerpts fit on their own."""
        return estimate_tokens(chat_message(message, self.excerpts, None)) <= max_input_tokens

    def last_answer(self) -> str:
        """The most recent reply, or "" before there is one."""
        return next((turn.text for turn in reversed(self.turns) if turn.role == "assistant"), "")

    def transcript(self) -> str:
        """The conversation as a person reads it: one paragraph per turn."""
        return "\n\n".join(f"{TRANSCRIPT_SPEAKERS[turn.role]}: {turn.text}" for turn in self.turns)
