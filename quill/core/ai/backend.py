"""Abstract AI backend so the assistant is engine-agnostic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from quill.core.error_codes import CodedError


class ContextWindowExceeded(CodedError):
    """Raised when a prompt + response would exceed the model's context window."""

    code = "QUILL-AI-BACKEND-CONTEXT-EXCEEDED"


class AIBackend(ABC):
    name: str = "ai"

    @abstractmethod
    def is_available(self) -> tuple[bool, str | None]:
        """Return (available, reason). reason is a message when unavailable."""

    @abstractmethod
    def respond(self, prompt: str) -> str:
        """Return the model's text response for a single prompt (blocking)."""

    def respond_stream(self, prompt: str, on_delta: Callable[[str], None]) -> str:
        """Stream the response, calling ``on_delta`` per fragment; return the full text.

        The default is a clean non-streaming fallback (AI-14): backends that
        cannot stream produce the whole answer and emit it as a single fragment,
        so callers can always use the streaming API and degrade gracefully.
        Streaming backends override this to deliver real incremental tokens.
        """
        text = self.respond(prompt)
        if text:
            on_delta(text)
        return text
