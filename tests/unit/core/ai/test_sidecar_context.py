"""Tests for the auto-loaded document sidecar context (#1322)."""

from __future__ import annotations

from pathlib import Path

from quill.core.ai.assistant import Assistant
from quill.core.ai.sidecar_context import (
    DOCUMENT_CONTEXT_SUFFIX,
    announcement,
    context_preamble,
    document_context_path,
    load_sidecar_context,
)


class _Backend:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def is_available(self):  # noqa: ANN201
        return True, None

    def respond(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "ok"

    def respond_stream(self, prompt: str, on_delta) -> str:  # noqa: ANN001
        return self.respond(prompt)


def test_sidecar_path_is_beside_the_document() -> None:
    assert document_context_path("book.docx") == Path("book.docx" + DOCUMENT_CONTEXT_SUFFIX)
    assert document_context_path(None) is None
    assert document_context_path("") is None


def test_absent_sidecar_is_not_present(tmp_path: Path) -> None:
    ctx = load_sidecar_context(tmp_path / "novel.md")
    assert not ctx.is_present
    assert context_preamble(ctx) == ""
    assert announcement(ctx) == ""


def test_present_sidecar_loads_and_builds_preamble_and_announcement(tmp_path: Path) -> None:
    doc = tmp_path / "novel.md"
    doc.write_text("chapter one", encoding="utf-8")
    sidecar = tmp_path / ("novel.md" + DOCUMENT_CONTEXT_SUFFIX)
    sidecar.write_text("Protagonist: Ada Vance. Setting: Titan Station.", encoding="utf-8")

    ctx = load_sidecar_context(doc)
    assert ctx.is_present
    assert "Ada Vance" in context_preamble(ctx)
    assert "not instructions" in context_preamble(ctx)  # framed as reference, not rules
    assert announcement(ctx) == f"Using context from novel.md{DOCUMENT_CONTEXT_SUFFIX}."


def test_blank_sidecar_is_not_present(tmp_path: Path) -> None:
    doc = tmp_path / "novel.md"
    sidecar = tmp_path / ("novel.md" + DOCUMENT_CONTEXT_SUFFIX)
    sidecar.write_text("   \n\n  ", encoding="utf-8")
    assert not load_sidecar_context(doc).is_present


def test_oversized_sidecar_is_truncated_and_announced(tmp_path: Path) -> None:
    doc = tmp_path / "novel.md"
    sidecar = tmp_path / ("novel.md" + DOCUMENT_CONTEXT_SUFFIX)
    sidecar.write_text("x" * 20_000, encoding="utf-8")
    ctx = load_sidecar_context(doc)
    assert ctx.truncated
    assert "trimmed to the first" in announcement(ctx)


def test_assistant_injects_context_after_instructions_and_style() -> None:
    backend = _Backend()
    assistant = Assistant(backend=backend)
    assistant.set_instructions_preamble("RULES")
    assistant.set_style_preamble("STYLE")
    assistant.set_context_preamble("CONTEXT-FACTS")

    assistant.ask("do the thing")

    prompt = backend.prompts[-1]
    assert prompt.index("RULES") < prompt.index("STYLE") < prompt.index("CONTEXT-FACTS")
    assert prompt.index("CONTEXT-FACTS") < prompt.index("do the thing")


def test_assistant_without_context_is_unchanged() -> None:
    backend = _Backend()
    Assistant(backend=backend).ask("plain")
    assert backend.prompts[-1] == "plain"
