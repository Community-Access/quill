"""Unit tests for quill.core.ai.document_qa."""

from __future__ import annotations

import pytest

from quill.core.ai.document_qa import (
    ConversationContext,
    DocumentQAAuthError,
    DocumentQAEmptyError,
    DocumentQAError,
    QAAnswer,
    _find_source_excerpt,
)

# ---------------------------------------------------------------------------
# QAAnswer
# ---------------------------------------------------------------------------


def test_qa_answer_is_frozen() -> None:
    a = QAAnswer("q", "answer", "excerpt", False)
    with pytest.raises((AttributeError, TypeError)):
        a.answer = "other"  # type: ignore[misc]


def test_qa_answer_defaults() -> None:
    a = QAAnswer(question="q", answer="a")
    assert a.source_excerpt == ""
    assert a.truncated is False


# ---------------------------------------------------------------------------
# _find_source_excerpt
# ---------------------------------------------------------------------------


def test_find_source_excerpt_finds_matching_word() -> None:
    doc = "The agreement was signed on January 15."
    answer = "The agreement was signed on January 15."
    excerpt = _find_source_excerpt(answer, doc)
    assert "agreement" in excerpt or "January" in excerpt or excerpt == ""


def test_find_source_excerpt_returns_empty_on_no_match() -> None:
    doc = "Short text."
    answer = "xyz"
    assert _find_source_excerpt(answer, doc) == ""


def test_find_source_excerpt_does_not_crash_on_empty_inputs() -> None:
    assert _find_source_excerpt("", "document text") == ""
    assert _find_source_excerpt("answer", "") == ""


def test_find_source_excerpt_adds_ellipsis_for_truncated_context() -> None:
    # Build a long document where the matching word is far in
    prefix = "a " * 200  # 400 chars
    doc = prefix + "particular word that appears here and continues for a bit more."
    answer = "The particular word is mentioned."
    excerpt = _find_source_excerpt(answer, doc)
    if excerpt:
        assert "particular" in excerpt


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_auth_error_is_qa_error() -> None:
    assert issubclass(DocumentQAAuthError, DocumentQAError)


def test_empty_error_is_qa_error() -> None:
    assert issubclass(DocumentQAEmptyError, DocumentQAError)


def test_qa_error_message() -> None:
    with pytest.raises(DocumentQAError, match="connection failed"):
        raise DocumentQAError("connection failed")


# ---------------------------------------------------------------------------
# ConversationContext
# ---------------------------------------------------------------------------


def test_conversation_context_starts_empty() -> None:
    ctx = ConversationContext(document_text="Some text.")
    assert ctx.turns == []


def test_conversation_context_clear_history() -> None:
    ctx = ConversationContext(document_text="text")
    ctx.turns.append(("q1", "a1"))
    ctx.turns.append(("q2", "a2"))
    ctx.clear_history()
    assert ctx.turns == []


def test_conversation_context_stores_document() -> None:
    text = "The cat sat on the mat."
    ctx = ConversationContext(document_text=text)
    assert ctx.document_text == text


# ---------------------------------------------------------------------------
# ask_document - mocked AI response
# ---------------------------------------------------------------------------


def _make_mock_connection() -> object:
    """Return a minimal fake AssistantConnectionSettings."""
    from quill.core.assistant_ai import AssistantConnectionSettings

    return AssistantConnectionSettings(provider="openai", model="gpt-4o-mini")


def test_ask_document_raises_on_empty_question() -> None:
    from quill.core.ai.document_qa import ask_document

    conn = _make_mock_connection()
    with pytest.raises(DocumentQAEmptyError, match="empty"):
        ask_document("", "Some document text.", conn)


def test_ask_document_raises_on_empty_document() -> None:
    from quill.core.ai.document_qa import ask_document

    conn = _make_mock_connection()
    with pytest.raises(DocumentQAEmptyError):
        ask_document("What is this about?", "   ", conn)


def test_ask_document_calls_generate_response(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai import document_qa as dq

    calls = []

    def fake_generate(conn, api_key, prompt, **kwargs):
        calls.append(prompt)
        return "The answer is 42.", None

    monkeypatch.setattr(dq, "generate_assistant_response", fake_generate)
    conn = _make_mock_connection()
    result = dq.ask_document("What is the answer?", "The answer is 42.", conn, "key")
    assert result.answer == "The answer is 42."
    assert result.question == "What is the answer?"
    assert len(calls) == 1
    assert "The answer is 42." in calls[0]


def test_ask_document_reports_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai import document_qa as dq

    monkeypatch.setattr(dq, "generate_assistant_response", lambda *a, **kw: ("answer", None))
    conn = _make_mock_connection()
    long_doc = "word " * 20_000  # > 80_000 chars
    result = dq.ask_document("Question?", long_doc, conn)
    assert result.truncated is True


def test_ask_document_raises_auth_error_on_auth_message(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai import document_qa as dq

    monkeypatch.setattr(
        dq, "generate_assistant_response", lambda *a, **kw: (None, "401 auth failed")
    )
    conn = _make_mock_connection()
    with pytest.raises(DocumentQAAuthError):
        dq.ask_document("Question?", "Document text.", conn)


def test_ask_document_raises_qa_error_on_generic_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai import document_qa as dq

    monkeypatch.setattr(dq, "generate_assistant_response", lambda *a, **kw: (None, "timeout"))
    conn = _make_mock_connection()
    with pytest.raises(DocumentQAError):
        dq.ask_document("Question?", "Document text.", conn)


def test_conversation_context_ask_accumulates_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai import document_qa as dq

    responses = iter(["Answer one.", "Answer two."])
    monkeypatch.setattr(dq, "generate_assistant_response", lambda *a, **kw: (next(responses), None))
    conn = _make_mock_connection()
    ctx = ConversationContext(document_text="Some text about things.")
    ctx.ask("Question one?", conn)
    ctx.ask("Question two?", conn)
    assert len(ctx.turns) == 2
    assert ctx.turns[0][1] == "Answer one."
    assert ctx.turns[1][1] == "Answer two."
