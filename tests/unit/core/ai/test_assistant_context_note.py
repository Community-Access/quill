"""The assistant reports, never hides, context trimming (error specificity).

``Assistant.answer``/``answer_stream``/``write_for_document`` trim the document
to a shrinking budget to fit the model's window. A sighted user might notice a
shortened prompt; a blind user cannot -- an answer over 6,000 of 40,000
characters reads exactly like an answer over all of them. After each call,
``last_context_note`` carries a user-facing sentence stating the working size
(or "" when nothing was trimmed) for the UI to speak.
"""

from __future__ import annotations

from quill.core.ai.assistant import Assistant
from quill.core.ai.backend import ContextWindowExceeded


class _Backend:
    """Fake backend: rejects prompts longer than *window* chars."""

    def __init__(self, window: int = 10_000) -> None:
        self.window = window
        self.prompts: list[str] = []

    def is_available(self):  # noqa: ANN201 - protocol shape
        return True, None

    def respond(self, prompt: str) -> str:
        if len(prompt) > self.window:
            raise ContextWindowExceeded("too big")
        self.prompts.append(prompt)
        return "answer"

    def respond_stream(self, prompt: str, on_delta) -> str:  # noqa: ANN001
        result = self.respond(prompt)
        on_delta(result)
        return result


def test_small_document_produces_no_note() -> None:
    assistant = Assistant(backend=_Backend())

    assistant.answer("What is this?", "A short document.")

    assert assistant.last_context_note == ""


def test_trimmed_document_is_reported_with_the_working_size() -> None:
    assistant = Assistant(backend=_Backend())
    document = "x" * 40_000

    assistant.answer("Summarize.", document)

    note = assistant.last_context_note
    assert "6,000" in note  # the first (largest) context budget
    assert "40,000" in note
    assert "first" in note


def test_shrunken_budget_is_reported_accurately() -> None:
    # A small window forces the budget ladder down to 1,200 chars.
    assistant = Assistant(backend=_Backend(window=2_000))
    document = "x" * 40_000

    assistant.answer("Summarize.", document)

    assert "1,200" in assistant.last_context_note
    assert "40,000" in assistant.last_context_note


def test_streaming_reports_the_same_note() -> None:
    assistant = Assistant(backend=_Backend())
    document = "y" * 20_000

    assistant.answer_stream("Summarize.", document, lambda _f: None)

    assert "6,000" in assistant.last_context_note
    assert "20,000" in assistant.last_context_note


def test_overlong_message_is_reported() -> None:
    assistant = Assistant(backend=_Backend(window=100_000))

    assistant.answer("m" * 9_000, "")

    note = assistant.last_context_note
    assert "4,000" in note  # the message clamp
    assert "9,000" in note


def test_note_resets_between_calls() -> None:
    assistant = Assistant(backend=_Backend())

    assistant.answer("Summarize.", "z" * 40_000)
    assert assistant.last_context_note

    assistant.answer("Summarize.", "short")
    assert assistant.last_context_note == ""
