"""ContextBuilder: scope assembly, redaction preview, and reserved-scope guard."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from quill.core.ai.context_builder import (
    ContextBuilder,
    ContextRequest,
    ContextScope,
)


@dataclass
class FakeSource:
    selection: str = "the selected sentence"
    section: str = "## Section\nbody of the current section"
    document: str = "full document body " * 100
    outline: list[str] = field(default_factory=lambda: ["Intro", "Body", "End"])
    file_name: str = "notes.md"
    file_type: str = "markdown"

    def get_selection(self) -> str:
        return self.selection

    def get_current_section(self) -> str:
        return self.section

    def get_document(self) -> str:
        return self.document

    def get_outline(self) -> list[str]:
        return self.outline

    def get_file_name(self) -> str:
        return self.file_name

    def get_file_type(self) -> str:
        return self.file_type


def test_prompt_only_sends_no_document_body() -> None:
    builder = ContextBuilder(FakeSource())
    preview = builder.build(
        ContextRequest(ContextScope.PROMPT_ONLY, prompt="hello", include_outline=False)
    )
    assert "full document body" not in preview.text
    assert preview.includes_full_document is False
    assert "hello" in preview.text


def test_selection_scope_includes_only_selection() -> None:
    builder = ContextBuilder(FakeSource())
    preview = builder.build(ContextRequest(ContextScope.SELECTION))
    assert "the selected sentence" in preview.text
    assert "full document body" not in preview.text
    assert preview.includes_full_document is False


def test_full_document_flags_inclusion() -> None:
    builder = ContextBuilder(FakeSource())
    preview = builder.build(ContextRequest(ContextScope.FULL_DOCUMENT))
    assert "full document body" in preview.text
    assert preview.includes_full_document is True
    assert preview.word_count > 0
    assert preview.token_estimate > 0


def test_document_summary_is_smaller_than_full_document() -> None:
    source = FakeSource()
    builder = ContextBuilder(source)
    summary = builder.build(ContextRequest(ContextScope.DOCUMENT_SUMMARY))
    full = builder.build(ContextRequest(ContextScope.FULL_DOCUMENT))
    assert len(summary.text) < len(full.text)
    assert summary.includes_full_document is False
    assert "Headings:" in summary.text


def test_outline_included_by_default() -> None:
    builder = ContextBuilder(FakeSource())
    preview = builder.build(ContextRequest(ContextScope.SELECTION))
    assert preview.headings_included == ("Intro", "Body", "End")


def test_redaction_triggers_on_secret() -> None:
    source = FakeSource(selection="api key sk-ABCDEF0123456789ABCDEF0123456789ABCDEF01 here")
    builder = ContextBuilder(source)
    preview = builder.build(ContextRequest(ContextScope.SELECTION, include_outline=False))
    assert preview.redaction_triggered is True
    assert "sk-ABCDEF0123456789" not in preview.text


def test_no_redaction_on_clean_text() -> None:
    builder = ContextBuilder(FakeSource())
    preview = builder.build(ContextRequest(ContextScope.SELECTION, include_outline=False))
    assert preview.redaction_triggered is False


def test_reserved_scope_raises() -> None:
    builder = ContextBuilder(FakeSource())
    with pytest.raises(NotImplementedError):
        builder.build(ContextRequest(ContextScope.WORKSPACE_SUMMARY))


def test_speakable_summary_mentions_full_document() -> None:
    builder = ContextBuilder(FakeSource())
    preview = builder.build(ContextRequest(ContextScope.FULL_DOCUMENT))
    spoken = preview.speakable_summary()
    assert "full document is included" in spoken
    assert "notes.md" in spoken
