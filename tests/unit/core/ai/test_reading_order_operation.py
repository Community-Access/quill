"""Tests for the assistant's ``reading_order`` transform operation (PRD §5.6)."""

from __future__ import annotations

from quill.core.ai.assistant import Assistant


class _RecordingBackend:
    """Minimal AIBackend that records prompts and echoes a canned response."""

    name = "recording"

    def __init__(self, response: str = "REFLOWED") -> None:
        self.prompts: list[str] = []
        self._response = response

    def is_available(self) -> tuple[bool, str | None]:
        return True, None

    def respond(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._response


def test_reading_order_is_a_known_operation() -> None:
    backend = _RecordingBackend()
    assert "reading_order" in Assistant(backend=backend).available_operations()


def test_reading_order_sends_the_text_with_reorder_instructions() -> None:
    backend = _RecordingBackend(response="clean markdown")
    result = Assistant(backend=backend).transform("reading_order", "col A col B jumbled")

    assert result == "clean markdown"
    assert len(backend.prompts) == 1
    prompt = backend.prompts[0].lower()
    assert "col A col B jumbled".lower() in prompt
    # The instruction is about repairing reading order, not summarizing.
    assert "reading order" in prompt
    assert "do not summarize" in prompt


def test_reading_order_preserves_wording_instruction_present() -> None:
    backend = _RecordingBackend()
    Assistant(backend=backend).transform("reading_order", "some text")
    assert "preserve all of the original wording" in backend.prompts[0].lower()
