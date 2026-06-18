"""Unit tests for quill.core.ai.thesaurus."""

from __future__ import annotations

import pytest

from quill.core.ai.thesaurus import (
    ThesaurusAuthError,
    ThesaurusEmptyError,
    ThesaurusEntry,
    ThesaurusError,
    _parse_response,
    get_synonyms,
)

# ---------------------------------------------------------------------------
# ThesaurusEntry
# ---------------------------------------------------------------------------


def test_thesaurus_entry_is_frozen() -> None:
    e = ThesaurusEntry(synonym="happy", note="A note.")
    with pytest.raises((AttributeError, TypeError)):
        e.synonym = "other"  # type: ignore[misc]


def test_thesaurus_entry_fields() -> None:
    e = ThesaurusEntry(synonym="joyful", note="More intense than happy.")
    assert e.synonym == "joyful"
    assert e.note == "More intense than happy."


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_auth_error_is_thesaurus_error() -> None:
    assert issubclass(ThesaurusAuthError, ThesaurusError)


def test_empty_error_is_thesaurus_error() -> None:
    assert issubclass(ThesaurusEmptyError, ThesaurusError)


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------


def test_parse_response_valid_json() -> None:
    raw = '[{"synonym": "happy", "note": "General."}, {"synonym": "joyful", "note": "Intense."}]'
    entries = _parse_response(raw)
    assert len(entries) == 2
    assert entries[0].synonym == "happy"
    assert entries[1].synonym == "joyful"


def test_parse_response_strips_markdown_fence() -> None:
    raw = '```json\n[{"synonym": "glad", "note": "Mild positivity."}]\n```'
    entries = _parse_response(raw)
    assert len(entries) == 1
    assert entries[0].synonym == "glad"


def test_parse_response_empty_string() -> None:
    assert _parse_response("") == []


def test_parse_response_no_json_array() -> None:
    assert _parse_response("No JSON here at all.") == []


def test_parse_response_malformed_json() -> None:
    assert _parse_response("[{bad json}]") == []


def test_parse_response_skips_entries_without_synonym() -> None:
    raw = '[{"synonym": "", "note": "Empty."}, {"synonym": "merry", "note": "Festive."}]'
    entries = _parse_response(raw)
    assert len(entries) == 1
    assert entries[0].synonym == "merry"


def test_parse_response_non_array_json() -> None:
    raw = '{"synonym": "happy", "note": "A note."}'
    entries = _parse_response(raw)
    assert entries == []


# ---------------------------------------------------------------------------
# get_synonyms - mocked
# ---------------------------------------------------------------------------


def _make_conn() -> object:
    from quill.core.assistant_ai import AssistantConnectionSettings

    return AssistantConnectionSettings(provider="openai", model="gpt-4o-mini")


def test_get_synonyms_raises_empty_error_on_blank_word() -> None:
    conn = _make_conn()
    with pytest.raises(ThesaurusEmptyError):
        get_synonyms("   ", conn)


def test_get_synonyms_calls_ai_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.thesaurus as th

    fake_response = '[{"synonym": "glad", "note": "Mild."}]'
    monkeypatch.setattr(th, "generate_assistant_response", lambda *a, **kw: (fake_response, None))
    conn = _make_conn()
    entries = get_synonyms("happy", conn, api_key="key")
    assert len(entries) == 1
    assert entries[0].synonym == "glad"


def test_get_synonyms_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.thesaurus as th

    monkeypatch.setattr(
        th, "generate_assistant_response", lambda *a, **kw: (None, "401 unauthorized")
    )
    conn = _make_conn()
    with pytest.raises(ThesaurusAuthError):
        get_synonyms("happy", conn)


def test_get_synonyms_raises_thesaurus_error_on_generic_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.core.ai.thesaurus as th

    monkeypatch.setattr(th, "generate_assistant_response", lambda *a, **kw: (None, "timeout"))
    conn = _make_conn()
    with pytest.raises(ThesaurusError):
        get_synonyms("happy", conn)


def test_get_synonyms_context_included_in_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.thesaurus as th

    prompts = []

    def fake_gen(conn, key, prompt, **kw):
        prompts.append(prompt)
        return ('[{"synonym": "glad", "note": "Mild."}]', None)

    monkeypatch.setattr(th, "generate_assistant_response", fake_gen)
    conn = _make_conn()
    get_synonyms("happy", conn, api_key="k", context_sentence="She was very happy today.")
    assert "She was very happy today." in prompts[0]
