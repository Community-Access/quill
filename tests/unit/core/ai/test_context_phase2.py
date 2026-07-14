"""Phase 2 context wiring: scope selection, string source, redaction in the build."""

from __future__ import annotations

from quill.core.ai.context_builder import (
    ContextBuilder,
    ContextRequest,
    ContextScope,
    StringContextSource,
    choose_context_scope,
)


def test_choose_scope_prefers_selection() -> None:
    assert choose_context_scope("picked", "a long document") is ContextScope.SELECTION


def test_choose_scope_full_for_small_document() -> None:
    assert choose_context_scope("", "a short doc") is ContextScope.FULL_DOCUMENT


def test_choose_scope_summary_for_large_document() -> None:
    big = "word " * 5000  # well over the full-document token limit
    assert choose_context_scope("", big, max_full_tokens=100) is ContextScope.DOCUMENT_SUMMARY


def test_choose_scope_prompt_only_for_empty() -> None:
    assert choose_context_scope("", "   ") is ContextScope.PROMPT_ONLY


def test_string_source_round_trips() -> None:
    source = StringContextSource(
        document="Body text", selection="sel", outline=("Intro",), file_name="a.md", file_type="md"
    )
    assert source.get_document() == "Body text"
    assert source.get_selection() == "sel"
    assert source.get_outline() == ["Intro"]
    assert source.get_file_name() == "a.md"
    assert source.get_file_type() == "md"
    # current_section falls back to the selection until Phase 3 sectioning lands.
    assert source.get_current_section() == "sel"


def test_build_redacts_secret_in_payload() -> None:
    secret = "sk-" + "A" * 40
    source = StringContextSource(document=f"Here is a key {secret} in the text.", file_name="a.md")
    preview = ContextBuilder(source).build(ContextRequest(scope=ContextScope.FULL_DOCUMENT))
    assert secret not in preview.text
    assert preview.redaction_triggered is True
    assert preview.includes_full_document is True


def test_summary_scope_is_smaller_than_full() -> None:
    big = "\n\n".join(f"Paragraph {i} has several words here." for i in range(200))
    source = StringContextSource(document=big, outline=("H1", "H2"))
    summary = ContextBuilder(source).build(ContextRequest(scope=ContextScope.DOCUMENT_SUMMARY))
    full = ContextBuilder(source).build(ContextRequest(scope=ContextScope.FULL_DOCUMENT))
    assert summary.token_estimate < full.token_estimate
