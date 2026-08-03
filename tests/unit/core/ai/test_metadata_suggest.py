"""AI metadata suggestions: defensive parsing, specific failures."""

from __future__ import annotations

import pytest

import quill.core.ai.metadata_suggest as metadata_suggest
from quill.core.ai.metadata_suggest import (
    MetadataSuggestError,
    _extract_json,
    suggest_document_metadata,
)
from quill.core.assistant_ai import AssistantConnectionSettings


def _conn() -> AssistantConnectionSettings:
    return AssistantConnectionSettings(provider="test", host="", model="m")


def test_extract_json_strips_code_fences() -> None:
    assert _extract_json('```json\n{"title": "T"}\n```') == {"title": "T"}


def test_extract_json_tolerates_a_preamble() -> None:
    assert _extract_json('Here you go:\n{"title": "T"}') == {"title": "T"}


def test_extract_json_raises_the_coded_error_on_garbage() -> None:
    with pytest.raises(MetadataSuggestError) as excinfo:
        _extract_json("no json here")
    assert "QUILL-AI-METADATA-FAILED" in str(excinfo.value)
    # The error-specificity contract: the user message carries the next step.
    assert "AI Hub" in excinfo.value.user_message()


def test_suggest_builds_field_suggestions(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = (
        '{"title": "My Doc", "summary": "About things.", '
        '"tags": ["alpha", "beta"], "category": "notes"}'
    )
    monkeypatch.setattr(
        metadata_suggest,
        "generate_assistant_response",
        lambda *args, **kwargs: (reply, ""),
    )

    suggestions = suggest_document_metadata("Some document text.", _conn())

    by_field = {s.field: s.value for s in suggestions}
    assert by_field == {
        "title": "My Doc",
        "summary": "About things.",
        "category": "notes",
        "tags": "alpha, beta",
    }


def test_suggest_raises_on_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        metadata_suggest,
        "generate_assistant_response",
        lambda *args, **kwargs: ("", "401 unauthorized"),
    )
    with pytest.raises(MetadataSuggestError):
        suggest_document_metadata("text", _conn())


def test_suggest_rejects_an_empty_document() -> None:
    with pytest.raises(MetadataSuggestError) as excinfo:
        suggest_document_metadata("   ", _conn())
    assert "empty" in str(excinfo.value)


def test_suggest_rejects_a_reply_with_no_usable_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        metadata_suggest,
        "generate_assistant_response",
        lambda *args, **kwargs: ('{"unrelated": 1}', ""),
    )
    with pytest.raises(MetadataSuggestError):
        suggest_document_metadata("text", _conn())
