from __future__ import annotations

import pytest

from quill.core.snippets import (
    Snippet,
    SnippetLibrary,
    extract_placeholders,
    find_snippet_by_trigger,
    load_snippet_library,
    merge_starter_pack,
    render_snippet,
    search_snippets,
)


def test_load_snippet_library_returns_empty_for_missing_file(tmp_path) -> None:
    library = load_snippet_library(tmp_path / "missing.json")
    assert library.version == 1
    assert library.snippets == []


def test_merge_starter_pack_keeps_existing_snippet() -> None:
    existing = Snippet(
        id="daily-journal-header",
        name="Custom Journal",
        trigger=";journal-custom",
        body="hello",
    )
    merged = merge_starter_pack(
        SnippetLibrary(version=1, snippets=[existing]),
        "daily-writing",
    )
    assert any(snippet.id == "daily-journal-header" for snippet in merged.snippets)
    assert any(snippet.id == "meeting-notes" for snippet in merged.snippets)


def test_search_snippets_prioritizes_exact_trigger() -> None:
    snippets = [
        Snippet(id="a", name="Bug Report", trigger=";bug", body="template"),
        Snippet(id="b", name="Bug Follow Up", trigger=";bugfollow", body="template"),
    ]
    results = search_snippets(snippets, ";bug")
    assert results[0].id == "a"


def test_extract_placeholders_supports_inputs_choices_cursor_and_time_tokens() -> None:
    placeholders = extract_placeholders(
        "Hello ${input:name}! ${choice:formal|casual} ${date} ${time} ${cursor}"
    )
    kinds = {(placeholder.kind, placeholder.name) for placeholder in placeholders}
    assert ("input", "name") in kinds
    assert ("choice", "formal|casual") in kinds
    assert ("date", "date") in kinds
    assert ("time", "time") in kinds
    assert ("cursor", "cursor") in kinds


def test_render_snippet_applies_values_and_cursor_position() -> None:
    result = render_snippet(
        "Dear ${input:name},\n${cursor}\nThanks,\n${signature}",
        {"input:name": "Quill", "signature": "Team"},
    )
    assert "Dear Quill" in result.text
    assert "Team" in result.text
    assert result.cursor == result.text.index("\n\n") + 1


def test_extract_placeholders_matches_nested_braces() -> None:
    """Regression for #287: the original pattern excluded `{`/`}` entirely,
    so an example value containing literal placeholder-looking text broke
    the match. A single level of nesting must now be allowed through."""
    placeholders = extract_placeholders("${input:Hello ${world}}")
    assert len(placeholders) == 1
    assert placeholders[0].kind == "input"
    assert placeholders[0].name == "Hello ${world}"


def test_extract_placeholders_raises_on_empty_input_name() -> None:
    with pytest.raises(ValueError, match="has no name after"):
        extract_placeholders("${input:}")


def test_extract_placeholders_raises_on_empty_choice_options() -> None:
    with pytest.raises(ValueError, match="has no choice options"):
        extract_placeholders("${choice:|}")


def test_render_snippet_exposes_placeholder_name_in_missing_value_error() -> None:
    """#287: render_snippet must surface the placeholder's friendly name
    (not just the raw token) so a UI/caller can report what is missing
    without re-parsing the token itself."""
    with pytest.raises(ValueError, match="Workflow tested"):
        render_snippet("Notes: ${input:Workflow tested}", {})


def test_find_snippet_by_trigger_is_case_insensitive_and_respects_enabled_flag() -> None:
    snippets = [
        Snippet(id="a", name="Greeting", trigger=";Hi", body="hello", enabled=False),
        Snippet(id="b", name="Greeting 2", trigger=";Hi", body="hello", enabled=True),
    ]
    assert find_snippet_by_trigger(snippets, ";hi") is snippets[1]


def test_mermaid_pack_asks_for_the_accessible_title_and_description_first() -> None:
    from quill.core.mermaid_a11y import check_mermaid
    from quill.core.snippets import starter_pack_names, starter_pack_snippets

    assert "mermaid-diagrams" in starter_pack_names()
    pack = starter_pack_snippets("mermaid-diagrams")
    kinds = {s.body.split("\n")[1].split()[0] for s in pack}
    assert kinds == {
        "flowchart",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "gantt",
        "mindmap",
        "timeline",
    }
    assert len({s.trigger for s in pack}) == len(pack)
    for snippet in pack:
        inputs = [p for p in extract_placeholders(snippet.body) if p.kind == "input"]
        assert [p.name for p in inputs[:2]] == ["accessible title", "accessible description"]
        values = {p.token: "Shown" for p in inputs}
        text = render_snippet(snippet.body, values).text
        assert "accTitle: Shown" in text and "accDescr: Shown" in text
        assert check_mermaid(text) == []
